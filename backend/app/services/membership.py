"""Core membership business logic: applications, approval, members, editing."""
from datetime import date, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import keyed_hash, mask_aadhaar
from app.database.types import utcnow
from app.models import (
    APPLICANT_EDITABLE_STATUSES, FORM_FIELD_NAMES, REVIEWABLE_STATUSES, ApplicationDocument, ApplicationHistory,
    ApplicationStatus, ChangeSource, DocumentType, EditPermission, Member, MemberApplication, MemberChangeHistory,
    MemberProfile, MembershipStatus, MemberSource, User,
)
from app.schemas.membership import (
    AdminApplicationOut, AdminMemberOut, ApplicationListItem, ApplicationOut, DirectoryMemberOut, DocumentOut,
    HistoryOut, IntroducerCheck, MyMembershipOut,
)
from app.services import numbering
from app.services.audit import audit
from app.services.notifications import notify, notify_admins
from app.utils.validators import age_on, is_valid_pincode

REQUIRED_FIELDS = {
    "full_name": "Name", "father_name": "Father's Name", "address_line1": "Address", "city": "City/Town/Village",
    "state": "State", "country": "Country", "pincode": "Pincode", "date_of_birth": "Date of Birth",
    "cell": "Cell (mobile number)",
}
INTRODUCER_FIELDS = {
    "introducer_name": "Introduced by Sri", "introducer_phone": "Introducer Phone No.",
    "introducer_reg_no": "Introducer Registration No.",
}
REQUIRED_DOCUMENTS = {
    DocumentType.PHOTO: "Recent passport-size photograph",
    DocumentType.ID_PROOF: "Identity proof",
    # The two additional passport photos are not collected by the application
    # form (see frontend ApplicationPage DOCS), so they are not required here.
    DocumentType.APPLICANT_SIGNATURE: "Applicant signature",
}
SENSITIVE_FIELDS = {"aadhaar_number"}


def unprocessable(message: str, errors: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(422, {"message": message, "errors": errors or {}})


# --- Serialisation ---------------------------------------------------------------
def doc_url(doc: ApplicationDocument) -> str:
    return f"{settings.API_PREFIX}/files/{doc.id}"


def doc_out(doc: ApplicationDocument) -> DocumentOut:
    return DocumentOut(id=doc.id, doc_type=doc.doc_type, original_filename=doc.original_filename,
                       content_type=doc.content_type, size_bytes=doc.size_bytes, created_at=doc.created_at,
                       url=doc_url(doc))


def current_docs(docs: list[ApplicationDocument]) -> list[ApplicationDocument]:
    return sorted([d for d in docs if d.is_current], key=lambda d: d.doc_type.value)


def photo_of(docs: list[ApplicationDocument]) -> ApplicationDocument | None:
    return next((d for d in docs if d.is_current and d.doc_type == DocumentType.PHOTO), None)


def form_data(obj) -> dict:
    data = {f: getattr(obj, f) for f in FORM_FIELD_NAMES if f != "aadhaar_number"}
    data["aadhaar_masked"] = f"XXXX XXXX {obj.aadhaar_last4}" if obj.aadhaar_last4 else None
    return data


def history_out(h: ApplicationHistory) -> HistoryOut:
    return HistoryOut(id=h.id, action=h.action, from_status=h.from_status, to_status=h.to_status, note=h.note,
                      actor_name=h.actor.full_name if h.actor else None, created_at=h.created_at)


def application_out(app: MemberApplication) -> ApplicationOut:
    return ApplicationOut(
        **form_data(app), id=app.id, application_number=app.application_number, status=app.status,
        declaration_accepted=app.declaration_accepted, declaration_place=app.declaration_place,
        declaration_date=app.declaration_date, correction_notes=app.correction_notes,
        rejection_reason=app.rejection_reason, submitted_at=app.submitted_at, last_submitted_at=app.last_submitted_at,
        reviewed_at=app.reviewed_at, created_at=app.created_at, updated_at=app.updated_at,
        can_edit=app.status in APPLICANT_EDITABLE_STATUSES,
        documents=[doc_out(d) for d in current_docs(app.documents)],
        history=[history_out(h) for h in app.history],
        membership_number=app.member.membership_number if app.member else None,
    )


def introducer_check(db: Session, app: MemberApplication) -> IntroducerCheck:
    if not app.introducer_reg_no:
        return IntroducerCheck(registration_number_found=False)
    m = db.scalar(select(Member).where(Member.membership_number == app.introducer_reg_no))
    if not m:
        return IntroducerCheck(registration_number_found=False)
    p = m.profile
    phones = {x for x in (p.cell, p.phone) if x}
    return IntroducerCheck(registration_number_found=True, member_name=p.full_name, member_status=m.status,
                           phone_matches=(app.introducer_phone in phones) if app.introducer_phone else None)


def duplicate_aadhaar_numbers(db: Session, aadhaar_hash: str | None, exclude_profile_id: int | None = None) -> list[str]:
    if not aadhaar_hash:
        return []
    stmt = (select(Member.membership_number).join(MemberProfile, Member.member_profile_id == MemberProfile.id)
            .where(MemberProfile.aadhaar_hash == aadhaar_hash))
    if exclude_profile_id:
        stmt = stmt.where(MemberProfile.id != exclude_profile_id)
    return list(db.scalars(stmt))


def admin_application_out(db: Session, app: MemberApplication) -> AdminApplicationOut:
    base = application_out(app).model_dump()
    return AdminApplicationOut(
        **base, aadhaar_number=app.aadhaar_number, applicant_user_id=app.user_id,
        applicant_account_name=app.user.full_name, applicant_account_email=app.user.email,
        applicant_account_phone=app.user.phone, reviewed_by_name=app.reviewed_by.full_name if app.reviewed_by else None,
        introducer_check=introducer_check(db, app),
        age_years=age_on(app.date_of_birth) if app.date_of_birth else None,
        duplicate_aadhaar_member_numbers=duplicate_aadhaar_numbers(db, app.aadhaar_hash),
        member_id=app.member.id if app.member else None,
    )


def application_list_item(app: MemberApplication) -> ApplicationListItem:
    photo = photo_of(app.documents)
    return ApplicationListItem(
        id=app.id, application_number=app.application_number, full_name=app.full_name, father_name=app.father_name,
        city=app.city, cell=app.cell, introducer_reg_no=app.introducer_reg_no, status=app.status,
        submitted_at=app.submitted_at, last_submitted_at=app.last_submitted_at, updated_at=app.updated_at,
        photo_url=doc_url(photo) if photo else None,
    )


# --- Form updates ----------------------------------------------------------------
def _stringify(field: str, value) -> str | None:
    if value is None:
        return None
    if field in SENSITIVE_FIELDS:
        return mask_aadhaar(str(value))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def apply_form_data(target, data: dict) -> list[tuple[str, str | None, str | None]]:
    """Apply validated form values; returns [(field, old, new)] for actual changes."""
    changes = []
    for field, value in data.items():
        if field not in FORM_FIELD_NAMES and field not in ("declaration_place", "declaration_date",
                                                         "declaration_accepted"):
            continue
        if isinstance(value, str) and value == "":
            value = None
        if field in ("show_contact_in_directory", "show_address_in_directory", "declaration_accepted") \
                and value is None:
            continue
        old = getattr(target, field)
        if old == value:
            continue
        setattr(target, field, value)
        if field == "aadhaar_number":
            target.aadhaar_last4 = value[-4:] if value else None
            target.aadhaar_hash = keyed_hash(value) if value else None
        changes.append((field, _stringify(field, old), _stringify(field, value)))
    return changes


def validate_form_completeness(obj, require_introducer: bool = True) -> dict[str, str]:
    errors: dict[str, str] = {}
    for field, label in REQUIRED_FIELDS.items():
        if not getattr(obj, field):
            errors[field] = f"{label} is required"
    if require_introducer:
        for field, label in INTRODUCER_FIELDS.items():
            if not getattr(obj, field):
                errors[field] = f"{label} is mandatory"
    if obj.pincode and not is_valid_pincode(obj.pincode, obj.country):
        errors["pincode"] = "Enter a valid pincode (6 digits for India)"
    if obj.date_of_birth:
        if obj.date_of_birth > date.today():
            errors["date_of_birth"] = "Date of birth cannot be in the future"
        elif age_on(obj.date_of_birth) < settings.MINIMUM_AGE_YEARS:
            errors["date_of_birth"] = f"Applicant must have completed {settings.MINIMUM_AGE_YEARS} years"
        elif age_on(obj.date_of_birth) > 120:
            errors["date_of_birth"] = "Enter a valid date of birth"
    return errors


def validate_submission(db: Session, app: MemberApplication, user: User) -> None:
    errors = validate_form_completeness(app, require_introducer=True)
    if not app.declaration_accepted:
        errors["declaration_accepted"] = "You must confirm the declaration"
    if not app.declaration_place:
        errors["declaration_place"] = "Place is required"
    if not app.declaration_date:
        errors["declaration_date"] = "Date is required"
    elif app.declaration_date > date.today() + timedelta(days=1):
        errors["declaration_date"] = "Declaration date cannot be in the future"
    if app.introducer_reg_no and settings.INTRODUCER_MUST_BE_REGISTERED:
        m = db.scalar(select(Member).where(Member.membership_number == app.introducer_reg_no,
                                           Member.status == MembershipStatus.ACTIVE))
        if not m:
            errors["introducer_reg_no"] = "No active member found with this registration number"
    have = {d.doc_type for d in app.documents if d.is_current}
    required_docs = dict(REQUIRED_DOCUMENTS)
    if settings.REQUIRE_INTRODUCER_SIGNATURE:
        required_docs[DocumentType.INTRODUCER_SIGNATURE] = "Introducer signature"
    for doc_type, label in required_docs.items():
        if doc_type not in have:
            errors[f"document_{doc_type.value}"] = f"{label} must be uploaded"
    if settings.REQUIRE_VERIFIED_CONTACT_FOR_SUBMISSION:
        # E-mail is optional and not verified; only the mobile number must be confirmed.
        if not user.phone_verified_at:
            errors["account_phone"] = "Verify your mobile number before submitting"
    if errors:
        raise unprocessable("Please complete all mandatory fields before submitting", errors)


def add_history(db: Session, app: MemberApplication, action: str, actor: User | None,
                from_status: ApplicationStatus | None, note: str | None = None) -> None:
    db.add(ApplicationHistory(application_id=app.id, action=action, actor_id=actor.id if actor else None,
                              from_status=from_status.value if from_status else None, to_status=app.status.value,
                              note=note))


# --- Applicant actions -----------------------------------------------------------
def submit_application(db: Session, app: MemberApplication, user: User, request: Request | None) -> None:
    if app.status not in APPLICANT_EDITABLE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Application cannot be submitted while {app.status.value}")
    validate_submission(db, app, user)
    previous = app.status
    now = utcnow()
    resubmission = previous == ApplicationStatus.CORRECTION_REQUIRED
    app.status = ApplicationStatus.RESUBMITTED if resubmission else ApplicationStatus.PENDING
    app.submitted_at = app.submitted_at or now
    app.last_submitted_at = now
    app.submission_count += 1
    add_history(db, app, "RESUBMITTED" if resubmission else "SUBMITTED", user, previous)
    audit(db, user, "application.resubmit" if resubmission else "application.submit", "application", app.id,
          request=request)
    ctx = {"application_number": app.application_number, "name": app.full_name or user.full_name}
    if resubmission:
        notify(db, user, "application_resubmitted", ctx, link="/dashboard/application")
        notify_admins(db, "admin_application_resubmitted", ctx, link=f"/admin/applications/{app.id}")
    else:
        notify(db, user, "application_submitted", ctx, link="/dashboard/application")
        notify_admins(db, "admin_new_application", ctx, link=f"/admin/applications/{app.id}")


# --- Admin review ----------------------------------------------------------------
def _lock_application(db: Session, app_id: int) -> MemberApplication:
    app = db.scalar(select(MemberApplication).where(MemberApplication.id == app_id).with_for_update())
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return app


def _require_reviewable(app: MemberApplication) -> None:
    if app.status not in REVIEWABLE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Only PENDING or RESUBMITTED applications can be reviewed (current: {app.status.value})")


def approve_application(db: Session, app_id: int, admin: User, office: dict, note: str | None,
                        request: Request | None) -> Member:
    """Atomic: lock application → allocate number → create profile + member → history/audit/notifications."""
    # Lock order (always the same, avoids deadlocks): application -> applicant user -> number sequence.
    app = _lock_application(db, app_id)
    _require_reviewable(app)
    user = db.scalar(select(User).where(User.id == app.user_id).with_for_update())
    existing_profile = db.scalar(select(MemberProfile).where(MemberProfile.user_id == user.id))
    if existing_profile and existing_profile.member:
        raise HTTPException(status.HTTP_409_CONFLICT, "This user already has an official membership")

    errors = validate_form_completeness(app, require_introducer=True)
    if errors:
        raise unprocessable("Application is incomplete and cannot be approved", errors)

    number = numbering.next_membership_number(db)  # holds the sequence row lock until commit

    profile = existing_profile or MemberProfile(user_id=user.id)
    for field in FORM_FIELD_NAMES:
        setattr(profile, field, getattr(app, field))
    profile.aadhaar_last4, profile.aadhaar_hash = app.aadhaar_last4, app.aadhaar_hash
    profile.declaration_place, profile.declaration_date = app.declaration_place, app.declaration_date
    db.add(profile)
    db.flush()

    member = Member(member_profile_id=profile.id, membership_number=number, status=MembershipStatus.ACTIVE,
                    source=MemberSource.ONLINE_APPLICATION, application_id=app.id, approved_by_id=admin.id,
                    enrolled_at=utcnow(), **office)
    db.add(member)
    for doc in app.documents:
        if doc.is_current:
            doc.member_profile_id = profile.id

    previous = app.status
    app.status = ApplicationStatus.APPROVED
    app.reviewed_at = utcnow()
    app.reviewed_by_id = admin.id
    app.correction_notes = None
    db.flush()
    add_history(db, app, "APPROVED", admin, previous, note=f"Membership number {number}" + (f". {note}" if note else ""))
    audit(db, admin, "application.approve", "application", app.id,
          {"membership_number": number, "member_id": member.id}, request)
    ctx = {"application_number": app.application_number, "membership_number": number,
           "name": profile.full_name}
    notify(db, user, "application_approved", ctx, link="/dashboard")
    notify(db, user, "membership_number_assigned", ctx, channels=("web",), link="/dashboard/membership")
    return member


def request_corrections(db: Session, app_id: int, admin: User, notes: str, request: Request | None) -> MemberApplication:
    app = _lock_application(db, app_id)
    _require_reviewable(app)
    previous = app.status
    app.status = ApplicationStatus.CORRECTION_REQUIRED
    app.correction_notes = notes.strip()
    app.reviewed_at = utcnow()
    app.reviewed_by_id = admin.id
    add_history(db, app, "CORRECTION_REQUESTED", admin, previous, note=notes.strip())
    audit(db, admin, "application.request_corrections", "application", app.id, request=request)
    notify(db, app.user, "application_correction_required",
           {"application_number": app.application_number, "notes": notes.strip()}, link="/dashboard/application")
    return app


def reject_application(db: Session, app_id: int, admin: User, reason: str, request: Request | None) -> MemberApplication:
    app = _lock_application(db, app_id)
    _require_reviewable(app)
    previous = app.status
    app.status = ApplicationStatus.REJECTED
    app.rejection_reason = reason.strip()
    app.reviewed_at = utcnow()
    app.reviewed_by_id = admin.id
    add_history(db, app, "REJECTED", admin, previous, note=reason.strip())
    audit(db, admin, "application.reject", "application", app.id, request=request)
    notify(db, app.user, "application_rejected",
           {"application_number": app.application_number, "reason": reason.strip()}, link="/dashboard/application")
    return app


# --- Manual existing members -------------------------------------------------------
OFFICE_FIELDS = ["verified_by", "receipt_number", "receipt_date", "committee_chairman", "committee_secretary",
                 "committee_president", "office_notes"]


def create_manual_member(db: Session, data: dict, admin: User, request: Request | None) -> Member:
    number = data.pop("membership_number").strip()
    enrolled_on = data.pop("enrolled_on", None)
    office = {k: data.pop(k, None) for k in OFFICE_FIELDS}
    if db.scalar(select(Member.id).where(Member.membership_number == number)):
        raise unprocessable("Membership number already exists", {"membership_number": "This number is already in use"})
    profile = MemberProfile(user_id=None)
    apply_form_data(profile, data)
    if profile.country is None:
        profile.country = "India"
    errors = validate_form_completeness(profile, require_introducer=False)
    if errors:
        raise unprocessable("Please complete the mandatory fields", errors)
    db.add(profile)
    db.flush()
    enrolled = datetime.combine(enrolled_on, datetime.min.time()) if enrolled_on else utcnow()
    member = Member(member_profile_id=profile.id, membership_number=number, status=MembershipStatus.ACTIVE,
                    source=MemberSource.MANUAL_ENTRY, approved_by_id=admin.id, enrolled_at=enrolled, **office)
    db.add(member)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise unprocessable("Membership number already exists",
                            {"membership_number": "This number is already in use"}) from None
    audit(db, admin, "member.manual_add", "member", member.id, {"membership_number": number}, request)
    return member


def record_changes(db: Session, member: Member, changes, actor: User, source: ChangeSource,
                   permission: EditPermission | None = None) -> None:
    for field, old, new in changes:
        db.add(MemberChangeHistory(member_id=member.id, member_profile_id=member.member_profile_id,
                                   edit_permission_id=permission.id if permission else None, changed_by_id=actor.id,
                                   source=source, field_name=field, old_value=old, new_value=new))


# --- Editing permission ------------------------------------------------------------
def active_edit_permission(db: Session, member_id: int, lock: bool = False) -> EditPermission | None:
    now = utcnow()
    stmt = (select(EditPermission)
            .where(EditPermission.member_id == member_id, EditPermission.revoked_at.is_(None),
                   EditPermission.starts_at <= now, EditPermission.expires_at > now)
            .order_by(EditPermission.expires_at.desc()))
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


# --- Member views -------------------------------------------------------------------
def directory_out(member: Member) -> DirectoryMemberOut:
    p = member.profile
    photo = photo_of(p.documents)
    out = DirectoryMemberOut(
        id=member.id, membership_number=member.membership_number, full_name=p.full_name, father_name=p.father_name,
        photo_url=doc_url(photo) if photo else None, city=p.city, state=p.state, country=p.country,
        blood_group=p.blood_group, family_surname=p.family_surname, gothram=p.gothram, natchathiram=p.natchathiram,
        occupation=p.occupation, native_place_address=p.native_place_address, enrolled_at=member.enrolled_at,
    )
    if p.show_contact_in_directory:
        out.cell, out.phone, out.email, out.whatsapp_facebook = p.cell, p.phone, p.email, p.whatsapp_facebook
    if p.show_address_in_directory:
        out.address_line1, out.address_line2, out.pincode = p.address_line1, p.address_line2, p.pincode
        out.occupation_address = p.occupation_address
    return out


def my_membership_out(db: Session, member: Member) -> MyMembershipOut:
    from app.models import EditRequest, EditRequestStatus

    p = member.profile
    perm = active_edit_permission(db, member.id)
    pending = db.scalar(select(EditRequest.id).where(EditRequest.member_id == member.id,
                                                     EditRequest.status == EditRequestStatus.PENDING))
    photo = photo_of(p.documents)
    return MyMembershipOut(
        **form_data(p), member_id=member.id, membership_number=member.membership_number, status=member.status,
        source=member.source, enrolled_at=member.enrolled_at, declaration_place=p.declaration_place,
        declaration_date=p.declaration_date, photo_url=doc_url(photo) if photo else None,
        documents=[doc_out(d) for d in current_docs(p.documents)],
        edit_permission_expires_at=perm.expires_at if perm else None, edit_permission_active=perm is not None,
        pending_edit_request=pending is not None,
    )


def admin_member_out(db: Session, member: Member) -> AdminMemberOut:
    p = member.profile
    photo = photo_of(p.documents)
    perm = active_edit_permission(db, member.id)
    history = db.scalars(select(MemberChangeHistory).where(MemberChangeHistory.member_id == member.id)
                         .order_by(MemberChangeHistory.id.desc()).limit(200)).all()
    return AdminMemberOut(
        **form_data(p), **{k: getattr(member, k) for k in OFFICE_FIELDS},
        member_id=member.id, member_profile_id=p.id, membership_number=member.membership_number,
        status=member.status, source=member.source, enrolled_at=member.enrolled_at, aadhaar_number=p.aadhaar_number,
        declaration_place=p.declaration_place, declaration_date=p.declaration_date,
        application_id=member.application_id,
        application_number=member.application.application_number if member.application else None,
        linked_user_id=p.user_id, linked_user_email=p.user.email if p.user else None,
        approved_by_name=member.approved_by.full_name if member.approved_by else None,
        deactivated_at=member.deactivated_at, deactivation_reason=member.deactivation_reason,
        photo_url=doc_url(photo) if photo else None, documents=[doc_out(d) for d in current_docs(p.documents)],
        change_history=[{"id": h.id, "field": h.field_name, "old": h.old_value, "new": h.new_value,
                         "source": h.source.value, "changed_by": h.changed_by.full_name if h.changed_by else None,
                         "at": h.created_at.isoformat()} for h in history],
        edit_permission_expires_at=perm.expires_at if perm else None,
    )
