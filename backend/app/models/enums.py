import enum


class Role(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class ApplicationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    RESUBMITTED = "RESUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


REVIEWABLE_STATUSES = (ApplicationStatus.PENDING, ApplicationStatus.RESUBMITTED)
APPLICANT_EDITABLE_STATUSES = (ApplicationStatus.DRAFT, ApplicationStatus.CORRECTION_REQUIRED)
OPEN_STATUSES = (
    ApplicationStatus.DRAFT,
    ApplicationStatus.PENDING,
    ApplicationStatus.CORRECTION_REQUIRED,
    ApplicationStatus.RESUBMITTED,
)


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MemberSource(str, enum.Enum):
    ONLINE_APPLICATION = "ONLINE_APPLICATION"
    MANUAL_ENTRY = "MANUAL_ENTRY"


class DocumentType(str, enum.Enum):
    PHOTO = "PHOTO"  # recent passport-size photograph (affixed on the form)
    ID_PROOF = "ID_PROOF"
    ADDITIONAL_PHOTO_1 = "ADDITIONAL_PHOTO_1"
    ADDITIONAL_PHOTO_2 = "ADDITIONAL_PHOTO_2"
    INTRODUCER_SIGNATURE = "INTRODUCER_SIGNATURE"
    APPLICANT_SIGNATURE = "APPLICANT_SIGNATURE"


class EditRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"


class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class OtpPurpose(str, enum.Enum):
    EMAIL_VERIFY = "EMAIL_VERIFY"
    PHONE_VERIFY = "PHONE_VERIFY"
    PASSWORD_RESET = "PASSWORD_RESET"


class ChangeSource(str, enum.Enum):
    MEMBER_EDIT = "MEMBER_EDIT"
    ADMIN_EDIT = "ADMIN_EDIT"


BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "A1+", "A1-", "A1B+", "A1B-", "A2+", "A2-",
                "A2B+", "A2B-", "Bombay (hh)", "Unknown")
