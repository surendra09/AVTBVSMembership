"""Password hashing, JWT handling and auth cookies."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Response

from app.core.config import settings

_hasher = PasswordHasher()  # Argon2id with library-recommended parameters

ACCESS_COOKIE = "avtbvs_access"
REFRESH_COOKIE = "avtbvs_refresh"
CSRF_COOKIE = "avtbvs_csrf"
CSRF_HEADER = "X-CSRF-Token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        # Spend comparable time to avoid user-enumeration by timing.
        _hasher.hash("timing-equaliser")
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "iat": now, "exp": expires, "jti": jti}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM), jti, expires


def decode_token(token: str, expected_type: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_url_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, access: str, refresh: str) -> str:
    common = dict(secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE, domain=settings.COOKIE_DOMAIN)
    response.set_cookie(ACCESS_COOKIE, access, httponly=True, path="/",
                        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh, httponly=True, path=f"{settings.API_PREFIX}/auth",
                        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, **common)
    csrf = secrets.token_urlsafe(24)
    # Readable by JS on purpose (double-submit CSRF token); carries no authority alone.
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, path="/",
                        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, **common)
    return csrf


def clear_auth_cookies(response: Response) -> None:
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, f"{settings.API_PREFIX}/auth"), (CSRF_COOKIE, "/")):
        response.delete_cookie(name, path=path, domain=settings.COOKIE_DOMAIN)
