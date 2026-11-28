from datetime import timedelta

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import sha256_hex
from app.core.deps import get_active_member_for_user
from app.core.security import (
    create_access_token, create_refresh_token, generate_otp, generate_url_token, set_auth_cookies,
)
from app.database.types import utcnow
from app.models import (
    APPLICANT_EDITABLE_STATUSES, EditPermission, MemberApplication, OtpCode, OtpPurpose, RefreshToken, User,
)
from app.schemas.auth import MembershipSummary
from app.services.notifications import notify
from app.utils.validators import normalize_phone


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    ident = identifier.strip()
    if "@" in ident:
        return db.scalar(select(User).where(User.email == ident.lower()))
    return db.scalar(select(User).where(User.phone == normalize_phone(ident)))


def issue_session(db: Session, user: User, response: Response, request: Request | None = None) -> str:
    access = create_access_token(user.id, user.role.value)
    refresh, jti, expires = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires,
                        user_agent=(request.headers.get("user-agent", "")[:255] if request else None)))
    set_auth_cookies(response, access, refresh)
    return access


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


def create_code(db: Session, user: User, purpose: OtpPurpose, raw: str, minutes: int) -> None:
    # Invalidate earlier unused codes for the same purpose.
    db.execute(update(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                                     OtpCode.consumed_at.is_(None)).values(consumed_at=utcnow()))
    db.add(OtpCode(user_id=user.id, purpose=purpose, code_hash=sha256_hex(f"{user.id}:{raw}"),
                   expires_at=utcnow() + timedelta(minutes=minutes)))


def send_verification_otp(db: Session, user: User, channel: str) -> None:
    code = generate_otp()
    if channel == "email":
        create_code(db, user, OtpPurpose.EMAIL_VERIFY, code, settings.OTP_EXPIRE_MINUTES)
        notify(db, user, "otp_email", {"code": code, "minutes": settings.OTP_EXPIRE_MINUTES}, channels=("email",),
               sensitive=True)
    else:
        create_code(db, user, OtpPurpose.PHONE_VERIFY, code, settings.OTP_EXPIRE_MINUTES)
        notify(db, user, "otp_phone", {"code": code, "minutes": settings.OTP_EXPIRE_MINUTES}, channels=("sms",),
               sensitive=True)


# Development-only fixed verification code so email/phone can be verified
# without a real SMS/email provider. NEVER accepted in production.
DEV_BYPASS_OTP = "123456"


def verify_code(db: Session, user: User, purpose: OtpPurpose, raw: str) -> None:
    if settings.ENVIRONMENT == "development" and raw == DEV_BYPASS_OTP:
        # Consume any outstanding code for this purpose, then accept.
        otp = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                                              OtpCode.consumed_at.is_(None)).order_by(OtpCode.id.desc()))
        if otp:
            otp.consumed_at = utcnow()
        return
    otp = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                                          OtpCode.consumed_at.is_(None)).order_by(OtpCode.id.desc()).with_for_update())
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
    if not otp or otp.expires_at <= utcnow() or otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise invalid
    if otp.code_hash != sha256_hex(f"{user.id}:{raw}"):
        otp.attempts += 1
        db.commit()
        raise invalid
    otp.consumed_at = utcnow()


def create_password_token(db: Session, user: User, minutes: int) -> str:
    token = generate_url_token()
    db.execute(update(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == OtpPurpose.PASSWORD_RESET,
                                     OtpCode.consumed_at.is_(None)).values(consumed_at=utcnow()))
    db.add(OtpCode(user_id=user.id, purpose=OtpPurpose.PASSWORD_RESET, code_hash=sha256_hex(token),
                   expires_at=utcnow() + timedelta(minutes=minutes)))
    return token


def consume_password_token(db: Session, token: str) -> User:
    otp = db.scalar(select(OtpCode).where(OtpCode.code_hash == sha256_hex(token),
                                          OtpCode.purpose == OtpPurpose.PASSWORD_RESET,
                                          OtpCode.consumed_at.is_(None)).with_for_update())
    if not otp or otp.expires_at <= utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
    otp.consumed_at = utcnow()
    return db.get(User, otp.user_id)


def membership_summary(db: Session, user: User) -> MembershipSummary:
    member = get_active_member_for_user(db, user)
    app = db.scalar(select(MemberApplication).where(MemberApplication.user_id == user.id)
                    .order_by(MemberApplication.id.desc()))
    perm = None
    if member:
        now = utcnow()
        perm = db.scalar(select(EditPermission).where(
            EditPermission.member_id == member.id, EditPermission.revoked_at.is_(None),
            EditPermission.starts_at <= now, EditPermission.expires_at > now))
    if not member:
        # An inactive membership still counts as "has membership" for display purposes
        from app.models import Member, MemberProfile
        member_any = db.scalar(select(Member).join(MemberProfile).where(MemberProfile.user_id == user.id))
    else:
        member_any = member
    return MembershipSummary(
        is_member=member is not None,
        member_id=member_any.id if member_any else None,
        membership_number=member_any.membership_number if member_any else None,
        membership_status=member_any.status if member_any else None,
        application_id=app.id if app else None,
        application_status=app.status if app else None,
        edit_permission_expires_at=perm.expires_at if perm else None,
    )


def user_exists(db: Session, email: str | None, phone: str) -> dict[str, str]:
    errors = {}
    cond = or_(User.email == email, User.phone == phone) if email else User.phone == phone
    rows = db.execute(select(User.email, User.phone).where(cond)).all()
    for e, p in rows:
        if email and e == email:
            errors["email"] = "An account with this email already exists"
        if p == phone:
            errors["phone"] = "An account with this mobile number already exists"
    return errors


__all__ = ["APPLICANT_EDITABLE_STATUSES"]
