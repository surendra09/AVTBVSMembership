"""Field-level encryption and keyed hashing for sensitive personal data."""
import hashlib
import hmac
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(settings.DATA_ENCRYPTION_KEY.encode())


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:  # wrong key or tampered data – never leak the ciphertext
        return "[undecryptable]"


def keyed_hash(value: str) -> str:
    """Deterministic HMAC-SHA256 used to detect duplicates without storing plaintext."""
    return hmac.new(settings.DATA_HASH_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_aadhaar(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(c for c in value if c.isdigit())
    return f"XXXX XXXX {digits[-4:]}" if len(digits) >= 4 else "XXXX"


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, domain = value.split("@", 1)
    return f"{local[:2]}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    return f"{'*' * max(len(value) - 4, 0)}{value[-4:]}"
