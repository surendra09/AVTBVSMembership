"""Custom SQLAlchemy column types."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Text
from sqlalchemy.types import TypeDecorator

from app.core.crypto import decrypt_value, encrypt_value


class UTCDateTime(TypeDecorator):
    """Stores naive UTC in MySQL DATETIME; always returns timezone-aware UTC."""

    impl = DateTime(timezone=False)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        # Truncate (MySQL DATETIME would otherwise *round* fractional seconds up).
        return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class EncryptedString(TypeDecorator):
    """Transparently encrypts a string at rest using Fernet (AES-128-CBC + HMAC)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect):
        if value is None or value == "":
            return None
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect):
        if value is None:
            return None
        return decrypt_value(value)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
