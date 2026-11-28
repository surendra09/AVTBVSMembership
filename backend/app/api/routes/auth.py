from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.core.security import (
    REFRESH_COOKIE, clear_auth_cookies, create_access_token, create_refresh_token, decode_token, hash_password,
    needs_rehash, set_auth_cookies, verify_password,
)
from app.database.session import get_db
from app.database.types import utcnow
from app.models import OtpPurpose, RefreshToken, Role, User
from app.schemas.auth import (
    ChangePasswordIn, ForgotPasswordIn, LoginIn, LoginOut, MeOut, RegisterIn, ResendOtpIn, ResetPasswordIn,
    UpdateAccountIn, VerifyCodeIn, user_out,
)
from app.schemas.common import Message
from app.services import auth as svc
from app.services.audit import audit
from app.services.membership import unprocessable
from app.services.notifications import notify

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MeOut, status_code=status.HTTP_201_CREATED,
             summary="Create a user account (not a membership)")
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "register", settings.RATE_LIMIT_REGISTER)
    errors = svc.user_exists(db, body.email, body.phone)
    if errors:
        raise unprocessable("Account already exists", errors)
    user = User(full_name=body.full_name, email=body.email, phone=body.phone,
                password_hash=hash_password(body.password), role=Role.USER, password_changed_at=None)
    db.add(user)
    db.flush()
    notify(db, user, "account_registered", link="/dashboard")
    svc.send_verification_otp(db, user, "phone")
    audit(db, user, "auth.register", "user", user.id, request=request)
    svc.issue_session(db, user, response, request)
    user.last_login_at = utcnow()
    db.commit()
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


def _login(db: Session, identifier: str, password: str, request: Request, response: Response) -> LoginOut:
    rate_limit(request, "login", settings.RATE_LIMIT_LOGIN, identifier)
    user = svc.find_user_by_identifier(db, identifier)
    if not user or not verify_password(password, user.password_hash):
        if user:
            audit(db, user, "auth.login_failed", "user", user.id, request=request)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email/mobile number or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated. Contact the Sabha office.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    access = svc.issue_session(db, user, response, request)
    audit(db, user, "auth.login", "user", user.id, request=request)
    db.commit()
    return LoginOut(user=user_out(user), membership=svc.membership_summary(db, user), access_token=access)


@router.post("/login", response_model=LoginOut, summary="Log in with email or mobile number")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    return _login(db, body.identifier, body.password, request, response)


@router.post("/token", response_model=LoginOut, summary="OAuth2 password flow (for Swagger 'Authorize')",
             include_in_schema=True)
def token(request: Request, response: Response, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    return _login(db, form.username, form.password, request, response)


@router.post("/refresh", response_model=MeOut, summary="Rotate the refresh token and issue a new access token")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(raw, "refresh") if raw else None
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again.")
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]).with_for_update())
    if not row or row.expires_at <= utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again.")
    if row.revoked_at is not None:
        # Re-use of a rotated token: possible theft – revoke the whole family.
        svc.revoke_all_refresh_tokens(db, row.user_id)
        db.commit()
        clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again.")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again.")
    new_refresh, jti, expires = create_refresh_token(user.id)
    row.revoked_at = utcnow()
    row.replaced_by_jti = jti
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires,
                        user_agent=request.headers.get("user-agent", "")[:255]))
    set_auth_cookies(response, create_access_token(user.id, user.role.value), new_refresh)
    db.commit()
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE)
    payload = decode_token(raw, "refresh") if raw else None
    if payload:
        row = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))
        if row and not row.revoked_at:
            row.revoked_at = utcnow()
            db.commit()
    clear_auth_cookies(response)
    return Message(message="Logged out")


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


@router.put("/me", response_model=MeOut, summary="Update account name")
def update_me(body: UpdateAccountIn, request: Request, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    user.full_name = body.full_name
    audit(db, user, "account.update", "user", user.id, request=request)
    db.commit()
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


@router.post("/verify-email", response_model=MeOut)
def verify_email(body: VerifyCodeIn, request: Request, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    rate_limit(request, "otp-verify", settings.RATE_LIMIT_OTP, f"email:{user.id}")
    if user.email_verified_at:
        return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))
    svc.verify_code(db, user, OtpPurpose.EMAIL_VERIFY, body.code)
    user.email_verified_at = utcnow()
    audit(db, user, "auth.verify_email", "user", user.id, request=request)
    db.commit()
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


@router.post("/verify-phone", response_model=MeOut)
def verify_phone(body: VerifyCodeIn, request: Request, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    rate_limit(request, "otp-verify", settings.RATE_LIMIT_OTP, f"phone:{user.id}")
    if user.phone_verified_at:
        return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))
    svc.verify_code(db, user, OtpPurpose.PHONE_VERIFY, body.code)
    user.phone_verified_at = utcnow()
    audit(db, user, "auth.verify_phone", "user", user.id, request=request)
    db.commit()
    return MeOut(user=user_out(user), membership=svc.membership_summary(db, user))


@router.post("/resend-otp", response_model=Message)
def resend_otp(body: ResendOtpIn, request: Request, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    rate_limit(request, "otp-send", settings.RATE_LIMIT_OTP, f"{body.channel}:{user.id}")
    if (body.channel == "email" and user.email_verified_at) or (body.channel == "phone" and user.phone_verified_at):
        return Message(message="Already verified")
    svc.send_verification_otp(db, user, body.channel)
    db.commit()
    return Message(message="A new verification code has been sent")


@router.post("/forgot-password", response_model=Message)
def forgot_password(body: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "forgot", settings.RATE_LIMIT_PASSWORD_RESET, body.email)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        token = svc.create_password_token(db, user, settings.PASSWORD_RESET_EXPIRE_MINUTES)
        link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password?token={token}"
        notify(db, user, "password_reset", {"link": link, "minutes": settings.PASSWORD_RESET_EXPIRE_MINUTES},
               channels=("email",), sensitive=True)
        audit(db, user, "auth.password_reset_requested", "user", user.id, request=request)
        db.commit()
    # Same response either way – prevents account enumeration.
    return Message(message="If an account exists for this email, a password reset link has been sent.")


@router.post("/reset-password", response_model=Message)
def reset_password(body: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    rate_limit(request, "reset", settings.RATE_LIMIT_PASSWORD_RESET)
    user = svc.consume_password_token(db, body.token)
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = utcnow()
    if not user.email_verified_at:
        user.email_verified_at = utcnow()  # the link proved control of the mailbox
    svc.revoke_all_refresh_tokens(db, user.id)
    audit(db, user, "auth.password_reset", "user", user.id, request=request)
    db.commit()
    return Message(message="Your password has been reset. Please log in.")


@router.post("/change-password", response_model=Message)
def change_password(body: ChangePasswordIn, request: Request, response: Response,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise unprocessable("Current password is incorrect", {"current_password": "Incorrect password"})
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = utcnow()
    svc.revoke_all_refresh_tokens(db, user.id)
    audit(db, user, "auth.password_change", "user", user.id, request=request)
    svc.issue_session(db, user, response, request)
    db.commit()
    return Message(message="Password changed")
