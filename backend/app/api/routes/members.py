from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import (
    get_active_member_for_user, get_current_user, get_optional_user, require_active_member,
    require_member_or_admin,
)
from app.database.session import get_db
from app.database.types import utcnow
from app.models import (
    ApplicationDocument, ChangeSource, DocumentType, EditRequest, EditRequestStatus, Member, MemberApplication,
    MemberProfile, MembershipStatus, User,
)
from app.schemas.common import Page, paginate_meta
from app.schemas.membership import (
    DirectoryMemberOut, DocumentOut, EditRequestIn, EditRequestOut, MemberProfileUpdateIn, MyMembershipOut,
    PublicMemberOut,
)
from app.services import membership as svc
from app.services import storage
from app.services.audit import audit
from app.services.edit_requests import edit_request_out
from app.services.notifications import notify, notify_admins

router = APIRouter(tags=["Member Directory & Member Self-Service"])

SORTS = {"name": MemberProfile.full_name, "number": Member.membership_number, "recent": Member.enrolled_at.desc(),
         "city": MemberProfile.city}


def _directory_query(q: str | None, city: str | None, include_number_search: bool):
    stmt = (select(Member).join(MemberProfile, Member.member_profile_id == MemberProfile.id)
            .where(Member.status == MembershipStatus.ACTIVE))
    if q:
        like = f"%{q.strip()}%"
        conds = [MemberProfile.full_name.ilike(like), MemberProfile.father_name.ilike(like)]
        if include_number_search:
            conds.append(Member.membership_number.ilike(like))
        stmt = stmt.where(or_(*conds))
    if city:
        stmt = stmt.where(MemberProfile.city.ilike(f"%{city.strip()}%"))
    return stmt


@router.get("/members/public", response_model=Page[PublicMemberOut],
            summary="Public directory – ONLY member name and father's name")
def public_directory(q: str | None = Query(None, max_length=100, description="Search by name or father's name"),
                     page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                     db: Session = Depends(get_db)):
    stmt = _directory_query(q, None, include_number_search=False)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    # Select ONLY the two public columns – private data never leaves the database here.
    rows = db.execute(
        stmt.with_only_columns(Member.id, MemberProfile.full_name, MemberProfile.father_name)
        .order_by(MemberProfile.full_name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[PublicMemberOut](items=[PublicMemberOut(id=r[0], full_name=r[1], father_name=r[2]) for r in rows],
                                 **paginate_meta(total, page, page_size))


@router.get("/members", response_model=Page[DirectoryMemberOut],
            summary="Full member directory (approved members & admins only)")
def member_directory(q: str | None = Query(None, max_length=100, description="Name, father's name or membership no."),
                     city: str | None = Query(None, max_length=100),
                     sort: str = Query("name", pattern="^(name|number|recent|city)$"),
                     page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100),
                     _: User = Depends(require_member_or_admin), db: Session = Depends(get_db)):
    stmt = _directory_query(q, city, include_number_search=True)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    members = db.scalars(stmt.order_by(SORTS[sort]).offset((page - 1) * page_size).limit(page_size)).all()
    return Page[DirectoryMemberOut](items=[svc.directory_out(m) for m in members],
                                    **paginate_meta(total, page, page_size))


@router.get("/members/me", response_model=MyMembershipOut, summary="My official membership record")
def my_membership(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.scalar(select(Member).join(MemberProfile).where(MemberProfile.user_id == user.id))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You do not have an official membership yet")
    return svc.my_membership_out(db, member)


@router.get("/members/edit-requests/me", response_model=list[EditRequestOut])
def my_edit_requests(member: Member = Depends(require_active_member), db: Session = Depends(get_db)):
    rows = db.scalars(select(EditRequest).where(EditRequest.member_id == member.id)
                      .order_by(EditRequest.id.desc())).all()
    return [edit_request_out(r) for r in rows]


@router.post("/members/edit-requests", response_model=EditRequestOut, status_code=status.HTTP_201_CREATED,
             summary="Request permission to edit my approved details")
def create_edit_request(body: EditRequestIn, request: Request, member: Member = Depends(require_active_member),
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.scalar(select(EditRequest.id).where(EditRequest.member_id == member.id,
                                              EditRequest.status == EditRequestStatus.PENDING)):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have a pending edit request")
    if svc.active_edit_permission(db, member.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have active editing access")
    er = EditRequest(member_id=member.id, requested_by_id=user.id, reason=body.reason.strip())
    db.add(er)
    db.flush()
    audit(db, user, "edit_request.create", "edit_request", er.id, request=request)
    notify(db, user, "edit_request_submitted", channels=("web",), link="/dashboard/membership")
    notify_admins(db, "admin_edit_request", {"name": member.profile.full_name, "reason": er.reason,
                                             "membership_number": member.membership_number},
                  link="/admin/edit-requests")
    db.commit()
    db.refresh(er)
    return edit_request_out(er)


@router.put("/members/profile", response_model=MyMembershipOut,
            summary="Update my details (only inside an approved 24-hour window – enforced server-side)")
def update_my_profile(body: MemberProfileUpdateIn, request: Request, member: Member = Depends(require_active_member),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perm = svc.active_edit_permission(db, member.id, lock=True)
    if not perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "You do not have active editing permission. Please submit a profile edit request.")
    profile = member.profile
    data = body.model_dump(exclude_unset=True, exclude={"introducer_name", "introducer_phone", "introducer_reg_no"})
    changes = svc.apply_form_data(profile, data)
    errors = svc.validate_form_completeness(profile, require_introducer=False)
    if errors:
        db.rollback()
        raise svc.unprocessable("Please correct the highlighted fields", errors)
    if changes:
        perm.last_used_at = utcnow()
        svc.record_changes(db, member, changes, user, ChangeSource.MEMBER_EDIT, perm)
        audit(db, user, "member.self_edit", "member", member.id, {"fields": [c[0] for c in changes]}, request)
        labels = ", ".join(c[0].replace("_", " ") for c in changes)
        notify_admins(db, "admin_member_edited", {"name": profile.full_name, "fields": labels,
                                                  "membership_number": member.membership_number},
                      link=f"/admin/members/{member.id}")
    db.commit()
    db.refresh(member)
    return svc.my_membership_out(db, member)


@router.post("/members/profile/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Replace my photograph/document during an approved edit window")
async def upload_my_document(request: Request, doc_type: DocumentType = Form(...), file: UploadFile = File(...),
                             member: Member = Depends(require_active_member), user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    perm = svc.active_edit_permission(db, member.id, lock=True)
    if not perm:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have active editing permission")
    stored = await storage.validate_and_store(file, doc_type)
    profile = member.profile
    for old in profile.documents:
        if old.doc_type == doc_type and old.is_current:
            old.is_current = False
    doc = ApplicationDocument(member_profile_id=profile.id, doc_type=doc_type, storage_key=stored.storage_key,
                              original_filename=stored.original_filename, content_type=stored.content_type,
                              size_bytes=stored.size_bytes, sha256=stored.sha256, uploaded_by_id=user.id)
    db.add(doc)
    db.flush()
    svc.record_changes(db, member, [(f"document:{doc_type.value}", None, stored.original_filename)], user,
                       ChangeSource.MEMBER_EDIT, perm)
    perm.last_used_at = utcnow()
    audit(db, user, "member.self_upload", "member", member.id, {"doc_type": doc_type.value}, request)
    notify_admins(db, "admin_member_edited", {"name": profile.full_name, "fields": f"document {doc_type.value}",
                                              "membership_number": member.membership_number},
                  link=f"/admin/members/{member.id}")
    db.commit()
    return svc.doc_out(doc)


@router.get("/members/{member_id}", response_model=DirectoryMemberOut,
            summary="Member profile (approved members & admins only)")
def member_detail(member_id: int, _: User = Depends(require_member_or_admin), db: Session = Depends(get_db)):
    m = db.get(Member, member_id)
    if not m or m.status != MembershipStatus.ACTIVE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return svc.directory_out(m)


# --- Private files ------------------------------------------------------------------
files_router = APIRouter(tags=["Private Files"])


@files_router.get("/files/{doc_id}", summary="Download a private document (authorisation enforced)",
                  response_class=FileResponse)
def download_file(doc_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    not_found = HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    doc = db.get(ApplicationDocument, doc_id)
    if not doc:
        raise not_found
    allowed = user.is_admin
    if not allowed and doc.application_id:
        app = db.get(MemberApplication, doc.application_id)
        allowed = app is not None and app.user_id == user.id
    if not allowed and doc.member_profile_id:
        profile = db.get(MemberProfile, doc.member_profile_id)
        if profile and profile.user_id == user.id:
            allowed = True
        elif (profile and doc.doc_type == DocumentType.PHOTO and doc.is_current and profile.member
              and profile.member.status == MembershipStatus.ACTIVE and get_active_member_for_user(db, user)):
            allowed = True  # directory photo visible to approved members
    if not allowed:
        raise not_found  # do not reveal existence
    path = storage.resolve_path(doc.storage_key)
    if not path.exists():
        raise not_found
    return FileResponse(path, media_type=doc.content_type, filename=doc.original_filename,
                        content_disposition_type="inline",
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
