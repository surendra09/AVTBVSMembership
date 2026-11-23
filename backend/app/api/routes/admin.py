import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database.session import get_db
from app.database.types import utcnow
from app.models import (
    ApplicationDocument, ApplicationStatus, ChangeSource, DeliveryStatus, DocumentType, EditRequest,
    EditRequestStatus, Member, MemberApplication, MemberProfile, MembershipStatus, MemberSource,
    NotificationChannel, NotificationDelivery, Role, User,
)
from app.schemas.common import Message, Page, paginate_meta
from app.schemas.membership import (
    AdminApplicationOut, AdminMemberListItem, AdminMemberOut, AdminMemberUpdateIn, ApplicationListItem, ApproveIn,
    CorrectionIn, DocumentOut, EditRejectIn, EditRequestOut, EditReviewIn, LinkAccountIn, ManualMemberIn,
    MemberStatusIn, RejectIn,
)
from app.services import edit_requests as edit_svc
from app.services import membership as svc
from app.services import storage
from app.services.audit import audit
from app.services.notifications import notify

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


# --- Dashboard ------------------------------------------------------------------------
@router.get("/dashboard", summary="Overview counts for the Admin dashboard")
def dashboard(db: Session = Depends(get_db)):
    def count_apps(*statuses):
        return db.scalar(select(func.count()).select_from(MemberApplication)
                         .where(MemberApplication.status.in_(statuses))) or 0

    since = utcnow() - timedelta(days=30)
    recent = db.scalars(select(MemberApplication)
                        .where(MemberApplication.status.in_([ApplicationStatus.PENDING, ApplicationStatus.RESUBMITTED]))
                        .order_by(MemberApplication.last_submitted_at.asc()).limit(6)).all()
    return {
        "total_members": db.scalar(select(func.count()).select_from(Member)) or 0,
        "active_members": db.scalar(select(func.count()).select_from(Member)
                                    .where(Member.status == MembershipStatus.ACTIVE)) or 0,
        "pending_applications": count_apps(ApplicationStatus.PENDING, ApplicationStatus.RESUBMITTED),
        "correction_requests": count_apps(ApplicationStatus.CORRECTION_REQUIRED),
        "rejected_applications": count_apps(ApplicationStatus.REJECTED),
        "approved_applications": count_apps(ApplicationStatus.APPROVED),
        "new_members_30d": db.scalar(select(func.count()).select_from(Member).where(Member.enrolled_at >= since)) or 0,
        "pending_edit_requests": db.scalar(select(func.count()).select_from(EditRequest)
                                           .where(EditRequest.status == EditRequestStatus.PENDING)) or 0,
        "failed_deliveries": db.scalar(select(func.count()).select_from(NotificationDelivery)
                                       .where(NotificationDelivery.status == DeliveryStatus.FAILED)) or 0,
        "awaiting_review": [svc.application_list_item(a).model_dump(mode="json") for a in recent],
    }


# --- Applications ----------------------------------------------------------------------
APP_SORTS = {
    "submitted_asc": MemberApplication.last_submitted_at.asc(),
    "submitted_desc": MemberApplication.last_submitted_at.desc(),
    "name": MemberApplication.full_name.asc(),
    "updated_desc": MemberApplication.updated_at.desc(),
}


@router.get("/applications", response_model=Page[ApplicationListItem])
def list_applications(
    status_filter: list[ApplicationStatus] | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=100, description="Name, father's name, application no., mobile, introducer"),
    sort: str = Query("submitted_asc", pattern="^(submitted_asc|submitted_desc|name|updated_desc)$"),
    include_drafts: bool = False,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(MemberApplication)
    if status_filter:
        stmt = stmt.where(MemberApplication.status.in_(status_filter))
    elif not include_drafts:
        stmt = stmt.where(MemberApplication.status != ApplicationStatus.DRAFT)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(MemberApplication.full_name.ilike(like), MemberApplication.father_name.ilike(like),
                              MemberApplication.application_number.ilike(like), MemberApplication.cell.ilike(like),
                              MemberApplication.introducer_reg_no.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(APP_SORTS[sort], MemberApplication.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return Page[ApplicationListItem](items=[svc.application_list_item(a) for a in rows],
                                     **paginate_meta(total, page, page_size))


def _get_app(db: Session, app_id: int) -> MemberApplication:
    app = db.get(MemberApplication, app_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


@router.get("/applications/{app_id}", response_model=AdminApplicationOut,
            summary="Complete application incl. documents, declaration and history")
def get_application(app_id: int, request: Request, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    app = _get_app(db, app_id)
    audit(db, admin, "application.view", "application", app.id, request=request)  # access to Aadhaar is logged
    db.commit()
    return svc.admin_application_out(db, app)


@router.post("/applications/{app_id}/approve", response_model=AdminApplicationOut,
             summary="Approve → creates official member + membership number (atomic)")
def approve(app_id: int, body: ApproveIn, request: Request, admin: User = Depends(require_admin),
            db: Session = Depends(get_db)):
    office = body.model_dump(exclude={"note"})
    try:
        svc.approve_application(db, app_id, admin, office, body.note, request)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return svc.admin_application_out(db, _get_app(db, app_id))


@router.post("/applications/{app_id}/corrections", response_model=AdminApplicationOut,
             summary="Request corrections (→ CORRECTION_REQUIRED)")
def corrections(app_id: int, body: CorrectionIn, request: Request, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    svc.request_corrections(db, app_id, admin, body.notes, request)
    db.commit()
    return svc.admin_application_out(db, _get_app(db, app_id))


@router.post("/applications/{app_id}/reject", response_model=AdminApplicationOut,
             summary="Reject with a reason (→ REJECTED)")
def reject(app_id: int, body: RejectIn, request: Request, admin: User = Depends(require_admin),
           db: Session = Depends(get_db)):
    svc.reject_application(db, app_id, admin, body.reason, request)
    db.commit()
    return svc.admin_application_out(db, _get_app(db, app_id))


# --- Members ---------------------------------------------------------------------------
MEMBER_SORTS = {"name": MemberProfile.full_name.asc(), "number": Member.membership_number.asc(),
                "recent": Member.enrolled_at.desc()}


@router.get("/members", response_model=Page[AdminMemberListItem])
def list_members(q: str | None = Query(None, max_length=100), status_filter: MembershipStatus | None = Query(None, alias="status"),
                 source: MemberSource | None = None, city: str | None = Query(None, max_length=100),
                 sort: str = Query("name", pattern="^(name|number|recent)$"),
                 page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 db: Session = Depends(get_db)):
    stmt = select(Member).join(MemberProfile, Member.member_profile_id == MemberProfile.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(MemberProfile.full_name.ilike(like), MemberProfile.father_name.ilike(like),
                              Member.membership_number.ilike(like), MemberProfile.cell.ilike(like)))
    if status_filter:
        stmt = stmt.where(Member.status == status_filter)
    if source:
        stmt = stmt.where(Member.source == source)
    if city:
        stmt = stmt.where(MemberProfile.city.ilike(f"%{city.strip()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(MEMBER_SORTS[sort]).offset((page - 1) * page_size).limit(page_size)).all()
    items = []
    for m in rows:
        p = m.profile
        photo = svc.photo_of(p.documents)
        items.append(AdminMemberListItem(
            id=m.id, membership_number=m.membership_number, full_name=p.full_name, father_name=p.father_name,
            city=p.city, cell=p.cell, status=m.status, source=m.source, enrolled_at=m.enrolled_at,
            has_account=p.user_id is not None, photo_url=svc.doc_url(photo) if photo else None))
    return Page[AdminMemberListItem](items=items, **paginate_meta(total, page, page_size))


def _get_member(db: Session, member_id: int, lock: bool = False) -> Member:
    stmt = select(Member).where(Member.id == member_id)
    if lock:
        stmt = stmt.with_for_update()
    m = db.scalar(stmt)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return m


@router.get("/members/check-number", summary="Check whether a membership number is already used")
def check_number(number: str = Query(..., min_length=1, max_length=50), db: Session = Depends(get_db)):
    m = db.scalar(select(Member).where(Member.membership_number == number.strip()))
    return {"exists": m is not None, "member_name": m.profile.full_name if m else None,
            "status": m.status if m else None}


@router.get("/members/{member_id}", response_model=AdminMemberOut)
def get_member(member_id: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = _get_member(db, member_id)
    audit(db, admin, "member.view", "member", m.id, request=request)
    db.commit()
    return svc.admin_member_out(db, m)


@router.post("/members", response_model=AdminMemberOut, status_code=status.HTTP_201_CREATED,
             summary="Add an existing member manually with their existing membership number")
def add_existing_member(body: ManualMemberIn, request: Request, admin: User = Depends(require_admin),
                        db: Session = Depends(get_db)):
    member = svc.create_manual_member(db, body.model_dump(), admin, request)
    db.commit()
    return svc.admin_member_out(db, _get_member(db, member.id))


@router.put("/members/{member_id}", response_model=AdminMemberOut, summary="Edit a member record (Admin)")
def update_member(member_id: int, body: AdminMemberUpdateIn, request: Request, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    m = _get_member(db, member_id, lock=True)
    data = body.model_dump(exclude_unset=True)
    office = {k: data.pop(k) for k in list(data) if k in svc.OFFICE_FIELDS}
    changes = svc.apply_form_data(m.profile, data)
    for k, v in office.items():
        old = getattr(m, k)
        if old != v:
            setattr(m, k, v)
            changes.append((f"office:{k}", svc._stringify(k, old), svc._stringify(k, v)))
    errors = svc.validate_form_completeness(m.profile, require_introducer=False)
    if errors:
        db.rollback()
        raise svc.unprocessable("Please correct the highlighted fields", errors)
    if changes:
        svc.record_changes(db, m, changes, admin, ChangeSource.ADMIN_EDIT)
        audit(db, admin, "member.admin_edit", "member", m.id, {"fields": [c[0] for c in changes]}, request)
    db.commit()
    return svc.admin_member_out(db, m)


@router.patch("/members/{member_id}/status", response_model=AdminMemberOut, summary="Activate / deactivate membership")
def set_member_status(member_id: int, body: MemberStatusIn, request: Request, admin: User = Depends(require_admin),
                      db: Session = Depends(get_db)):
    m = _get_member(db, member_id, lock=True)
    if m.status == body.status:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Membership is already {body.status.value}")
    old = m.status
    m.status = body.status
    if body.status == MembershipStatus.INACTIVE:
        m.deactivated_at, m.deactivation_reason = utcnow(), body.reason
    else:
        m.deactivated_at, m.deactivation_reason = None, None
    svc.record_changes(db, m, [("status", old.value, body.status.value)], admin, ChangeSource.ADMIN_EDIT)
    audit(db, admin, "member.status", "member", m.id, {"from": old.value, "to": body.status.value}, request)
    if m.profile.user:
        notify(db, m.profile.user, "membership_status_changed",
               {"membership_number": m.membership_number, "status": body.status.value,
                "reason": f"Reason: {body.reason}" if body.reason else ""}, link="/dashboard")
    db.commit()
    return svc.admin_member_out(db, m)


@router.post("/members/{member_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Upload a photograph/document for a member (Admin)")
async def upload_member_document(member_id: int, request: Request, doc_type: DocumentType = Form(...),
                                 file: UploadFile = File(...), admin: User = Depends(require_admin),
                                 db: Session = Depends(get_db)):
    m = _get_member(db, member_id, lock=True)
    stored = await storage.validate_and_store(file, doc_type)
    for old in m.profile.documents:
        if old.doc_type == doc_type and old.is_current:
            old.is_current = False
    doc = ApplicationDocument(member_profile_id=m.member_profile_id, doc_type=doc_type,
                              storage_key=stored.storage_key, original_filename=stored.original_filename,
                              content_type=stored.content_type, size_bytes=stored.size_bytes, sha256=stored.sha256,
                              uploaded_by_id=admin.id)
    db.add(doc)
    db.flush()
    svc.record_changes(db, m, [(f"document:{doc_type.value}", None, stored.original_filename)], admin,
                       ChangeSource.ADMIN_EDIT)
    audit(db, admin, "member.upload", "member", m.id, {"doc_type": doc_type.value}, request)
    db.commit()
    return svc.doc_out(doc)


@router.post("/members/{member_id}/link-account", response_model=AdminMemberOut,
             summary="Link a manually-added member to a verified user account")
def link_account(member_id: int, body: LinkAccountIn, request: Request, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    m = _get_member(db, member_id, lock=True)
    if m.profile.user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This membership is already linked to an account")
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user:
        raise svc.unprocessable("No account found", {"email": "No account is registered with this email"})
    if user.role != Role.USER:
        raise svc.unprocessable("Invalid account", {"email": "Administrator accounts cannot be linked to a membership"})
    if not (user.email_verified_at and user.phone_verified_at):
        raise svc.unprocessable("Account not verified",
                                {"email": "The account holder must verify their email and mobile number first"})
    if db.scalar(select(MemberProfile.id).where(MemberProfile.user_id == user.id)):
        raise svc.unprocessable("Account already linked", {"email": "This account already has a membership"})
    open_app = db.scalar(select(MemberApplication).where(
        MemberApplication.user_id == user.id,
        MemberApplication.status.in_([ApplicationStatus.PENDING, ApplicationStatus.RESUBMITTED,
                                      ApplicationStatus.CORRECTION_REQUIRED, ApplicationStatus.DRAFT])))
    if open_app:
        raise svc.unprocessable("Open application", {
            "email": f"This account has an open application ({open_app.application_number}); reject it first"})
    m.profile.user_id = user.id
    svc.record_changes(db, m, [("linked_account", None, user.email)], admin, ChangeSource.ADMIN_EDIT)
    audit(db, admin, "member.link_account", "member", m.id, {"user_id": user.id}, request)
    notify(db, user, "account_linked", {"membership_number": m.membership_number}, link="/dashboard")
    db.commit()
    db.refresh(m)
    return svc.admin_member_out(db, m)


# --- Edit requests ---------------------------------------------------------------------
@router.get("/edit-requests", response_model=Page[EditRequestOut])
def list_edit_requests(status_filter: EditRequestStatus | None = Query(None, alias="status"),
                       page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                       db: Session = Depends(get_db)):
    stmt = select(EditRequest)
    if status_filter:
        stmt = stmt.where(EditRequest.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(EditRequest.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return Page[EditRequestOut](items=[edit_svc.edit_request_out(r) for r in rows],
                                **paginate_meta(total, page, page_size))


@router.post("/edit-requests/{request_id}/approve", response_model=EditRequestOut,
             summary="Approve → member may edit for exactly 24 hours")
def approve_edit(request_id: int, body: EditReviewIn, request: Request, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    er = edit_svc.approve(db, request_id, admin, body.note, request)
    db.commit()
    db.refresh(er)
    return edit_svc.edit_request_out(er)


@router.post("/edit-requests/{request_id}/reject", response_model=EditRequestOut)
def reject_edit(request_id: int, body: EditRejectIn, request: Request, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    er = edit_svc.reject(db, request_id, admin, body.note, request)
    db.commit()
    db.refresh(er)
    return edit_svc.edit_request_out(er)


@router.post("/edit-requests/{request_id}/revoke", response_model=EditRequestOut,
             summary="Revoke an active editing window early")
def revoke_edit(request_id: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    er = edit_svc.revoke(db, request_id, admin, request)
    db.commit()
    db.refresh(er)
    return edit_svc.edit_request_out(er)


# --- Notification records --------------------------------------------------------------
@router.get("/notification-deliveries", summary="Email/SMS delivery records with status and errors")
def list_deliveries(status_filter: DeliveryStatus | None = Query(None, alias="status"),
                    channel: NotificationChannel | None = None, q: str | None = Query(None, max_length=100),
                    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                    db: Session = Depends(get_db)):
    stmt = select(NotificationDelivery)
    if status_filter:
        stmt = stmt.where(NotificationDelivery.status == status_filter)
    if channel:
        stmt = stmt.where(NotificationDelivery.channel == channel)
    if q:
        stmt = stmt.where(or_(NotificationDelivery.recipient.ilike(f"%{q}%"), NotificationDelivery.event.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(NotificationDelivery.id.desc()).offset((page - 1) * page_size).limit(page_size))
    items = [{
        "id": d.id, "event": d.event, "channel": d.channel, "recipient": d.recipient, "subject": d.subject,
        # OTP codes / reset links are never shown back, even to admins
        "body_preview": "[sensitive – hidden]" if d.is_sensitive else d.body_text[:240],
        "status": d.status, "attempts": d.attempts, "last_error": d.last_error, "sent_at": d.sent_at,
        "created_at": d.created_at, "next_attempt_at": d.next_attempt_at,
    } for d in rows]
    return {"items": items, **paginate_meta(total, page, page_size)}


@router.post("/notification-deliveries/{delivery_id}/retry", response_model=Message)
def retry_delivery(delivery_id: int, request: Request, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    d = db.get(NotificationDelivery, delivery_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Delivery not found")
    if d.status != DeliveryStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only failed deliveries can be retried")
    if d.is_sensitive:
        raise HTTPException(status.HTTP_409_CONFLICT, "Expired one-time codes cannot be resent; ask the user to request a new one")
    d.status, d.attempts, d.next_attempt_at = DeliveryStatus.PENDING, 0, utcnow()
    audit(db, admin, "delivery.retry", "notification_delivery", d.id, request=request)
    db.commit()
    return Message(message="Queued for retry")


# --- Reports ---------------------------------------------------------------------------
@router.get("/reports/summary", summary="Membership statistics")
def report_summary(months: int = Query(12, ge=1, le=60), db: Session = Depends(get_db)):
    start = (utcnow().replace(day=1) - timedelta(days=31 * (months - 1))).replace(day=1, hour=0, minute=0, second=0,
                                                                                    microsecond=0)
    enrolled = db.scalars(select(Member.enrolled_at).where(Member.enrolled_at >= start)).all()
    by_month: dict[str, int] = {}
    cursor = start
    for _ in range(months):
        by_month[cursor.strftime("%Y-%m")] = 0
        cursor = (cursor + timedelta(days=32)).replace(day=1)
    for dt in enrolled:
        key = dt.strftime("%Y-%m")
        if key in by_month:
            by_month[key] += 1
    by_status = dict(db.execute(select(MemberApplication.status, func.count()).group_by(MemberApplication.status)).all())
    by_city = db.execute(select(MemberProfile.city, func.count()).join(Member).where(Member.status == MembershipStatus.ACTIVE)
                         .group_by(MemberProfile.city).order_by(func.count().desc()).limit(10)).all()
    by_source = dict(db.execute(select(Member.source, func.count()).group_by(Member.source)).all())
    by_blood = db.execute(select(MemberProfile.blood_group, func.count()).join(Member)
                          .where(Member.status == MembershipStatus.ACTIVE, MemberProfile.blood_group.is_not(None))
                          .group_by(MemberProfile.blood_group).order_by(func.count().desc())).all()
    return {
        "new_members_by_month": [{"month": k, "count": v} for k, v in by_month.items()],
        "applications_by_status": {s.value: int(by_status.get(s, 0)) for s in ApplicationStatus},
        "members_by_source": {s.value: int(by_source.get(s, 0)) for s in MemberSource},
        "top_cities": [{"city": c or "—", "count": n} for c, n in by_city],
        "blood_groups": [{"blood_group": b, "count": n} for b, n in by_blood],
    }


@router.get("/reports/members.csv", summary="Export member list as CSV (no Aadhaar or documents)",
            response_class=StreamingResponse)
def export_members(request: Request, status_filter: MembershipStatus | None = Query(None, alias="status"),
                   admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(Member).join(MemberProfile).order_by(Member.membership_number)
    if status_filter:
        stmt = stmt.where(Member.status == status_filter)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Membership No.", "Name", "Father's Name", "City/Town/Village", "State", "Country", "Pincode", "Cell",
                "Email", "Blood Group", "Family Surname", "Gothram", "Natchathiram", "Occupation", "Status", "Source",
                "Enrolled On"])
    for m in db.scalars(stmt):
        p = m.profile
        w.writerow([m.membership_number, p.full_name, p.father_name, p.city, p.state, p.country, p.pincode, p.cell,
                    p.email or "", p.blood_group or "", p.family_surname or "", p.gothram or "", p.natchathiram or "",
                    p.occupation or "", m.status.value, m.source.value, m.enrolled_at.date().isoformat()])
    audit(db, admin, "report.export_members", "member", None, {"status": status_filter.value if status_filter else None},
          request)
    db.commit()
    filename = f"avtbvs-members-{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
