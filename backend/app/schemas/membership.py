"""Schemas for the official membership form, applications and members."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import (
    ApplicationStatus, DocumentType, EditRequestStatus, MemberSource, MembershipStatus,
)
from app.schemas.common import ORMModel
from app.utils.validators import (
    clean_multiline, clean_text, is_valid_aadhaar, is_valid_blood_group, is_valid_phone, normalize_aadhaar,
    normalize_phone,
)

SINGLE_LINE = ["full_name", "father_name", "address_line1", "address_line2", "city", "state", "country",
               "family_surname", "gothram", "natchathiram", "occupation", "introducer_name",
               "introducer_reg_no", "whatsapp_facebook", "centre_x_no", "declaration_place", "pincode"]
MULTI_LINE = ["occupation_address", "native_place_address"]
PHONES = ["phone", "cell", "introducer_phone"]


class MembershipFormIn(BaseModel):
    """All fields of the LIFE MEMBERSHIP APPLICATION FORM.

    Every field is optional here so drafts can be saved; completeness (including
    the three mandatory introducer fields) is enforced on submission.
    """

    model_config = ConfigDict(str_max_length=2000)

    # PERSONAL DETAILS
    full_name: str | None = Field(None, max_length=150, description="Name")
    father_name: str | None = Field(None, max_length=150, description="Father's Name")
    address_line1: str | None = Field(None, max_length=255, description="Address (line 1)")
    address_line2: str | None = Field(None, max_length=255, description="Address (line 2)")
    city: str | None = Field(None, max_length=120, description="City/Town/Village")
    state: str | None = Field(None, max_length=120)
    country: str | None = Field(None, max_length=120)
    pincode: str | None = Field(None, max_length=12)
    aadhaar_number: str | None = Field(None, description="Aadhar Card No. (12 digits). Encrypted at rest.")
    blood_group: str | None = None
    date_of_birth: date | None = Field(None, description="D.O.B.")
    # CONTACT DETAILS
    phone: str | None = Field(None, description="Phone (landline)")
    centre_x_no: str | None = Field(None, max_length=30, description="Centre X No.")
    cell: str | None = Field(None, description="Cell (mobile)")
    email: EmailStr | None = Field(None, description="E.Mail")
    whatsapp_facebook: str | None = Field(None, max_length=255, description="Whatsapp/Face Book")
    # FAMILY DETAILS
    family_surname: str | None = Field(None, max_length=120)
    gothram: str | None = Field(None, max_length=120)
    natchathiram: str | None = Field(None, max_length=120)
    # PROFESSIONAL DETAILS
    occupation: str | None = Field(None, max_length=150)
    occupation_address: str | None = Field(None, max_length=1000)
    # NATIVE PLACE
    native_place_address: str | None = Field(None, max_length=1000)
    # INTRODUCER DETAILS
    introducer_name: str | None = Field(None, max_length=150, description="Introduced by Sri")
    introducer_phone: str | None = Field(None, description="Introducer Phone No.")
    introducer_reg_no: str | None = Field(None, max_length=50, description="Introducer's Reg. No. (membership no.)")
    # Directory privacy preferences
    show_contact_in_directory: bool | None = None
    show_address_in_directory: bool | None = None

    @field_validator(*SINGLE_LINE, check_fields=False)
    @classmethod
    def _single(cls, v):
        return clean_text(v) if isinstance(v, str) else v

    @field_validator(*MULTI_LINE)
    @classmethod
    def _multi(cls, v):
        return clean_multiline(v) if isinstance(v, str) else v

    @field_validator(*PHONES)
    @classmethod
    def _phone(cls, v):
        if v is None or v == "":
            return None
        v = normalize_phone(v)
        if v and not is_valid_phone(v):
            raise ValueError("Enter a valid phone number (7–15 digits, optional +country code)")
        return v

    @field_validator("aadhaar_number")
    @classmethod
    def _aadhaar(cls, v):
        if v is None or v == "":
            return v
        v = normalize_aadhaar(v)
        if v and not is_valid_aadhaar(v):
            raise ValueError("Enter a valid 12-digit Aadhaar number")
        return v

    @field_validator("blood_group")
    @classmethod
    def _bg(cls, v):
        if v in (None, ""):
            return None
        if not is_valid_blood_group(v):
            raise ValueError("Select a valid blood group")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        if v in ("", None):
            return None
        return v.strip().lower() if isinstance(v, str) else v


class DeclarationIn(BaseModel):
    declaration_accepted: bool | None = None
    declaration_place: str | None = Field(None, max_length=120)
    declaration_date: date | None = None

    @field_validator("declaration_place")
    @classmethod
    def _p(cls, v):
        return clean_text(v) if isinstance(v, str) else v


class ApplicationSaveIn(MembershipFormIn, DeclarationIn):
    pass


class DocumentOut(ORMModel):
    id: int
    doc_type: DocumentType
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    url: str


class HistoryOut(BaseModel):
    id: int
    action: str
    from_status: str | None
    to_status: str | None
    note: str | None
    actor_name: str | None
    created_at: datetime


class FormDataOut(BaseModel):
    full_name: str | None = None
    father_name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    pincode: str | None = None
    aadhaar_masked: str | None = None
    blood_group: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None
    centre_x_no: str | None = None
    cell: str | None = None
    email: str | None = None
    whatsapp_facebook: str | None = None
    family_surname: str | None = None
    gothram: str | None = None
    natchathiram: str | None = None
    occupation: str | None = None
    occupation_address: str | None = None
    native_place_address: str | None = None
    introducer_name: str | None = None
    introducer_phone: str | None = None
    introducer_reg_no: str | None = None
    show_contact_in_directory: bool = True
    show_address_in_directory: bool = True


class ApplicationOut(FormDataOut):
    """Applicant's own view of their application (Aadhaar masked)."""

    id: int
    application_number: str
    status: ApplicationStatus
    declaration_accepted: bool
    declaration_place: str | None
    declaration_date: date | None
    correction_notes: str | None
    rejection_reason: str | None
    submitted_at: datetime | None
    last_submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_edit: bool
    documents: list[DocumentOut]
    history: list[HistoryOut]
    membership_number: str | None = None


class IntroducerCheck(BaseModel):
    registration_number_found: bool
    member_name: str | None = None
    member_status: MembershipStatus | None = None
    phone_matches: bool | None = None


class AdminApplicationOut(ApplicationOut):
    """Full view for Admins – includes the decrypted Aadhaar for verification."""

    aadhaar_number: str | None = None
    applicant_user_id: int
    applicant_account_name: str
    applicant_account_email: str | None
    applicant_account_phone: str
    reviewed_by_name: str | None = None
    introducer_check: IntroducerCheck
    age_years: int | None = None
    duplicate_aadhaar_member_numbers: list[str] = []
    member_id: int | None = None


class ApplicationListItem(BaseModel):
    id: int
    application_number: str
    full_name: str | None
    father_name: str | None
    city: str | None
    cell: str | None
    introducer_reg_no: str | None
    status: ApplicationStatus
    submitted_at: datetime | None
    last_submitted_at: datetime | None
    updated_at: datetime
    photo_url: str | None = None


class OfficeUseIn(BaseModel):
    """OFFICE USE ONLY section – editable by Admins only."""

    verified_by: str | None = Field(None, max_length=150)
    receipt_number: str | None = Field(None, max_length=50, description="Rec. No.")
    receipt_date: date | None = None
    committee_chairman: str | None = Field(None, max_length=150)
    committee_secretary: str | None = Field(None, max_length=150)
    committee_president: str | None = Field(None, max_length=150)
    office_notes: str | None = Field(None, max_length=2000)


class ApproveIn(OfficeUseIn):
    note: str | None = Field(None, max_length=2000)


class CorrectionIn(BaseModel):
    notes: str = Field(min_length=10, max_length=4000, description="Describe exactly what must be corrected")


class RejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=4000)


class ManualMemberIn(MembershipFormIn, OfficeUseIn):
    """Admin entry of an existing (paper) member with their existing number."""

    membership_number: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=2, max_length=150)
    father_name: str = Field(min_length=2, max_length=150)
    address_line1: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    country: str = Field("India", min_length=2, max_length=120)
    pincode: str = Field(min_length=3, max_length=12)
    date_of_birth: date
    cell: str
    enrolled_on: date | None = Field(None, description="Original enrolment date, if known")
    declaration_place: str | None = None
    declaration_date: date | None = None

    @field_validator("membership_number")
    @classmethod
    def _num(cls, v: str) -> str:
        v = v.strip()
        if not v or any(c in v for c in "<>\"'\\"):
            raise ValueError("Invalid membership number")
        return v


class AdminMemberUpdateIn(MembershipFormIn, OfficeUseIn):
    declaration_place: str | None = None
    declaration_date: date | None = None


class MemberStatusIn(BaseModel):
    status: MembershipStatus
    reason: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _reason(self):
        if self.status == MembershipStatus.INACTIVE and not (self.reason and len(self.reason.strip()) >= 5):
            raise ValueError("A reason (min 5 characters) is required to deactivate a membership")
        return self


class LinkAccountIn(BaseModel):
    email: EmailStr


# --- Directory -----------------------------------------------------------------
class PublicMemberOut(BaseModel):
    """The ONLY fields public visitors and non-member accounts may receive."""

    id: int
    full_name: str
    father_name: str


class DirectoryMemberOut(BaseModel):
    """Member-authorised directory entry. Never includes Aadhaar, DOB, documents,
    signatures, introducer details or office data."""

    id: int
    membership_number: str
    full_name: str
    father_name: str
    photo_url: str | None
    city: str
    state: str
    country: str
    blood_group: str | None
    family_surname: str | None
    gothram: str | None
    natchathiram: str | None
    occupation: str | None
    native_place_address: str | None
    enrolled_at: datetime
    # Contact – only when the member consented
    cell: str | None = None
    phone: str | None = None
    email: str | None = None
    whatsapp_facebook: str | None = None
    # Address – only when the member consented
    address_line1: str | None = None
    address_line2: str | None = None
    pincode: str | None = None
    occupation_address: str | None = None


class MyMembershipOut(FormDataOut):
    member_id: int
    membership_number: str
    status: MembershipStatus
    source: MemberSource
    enrolled_at: datetime
    declaration_place: str | None
    declaration_date: date | None
    photo_url: str | None
    documents: list[DocumentOut]
    edit_permission_expires_at: datetime | None
    edit_permission_active: bool
    pending_edit_request: bool


class AdminMemberOut(FormDataOut, OfficeUseIn):
    member_id: int
    member_profile_id: int
    membership_number: str
    status: MembershipStatus
    source: MemberSource
    enrolled_at: datetime
    aadhaar_number: str | None
    declaration_place: str | None
    declaration_date: date | None
    application_id: int | None
    application_number: str | None
    linked_user_id: int | None
    linked_user_email: str | None
    approved_by_name: str | None
    deactivated_at: datetime | None
    deactivation_reason: str | None
    photo_url: str | None
    documents: list[DocumentOut]
    change_history: list[dict]
    edit_permission_expires_at: datetime | None


class AdminMemberListItem(BaseModel):
    id: int
    membership_number: str
    full_name: str
    father_name: str
    city: str
    cell: str
    status: MembershipStatus
    source: MemberSource
    enrolled_at: datetime
    has_account: bool
    photo_url: str | None


# --- Edit requests -----------------------------------------------------------
class EditRequestIn(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class EditReviewIn(BaseModel):
    note: str | None = Field(None, max_length=2000)


class EditRejectIn(BaseModel):
    note: str = Field(min_length=5, max_length=2000)


class EditRequestOut(BaseModel):
    id: int
    member_id: int
    membership_number: str
    member_name: str
    reason: str
    status: EditRequestStatus
    created_at: datetime
    reviewed_at: datetime | None
    reviewed_by_name: str | None
    review_note: str | None
    permission_starts_at: datetime | None
    permission_expires_at: datetime | None
    permission_active: bool


class MemberProfileUpdateIn(MembershipFormIn):
    """Fields a member may change during an approved 24-hour edit window."""

    # Introducer details belong to the original application and are not member-editable.
    introducer_name: None = Field(None, exclude=True)
    introducer_phone: None = Field(None, exclude=True)
    introducer_reg_no: None = Field(None, exclude=True)
