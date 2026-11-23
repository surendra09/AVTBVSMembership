from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.session import get_db
from app.models import (
    APPLICANT_EDITABLE_STATUSES, OPEN_STATUSES, ApplicationDocument, ApplicationStatus, DocumentType,
    MemberApplication, MemberProfile, Role, User,
)
from app.schemas.membership import ApplicationOut, ApplicationSaveIn, DocumentOut
from app.services import numbering, storage
from app.services import membership as svc
from app.services.audit import audit

router = APIRouter(prefix="/applications", tags=["Membership Applications"])


def _own_application(db: Session, app_id: int, user: User, lock: bool = False) -> MemberApplication:
    stmt = select(MemberApplication).where(MemberApplication.id == app_id, MemberApplication.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    app = db.scalar(stmt)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


def _require_editable(app: MemberApplication) -> None:
    if app.status not in APPLICANT_EDITABLE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This application can no longer be edited. Edits are only possible while it is a draft "
                            "or when the office has requested corrections.")


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED,
             summary="Start a membership application (saved as DRAFT)")
def create_application(body: ApplicationSaveIn, request: Request, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    if user.role != Role.USER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator accounts cannot apply for membership")
    profile = db.scalar(select(MemberProfile).where(MemberProfile.user_id == user.id))
    if profile and profile.member:
        raise HTTPException(status.HTTP_409_CONFLICT, "You are already an official member")
    existing = db.scalar(select(MemberApplication).where(MemberApplication.user_id == user.id,
                                                         MemberApplication.status.in_(OPEN_STATUSES)))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an application in progress")
    app = MemberApplication(application_number=numbering.next_application_number(db), user_id=user.id,
                            status=ApplicationStatus.DRAFT, full_name=user.full_name, cell=user.phone,
                            email=user.email, father_name="", address_line1="", city="", state="", country="India",
                            pincode="")
    data = body.model_dump(exclude_unset=True)
    svc.apply_form_data(app, data)
    # NOT NULL columns may be empty strings while in draft
    for f in ("father_name", "address_line1", "city", "state", "pincode", "full_name", "cell", "country"):
        if getattr(app, f) is None:
            setattr(app, f, "")
    app.date_of_birth = app.date_of_birth or None
    db.add(app)
    db.flush()
    svc.add_history(db, app, "CREATED", user, None)
    audit(db, user, "application.create", "application", app.id, request=request)
    db.commit()
    db.refresh(app)
    return svc.application_out(app)


@router.get("/me", response_model=ApplicationOut | None, summary="My latest application (null if none)")
def my_application(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.scalar(select(MemberApplication).where(MemberApplication.user_id == user.id)
                    .order_by(MemberApplication.id.desc()))
    return svc.application_out(app) if app else None


@router.get("/{app_id}", response_model=ApplicationOut, summary="One of my applications")
def get_application(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.application_out(_own_application(db, app_id, user))


@router.put("/{app_id}", response_model=ApplicationOut,
            summary="Save changes (only while DRAFT or CORRECTION_REQUIRED)")
def update_application(app_id: int, body: ApplicationSaveIn, request: Request,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _own_application(db, app_id, user, lock=True)
    _require_editable(app)
    data = body.model_dump(exclude_unset=True)
    for f in ("father_name", "address_line1", "city", "state", "pincode", "full_name", "cell", "country"):
        if f in data and data[f] is None:
            data[f] = ""
    changes = svc.apply_form_data(app, data)
    if changes:
        audit(db, user, "application.update", "application", app.id,
              {"fields": [c[0] for c in changes]}, request)
    db.commit()
    db.refresh(app)
    return svc.application_out(app)


@router.post("/{app_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Upload / replace a photograph or document")
async def upload_document(app_id: int, request: Request, doc_type: DocumentType = Form(...),
                          file: UploadFile = File(...), user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    app = _own_application(db, app_id, user, lock=True)
    _require_editable(app)
    stored = await storage.validate_and_store(file, doc_type)
    for old in app.documents:
        if old.doc_type == doc_type and old.is_current:
            old.is_current = False
    doc = ApplicationDocument(application_id=app.id, doc_type=doc_type, storage_key=stored.storage_key,
                              original_filename=stored.original_filename, content_type=stored.content_type,
                              size_bytes=stored.size_bytes, sha256=stored.sha256, uploaded_by_id=user.id)
    db.add(doc)
    db.flush()
    audit(db, user, "application.upload", "application", app.id, {"doc_type": doc_type.value}, request)
    db.commit()
    return svc.doc_out(doc)


@router.delete("/{app_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(app_id: int, doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _own_application(db, app_id, user, lock=True)
    _require_editable(app)
    doc = db.get(ApplicationDocument, doc_id)
    if not doc or doc.application_id != app.id or not doc.is_current:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    doc.is_current = False
    db.commit()


@router.post("/{app_id}/submit", response_model=ApplicationOut, summary="Submit a DRAFT application (→ PENDING)")
def submit(app_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _own_application(db, app_id, user, lock=True)
    if app.status != ApplicationStatus.DRAFT:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft applications can be submitted")
    svc.submit_application(db, app, user, request)
    db.commit()
    db.refresh(app)
    return svc.application_out(app)


@router.post("/{app_id}/resubmit", response_model=ApplicationOut,
             summary="Resubmit after corrections (CORRECTION_REQUIRED → RESUBMITTED)")
def resubmit(app_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = _own_application(db, app_id, user, lock=True)
    if app.status != ApplicationStatus.CORRECTION_REQUIRED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only applications with requested corrections can be resubmitted")
    svc.submit_application(db, app, user, request)
    db.commit()
    db.refresh(app)
    return svc.application_out(app)
