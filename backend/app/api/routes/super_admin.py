from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_super_admin
from app.core.security import hash_password
from app.database.session import get_db
from app.database.types import utcnow
from app.models import (
    ApplicationStatus, AuditLog, Member, MemberApplication, MemberProfile, MembershipStatus, Role, User,
)
from app.schemas.auth import UserOut, _check_password, _check_phone, user_out
from app.schemas.common import Page, paginate_meta
from app.services import auth as auth_svc
from app.services import numbering
from app.services.audit import audit
from app.services.membership import unprocessable
from app.services.notifications import notify

router = APIRouter(prefix="/super-admin", tags=["Super Admin"], dependencies=[Depends(require_super_admin)])

ADMIN_ROLES = (Role.ADMIN, Role.SUPER_ADMIN)


class CreateAdminIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str
    role: Role = Role.ADMIN
    temporary_password: str | None = Field(None, description="Optional. If omitted an invitation link is emailed.")

    _ph = field_validator("phone")(_check_phone)

    @field_validator("temporary_password")
    @classmethod
    def _pw(cls, v):
        return _check_password(v) if v else None

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v not in ADMIN_ROLES:
            raise ValueError("Role must be ADMIN or SUPER_ADMIN")
        return v


class PromoteIn(BaseModel):
    email: EmailStr
    role: Role = Role.ADMIN

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v not in ADMIN_ROLES:
            raise ValueError("Role must be ADMIN or SUPER_ADMIN")
        return v


class UpdateAdminIn(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=150)
    phone: str | None = None
    role: Role | None = Field(None, description="ADMIN, SUPER_ADMIN, or USER to remove administrative access")

    @field_validator("phone")
    @classmethod
    def _p(cls, v):
        return _check_phone(v) if v else None


class StatusIn(BaseModel):
    is_active: bool


class SequenceIn(BaseModel):
    next_value: int = Field(ge=1, le=10**12)


class AdminOut(UserOut):
    created_by_name: str | None = None
    membership_number: str | None = None


def _admin_out(db: Session, u: User) -> AdminOut:
    creator = db.get(User, u.created_by_id) if u.created_by_id else None
    num = db.scalar(select(Member.membership_number).join(MemberProfile).where(MemberProfile.user_id == u.id))
    return AdminOut(**user_out(u).model_dump(), created_by_name=creator.full_name if creator else None,
                    membership_number=num)


def _active_super_admin_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)
                     .where(User.role == Role.SUPER_ADMIN, User.is_active.is_(True))) or 0


def _guard_last_super_admin(db: Session, target: User, new_role: Role | None, new_active: bool | None) -> None:
    losing = target.role == Role.SUPER_ADMIN and target.is_active and (
        (new_role is not None and new_role != Role.SUPER_ADMIN) or new_active is False)
    if losing and _active_super_admin_count(db) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This is the last active Super Admin. Create another Super Admin first.")


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    recent = db.execute(select(AuditLog, User.full_name).join(User, AuditLog.actor_id == User.id)
                        .where(AuditLog.actor_role.in_([Role.ADMIN.value, Role.SUPER_ADMIN.value]))
                        .order_by(AuditLog.id.desc()).limit(10)).all()
    return {
        "total_members": db.scalar(select(func.count()).select_from(Member)) or 0,
        "active_members": db.scalar(select(func.count()).select_from(Member)
                                    .where(Member.status == MembershipStatus.ACTIVE)) or 0,
        "total_admins": db.scalar(select(func.count()).select_from(User).where(User.role.in_(ADMIN_ROLES))) or 0,
        "active_admins": db.scalar(select(func.count()).select_from(User)
                                   .where(User.role.in_(ADMIN_ROLES), User.is_active.is_(True))) or 0,
        "pending_applications": db.scalar(select(func.count()).select_from(MemberApplication).where(
            MemberApplication.status.in_([ApplicationStatus.PENDING, ApplicationStatus.RESUBMITTED]))) or 0,
        "total_applications": db.scalar(select(func.count()).select_from(MemberApplication)
                                        .where(MemberApplication.status != ApplicationStatus.DRAFT)) or 0,
        "recent_admin_activity": [{"id": a.id, "actor": name, "role": a.actor_role, "action": a.action,
                                   "entity_type": a.entity_type, "entity_id": a.entity_id, "at": a.created_at}
                                  for a, name in recent],
    }


@router.get("/admins", response_model=list[AdminOut])
def list_admins(db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.role.in_(ADMIN_ROLES)).order_by(User.role.desc(), User.full_name))
    return [_admin_out(db, u) for u in users]


@router.get("/users/search", summary="Find a user/member account to promote to Admin")
def search_users(q: str = Query(..., min_length=2, max_length=100), db: Session = Depends(get_db)):
    like = f"%{q.strip()}%"
    rows = db.scalars(select(User).where(User.role == Role.USER,
                                         or_(User.full_name.ilike(like), User.email.ilike(like), User.phone.ilike(like)))
                      .limit(10)).all()
    return [_admin_out(db, u) for u in rows]


@router.post("/admins", response_model=AdminOut, status_code=status.HTTP_201_CREATED, summary="Create an Admin account")
def create_admin(body: CreateAdminIn, request: Request, actor: User = Depends(require_super_admin),
                 db: Session = Depends(get_db)):
    errors = auth_svc.user_exists(db, body.email.lower(), body.phone)
    if errors:
        raise unprocessable("Account already exists – use 'Convert existing user' instead", errors)
    user = User(full_name=body.full_name, email=body.email.lower(), phone=body.phone, role=body.role,
                created_by_id=actor.id,
                password_hash=hash_password(body.temporary_password) if body.temporary_password else None,
                password_changed_at=utcnow() if body.temporary_password else None)
    db.add(user)
    db.flush()
    if not body.temporary_password:
        hours = settings.ADMIN_INVITE_EXPIRE_HOURS
        token = auth_svc.create_password_token(db, user, hours * 60)
        link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/reset-password?token={token}&invite=1"
        notify(db, user, "admin_invite", {"role": body.role.value.replace("_", " ").title(), "link": link,
                                          "hours": hours}, channels=("email",), sensitive=True)
    audit(db, actor, "admin.create", "user", user.id, {"role": body.role.value, "email": user.email}, request)
    db.commit()
    return _admin_out(db, user)


@router.post("/admins/promote", response_model=AdminOut, summary="Convert an existing user/member into an Admin")
def promote(body: PromoteIn, request: Request, actor: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()).with_for_update())
    if not user:
        raise unprocessable("No account found", {"email": "No account is registered with this email"})
    if user.role in ADMIN_ROLES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account already has administrative access")
    if not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is deactivated")
    user.role = body.role
    audit(db, actor, "admin.promote", "user", user.id, {"role": body.role.value}, request)
    notify(db, user, "role_changed", {"role": body.role.value.replace("_", " ").title()}, channels=("web", "email"))
    db.commit()
    return _admin_out(db, user)


def _get_admin(db: Session, user_id: int) -> User:
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u or u.role not in ADMIN_ROLES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Admin not found")
    return u


@router.put("/admins/{user_id}", response_model=AdminOut, summary="Edit an Admin (name, phone, role)")
def update_admin(user_id: int, body: UpdateAdminIn, request: Request, actor: User = Depends(require_super_admin),
                 db: Session = Depends(get_db)):
    u = _get_admin(db, user_id)
    if body.role is not None and body.role != u.role:
        _guard_last_super_admin(db, u, body.role, None)
    changes = {}
    if body.full_name and body.full_name != u.full_name:
        changes["full_name"] = body.full_name
        u.full_name = body.full_name
    if body.phone and body.phone != u.phone:
        if db.scalar(select(User.id).where(User.phone == body.phone, User.id != u.id)):
            raise unprocessable("Phone in use", {"phone": "Another account uses this mobile number"})
        changes["phone"] = body.phone
        u.phone, u.phone_verified_at = body.phone, None
    if body.role is not None and body.role != u.role:
        changes["role"] = f"{u.role.value}->{body.role.value}"
        u.role = body.role
        auth_svc.revoke_all_refresh_tokens(db, u.id)
        notify(db, u, "role_changed", {"role": body.role.value.replace("_", " ").title()}, channels=("web", "email"))
    if changes:
        audit(db, actor, "admin.update", "user", u.id, changes, request)
    db.commit()
    return _admin_out(db, u)


@router.patch("/admins/{user_id}/status", response_model=AdminOut, summary="Activate / deactivate an Admin")
def set_admin_status(user_id: int, body: StatusIn, request: Request, actor: User = Depends(require_super_admin),
                     db: Session = Depends(get_db)):
    u = _get_admin(db, user_id)
    if u.id == actor.id and not body.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "You cannot deactivate your own account")
    _guard_last_super_admin(db, u, None, body.is_active)
    if u.is_active != body.is_active:
        u.is_active = body.is_active
        if not body.is_active:
            auth_svc.revoke_all_refresh_tokens(db, u.id)
        audit(db, actor, "admin.activate" if body.is_active else "admin.deactivate", "user", u.id, request=request)
    db.commit()
    return _admin_out(db, u)


@router.get("/audit-logs", summary="Audit trail of administrative and security events")
def audit_logs(actor_id: int | None = None, action: str | None = Query(None, max_length=80),
               entity_type: str | None = Query(None, max_length=50), admin_only: bool = False,
               page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(AuditLog)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if admin_only:
        stmt = stmt.where(AuditLog.actor_role.in_([Role.ADMIN.value, Role.SUPER_ADMIN.value]))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_({r.actor_id for r in rows if r.actor_id})))}
    return {"items": [{"id": r.id, "actor_id": r.actor_id, "actor": names.get(r.actor_id), "actor_role": r.actor_role,
                       "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id,
                       "details": r.details, "ip_address": r.ip_address, "created_at": r.created_at} for r in rows],
            **paginate_meta(total, page, page_size)}


@router.get("/settings", summary="System settings (organisation, numbering, providers)")
def get_settings_view(db: Session = Depends(get_db)):
    return {
        "organisation": {"full_name": settings.ORG_FULL_NAME, "abbreviation": settings.ORG_ABBREVIATION,
                         "registration": settings.ORG_REGISTRATION, "address": settings.ORG_ADDRESS,
                         "phone": settings.ORG_PHONE, "email": settings.ORG_EMAIL},
        "membership_numbering": numbering.preview_numbers(db),
        "rules": {"minimum_age_years": settings.MINIMUM_AGE_YEARS,
                  "edit_permission_hours": settings.EDIT_PERMISSION_HOURS,
                  "require_introducer_signature": settings.REQUIRE_INTRODUCER_SIGNATURE,
                  "introducer_must_be_registered": settings.INTRODUCER_MUST_BE_REGISTERED,
                  "require_verified_contact_for_submission": settings.REQUIRE_VERIFIED_CONTACT_FOR_SUBMISSION},
        "providers": {"email": settings.EMAIL_PROVIDER, "sms": settings.SMS_PROVIDER},
        "environment": settings.ENVIRONMENT,
        "configuration_warnings": settings.validate_production() if settings.is_production else [
            "Development mode: emails/SMS are written to the console outbox, not delivered."
        ] if settings.EMAIL_PROVIDER == "console" or settings.SMS_PROVIDER == "console" else [],
    }


@router.put("/settings/membership-sequence", summary="Set the next automatic membership sequence value")
def set_sequence(body: SequenceIn, request: Request, actor: User = Depends(require_super_admin),
                 db: Session = Depends(get_db)):
    seq = numbering.set_next_value(db, body.next_value)
    audit(db, actor, "settings.membership_sequence", "membership_sequence", seq.id, {"next_value": body.next_value},
          request)
    db.commit()
    return numbering.preview_numbers(db)


__all__ = ["timedelta", "Page"]
