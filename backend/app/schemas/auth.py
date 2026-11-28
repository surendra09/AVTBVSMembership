from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import ApplicationStatus, MembershipStatus, Role
from app.schemas.common import ORMModel
from app.utils.validators import clean_text, is_valid_phone, normalize_phone, password_problems


def _check_password(v: str) -> str:
    problems = password_problems(v)
    if problems:
        raise ValueError("Password must contain " + ", ".join(problems))
    return v


def _check_phone(v: str) -> str:
    v = normalize_phone(v) or ""
    if not is_valid_phone(v):
        raise ValueError("Enter a valid mobile number (7–15 digits, optional +country code)")
    return v


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = Field(None, description="Optional. Needed only for e-mail notifications and password reset")
    phone: str = Field(description="Mobile number used for SMS/OTP")
    password: str

    _name = field_validator("full_name")(lambda v: clean_text(v))
    _pw = field_validator("password")(_check_password)
    _ph = field_validator("phone")(_check_phone)

    @field_validator("email", mode="before")
    @classmethod
    def _lower(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip().lower() if isinstance(v, str) else v


class LoginIn(BaseModel):
    identifier: str = Field(description="Registered email address or mobile number", min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class VerifyCodeIn(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendOtpIn(BaseModel):
    channel: str = Field(pattern="^(email|phone)$")


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str
    _pw = field_validator("new_password")(_check_password)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str
    _pw = field_validator("new_password")(_check_password)


class UpdateAccountIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    _name = field_validator("full_name")(lambda v: clean_text(v))


class MembershipSummary(BaseModel):
    is_member: bool
    member_id: int | None = None
    membership_number: str | None = None
    membership_status: MembershipStatus | None = None
    application_id: int | None = None
    application_status: ApplicationStatus | None = None
    edit_permission_expires_at: datetime | None = None


class UserOut(ORMModel):
    id: int
    full_name: str
    email: str | None
    phone: str
    role: Role
    is_active: bool
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None


class MeOut(BaseModel):
    user: UserOut
    membership: MembershipSummary


class LoginOut(MeOut):
    access_token: str = Field(description="Also set as an HttpOnly cookie; returned for API/Swagger clients")
    token_type: str = "bearer"


def user_out(user) -> UserOut:
    return UserOut(
        id=user.id, full_name=user.full_name, email=user.email, phone=user.phone, role=user.role,
        is_active=user.is_active, email_verified=user.email_verified_at is not None,
        phone_verified=user.phone_verified_at is not None, created_at=user.created_at,
        last_login_at=user.last_login_at,
    )
