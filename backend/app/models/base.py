from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.database.types import EncryptedString, UTCDateTime, utcnow


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False)


def pk() -> Mapped[int]:
    # BigInteger on MySQL; INTEGER on SQLite so the demo DB autoincrements the PK.
    return mapped_column(BigInteger().with_variant(Integer, "sqlite"),
                         primary_key=True, autoincrement=True)


class MembershipFormFields:
    """Every field from the official LIFE MEMBERSHIP APPLICATION FORM.

    Shared by member_applications (what the applicant submitted) and
    member_profiles (the official member's current record).
    """

    # PERSONAL DETAILS
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    father_name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(120), nullable=False)  # City/Town/Village
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False, default="India")
    pincode: Mapped[str] = mapped_column(String(12), nullable=False)
    aadhaar_number: Mapped[str | None] = mapped_column(EncryptedString())  # encrypted at rest
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))

    @declared_attr
    def aadhaar_hash(cls) -> Mapped[str | None]:
        return mapped_column(String(64), index=True)

    blood_group: Mapped[str | None] = mapped_column(String(16))
    date_of_birth: Mapped[date | None] = mapped_column(Date)  # required on submission

    # CONTACT DETAILS
    phone: Mapped[str | None] = mapped_column(String(20))  # landline "Phone"
    centre_x_no: Mapped[str | None] = mapped_column(String(30))  # "Centre X No." (exchange/extension)
    cell: Mapped[str] = mapped_column(String(20), nullable=False)  # mobile
    email: Mapped[str | None] = mapped_column(String(255))
    whatsapp_facebook: Mapped[str | None] = mapped_column(String(255))

    # FAMILY DETAILS
    family_surname: Mapped[str | None] = mapped_column(String(120))
    gothram: Mapped[str | None] = mapped_column(String(120))
    natchathiram: Mapped[str | None] = mapped_column(String(120))

    # PROFESSIONAL DETAILS
    occupation: Mapped[str | None] = mapped_column(String(150))
    occupation_address: Mapped[str | None] = mapped_column(Text)

    # NATIVE PLACE
    native_place_address: Mapped[str | None] = mapped_column(Text)

    # INTRODUCER DETAILS (all three mandatory for online applications)
    introducer_name: Mapped[str | None] = mapped_column(String(150))  # "Introduced by Sri"
    introducer_phone: Mapped[str | None] = mapped_column(String(20))
    introducer_reg_no: Mapped[str | None] = mapped_column(String(50))

    # Directory privacy preferences (member consent)
    show_contact_in_directory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_address_in_directory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


FORM_FIELD_NAMES = [
    "full_name", "father_name", "address_line1", "address_line2", "city", "state", "country", "pincode",
    "aadhaar_number", "blood_group", "date_of_birth", "phone", "centre_x_no", "cell", "email",
    "whatsapp_facebook", "family_surname", "gothram", "natchathiram", "occupation", "occupation_address",
    "native_place_address", "introducer_name", "introducer_phone", "introducer_reg_no",
    "show_contact_in_directory", "show_address_in_directory",
]

__all__ = ["Base", "TimestampMixin", "MembershipFormFields", "FORM_FIELD_NAMES", "pk", "Text", "Date"]
