"""ORM entities for the AVTBVS Membership system."""
from datetime import date, datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.types import UTCDateTime, utcnow
from app.models.base import Base, MembershipFormFields, TimestampMixin, pk
from app.models.enums import (
    ApplicationStatus, ChangeSource, DeliveryStatus, DocumentType, EditRequestStatus, MemberSource,
    MembershipStatus, NotificationChannel, OtpPurpose, Role,
)


def _enum(e):
    return Enum(e, native_enum=False, length=32, validate_strings=True)


# 1. users --------------------------------------------------------------------
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = pk()
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)  # optional; login also works by mobile
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), default=Role.USER, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    phone_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    password_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    profile: Mapped["MemberProfile | None"] = relationship(back_populates="user", uselist=False,
                                                           foreign_keys="MemberProfile.user_id")

    @property
    def is_admin(self) -> bool:
        return self.role in (Role.ADMIN, Role.SUPER_ADMIN)


# 2. member_profiles -----------------------------------------------------------
class MemberProfile(MembershipFormFields, TimestampMixin, Base):
    """Canonical personal record of an official member (online or manually added)."""

    __tablename__ = "member_profiles"

    id: Mapped[int] = pk()
    # Nullable: manually added existing members need no login account.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    # Declaration as captured on the paper/online form
    declaration_place: Mapped[str | None] = mapped_column(String(120))
    declaration_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User | None] = relationship(back_populates="profile", foreign_keys=[user_id])
    member: Mapped["Member | None"] = relationship(back_populates="profile", uselist=False)
    documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="member_profile", foreign_keys="ApplicationDocument.member_profile_id")

    __table_args__ = (Index("ix_member_profiles_full_name", "full_name"),
                      Index("ix_member_profiles_father_name", "father_name"),
                      Index("ix_member_profiles_city", "city"))


# 3. member_applications ------------------------------------------------------
class MemberApplication(MembershipFormFields, TimestampMixin, Base):
    __tablename__ = "member_applications"

    id: Mapped[int] = pk()
    application_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[ApplicationStatus] = mapped_column(_enum(ApplicationStatus), default=ApplicationStatus.DRAFT,
                                                      nullable=False, index=True)
    # DECLARATION
    declaration_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    declaration_place: Mapped[str | None] = mapped_column(String(120))
    declaration_date: Mapped[date | None] = mapped_column(Date)
    # Review data
    correction_notes: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    submission_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="application", foreign_keys="ApplicationDocument.application_id")
    history: Mapped[list["ApplicationHistory"]] = relationship(back_populates="application",
                                                               order_by="ApplicationHistory.id")
    member: Mapped["Member | None"] = relationship(back_populates="application", uselist=False)


# 4. application_documents ----------------------------------------------------
class ApplicationDocument(TimestampMixin, Base):
    """Private uploaded file. Linked to an application and/or an official member profile."""

    __tablename__ = "application_documents"

    id: Mapped[int] = pk()
    application_id: Mapped[int | None] = mapped_column(ForeignKey("member_applications.id", ondelete="CASCADE"),
                                                       index=True)
    member_profile_id: Mapped[int | None] = mapped_column(ForeignKey("member_profiles.id", ondelete="CASCADE"),
                                                          index=True)
    doc_type: Mapped[DocumentType] = mapped_column(_enum(DocumentType), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    application: Mapped[MemberApplication | None] = relationship(back_populates="documents",
                                                                 foreign_keys=[application_id])
    member_profile: Mapped[MemberProfile | None] = relationship(back_populates="documents",
                                                                foreign_keys=[member_profile_id])


# 5. members ------------------------------------------------------------------
class Member(TimestampMixin, Base):
    """The official membership record – exists only after approval or manual entry."""

    __tablename__ = "members"

    id: Mapped[int] = pk()
    member_profile_id: Mapped[int] = mapped_column(ForeignKey("member_profiles.id", ondelete="RESTRICT"),
                                                   unique=True, nullable=False)  # one membership per profile
    membership_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(_enum(MembershipStatus), default=MembershipStatus.ACTIVE,
                                                     nullable=False, index=True)
    source: Mapped[MemberSource] = mapped_column(_enum(MemberSource), nullable=False)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("member_applications.id", ondelete="SET NULL"),
                                                       unique=True)
    enrolled_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False, index=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # OFFICE USE ONLY (from the paper form)
    verified_by: Mapped[str | None] = mapped_column(String(150))
    receipt_number: Mapped[str | None] = mapped_column(String(50))
    receipt_date: Mapped[date | None] = mapped_column(Date)
    committee_chairman: Mapped[str | None] = mapped_column(String(150))
    committee_secretary: Mapped[str | None] = mapped_column(String(150))
    committee_president: Mapped[str | None] = mapped_column(String(150))
    office_notes: Mapped[str | None] = mapped_column(Text)
    deactivated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    deactivation_reason: Mapped[str | None] = mapped_column(Text)

    profile: Mapped[MemberProfile] = relationship(back_populates="member")
    application: Mapped[MemberApplication | None] = relationship(back_populates="member")
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])


# 6. membership_sequences -----------------------------------------------------
class MembershipSequence(TimestampMixin, Base):
    __tablename__ = "membership_sequences"

    id: Mapped[int] = pk()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g. "default" or "2026"
    next_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


# 7. application_history ------------------------------------------------------
class ApplicationHistory(Base):
    __tablename__ = "application_history"

    id: Mapped[int] = pk()
    application_id: Mapped[int] = mapped_column(ForeignKey("member_applications.id", ondelete="CASCADE"),
                                                nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    application: Mapped[MemberApplication] = relationship(back_populates="history")
    actor: Mapped[User | None] = relationship()


# 8. notifications ------------------------------------------------------------
class Notification(Base):
    """Website (in-app) notification."""

    __tablename__ = "notifications"

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(255))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read", "created_at"),)


# 9. notification_deliveries --------------------------------------------------
class NotificationDelivery(Base):
    """Outbox row for email / SMS – processed by the background worker with retries."""

    __tablename__ = "notification_deliveries"

    id: Mapped[int] = pk()
    notification_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(_enum(NotificationChannel), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255))
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DeliveryStatus] = mapped_column(_enum(DeliveryStatus), default=DeliveryStatus.PENDING,
                                                   nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    next_attempt_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # OTP / reset links

    __table_args__ = (Index("ix_deliveries_queue", "status", "next_attempt_at"),)


# 10. edit_requests -----------------------------------------------------------
class EditRequest(TimestampMixin, Base):
    __tablename__ = "edit_requests"

    id: Mapped[int] = pk()
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EditRequestStatus] = mapped_column(_enum(EditRequestStatus), default=EditRequestStatus.PENDING,
                                                      nullable=False, index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    review_note: Mapped[str | None] = mapped_column(Text)

    member: Mapped[Member] = relationship()
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    permission: Mapped["EditPermission | None"] = relationship(back_populates="edit_request", uselist=False)


# 11. edit_permissions --------------------------------------------------------
class EditPermission(Base):
    __tablename__ = "edit_permissions"

    id: Mapped[int] = pk()
    edit_request_id: Mapped[int] = mapped_column(ForeignKey("edit_requests.id", ondelete="CASCADE"),
                                                 unique=True, nullable=False)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    granted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    expiry_notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    edit_request: Mapped[EditRequest] = relationship(back_populates="permission")

    __table_args__ = (Index("ix_edit_permissions_member_window", "member_id", "expires_at"),)


# 12. member_change_history ---------------------------------------------------
class MemberChangeHistory(Base):
    __tablename__ = "member_change_history"

    id: Mapped[int] = pk()
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    member_profile_id: Mapped[int] = mapped_column(ForeignKey("member_profiles.id", ondelete="CASCADE"),
                                                   nullable=False)
    edit_permission_id: Mapped[int | None] = mapped_column(ForeignKey("edit_permissions.id", ondelete="SET NULL"))
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[ChangeSource] = mapped_column(_enum(ChangeSource), nullable=False)
    field_name: Mapped[str] = mapped_column(String(60), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)  # sensitive fields stored masked
    new_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    changed_by: Mapped[User | None] = relationship()


# 13. audit_logs --------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = pk()
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(50))
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False, index=True)

    actor: Mapped[User | None] = relationship()

    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)


# Supporting tables -----------------------------------------------------------
class OtpCode(Base):
    """Hashed one-time codes / tokens for email+phone verification and password reset."""

    __tablename__ = "otp_codes"

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(_enum(OtpPurpose), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_otp_user_purpose", "user_id", "purpose"),)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = pk()
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))


__all__ = [
    "User", "MemberProfile", "MemberApplication", "ApplicationDocument", "Member", "MembershipSequence",
    "ApplicationHistory", "Notification", "NotificationDelivery", "EditRequest", "EditPermission",
    "MemberChangeHistory", "AuditLog", "OtpCode", "RefreshToken", "UniqueConstraint", "Text",
]
