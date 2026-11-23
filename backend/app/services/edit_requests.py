from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.types import utcnow
from app.models import EditPermission, EditRequest, EditRequestStatus, User
from app.schemas.membership import EditRequestOut
from app.services.audit import audit
from app.services.notifications import notify


def edit_request_out(er: EditRequest) -> EditRequestOut:
    perm = er.permission
    now = utcnow()
    return EditRequestOut(
        id=er.id, member_id=er.member_id, membership_number=er.member.membership_number,
        member_name=er.member.profile.full_name, reason=er.reason, status=er.status, created_at=er.created_at,
        reviewed_at=er.reviewed_at, reviewed_by_name=er.reviewed_by.full_name if er.reviewed_by else None,
        review_note=er.review_note, permission_starts_at=perm.starts_at if perm else None,
        permission_expires_at=perm.expires_at if perm else None,
        permission_active=bool(perm and not perm.revoked_at and perm.starts_at <= now < perm.expires_at),
    )


def _lock_pending(db: Session, request_id: int) -> EditRequest:
    er = db.scalar(select(EditRequest).where(EditRequest.id == request_id).with_for_update())
    if not er:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Edit request not found")
    if er.status != EditRequestStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This request has already been {er.status.value.lower()}")
    return er


def _member_user(er: EditRequest) -> User | None:
    return er.member.profile.user


def approve(db: Session, request_id: int, admin: User, note: str | None, request: Request | None) -> EditRequest:
    er = _lock_pending(db, request_id)
    now = utcnow()
    expires = now + timedelta(hours=settings.EDIT_PERMISSION_HOURS)
    er.status = EditRequestStatus.APPROVED
    er.reviewed_by_id = admin.id
    er.reviewed_at = now
    er.review_note = note
    db.add(EditPermission(edit_request_id=er.id, member_id=er.member_id, granted_by_id=admin.id, starts_at=now,
                          expires_at=expires))
    db.flush()
    audit(db, admin, "edit_request.approve", "edit_request", er.id,
          {"member_id": er.member_id, "expires_at": expires.isoformat()}, request)
    user = _member_user(er)
    if user:
        notify(db, user, "edit_request_approved",
               {"expires_at": expires.strftime("%d %b %Y, %H:%M UTC")}, link="/dashboard/membership/edit")
    return er


def reject(db: Session, request_id: int, admin: User, note: str, request: Request | None) -> EditRequest:
    er = _lock_pending(db, request_id)
    er.status = EditRequestStatus.REJECTED
    er.reviewed_by_id = admin.id
    er.reviewed_at = utcnow()
    er.review_note = note
    audit(db, admin, "edit_request.reject", "edit_request", er.id, {"member_id": er.member_id}, request)
    user = _member_user(er)
    if user:
        notify(db, user, "edit_request_rejected", {"note": note}, link="/dashboard/membership")
    return er


def revoke(db: Session, request_id: int, admin: User, request: Request | None) -> EditRequest:
    er = db.get(EditRequest, request_id)
    if not er or not er.permission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No editing permission found for this request")
    if er.permission.revoked_at is None:
        er.permission.revoked_at = utcnow()
        er.permission.revoked_by_id = admin.id
        audit(db, admin, "edit_permission.revoke", "edit_request", er.id, request=request)
    return er
