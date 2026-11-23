"""Reusable validation helpers (used by Pydantic schemas and services)."""
import re
from datetime import date

from app.models.enums import BLOOD_GROUPS

# Verhoeff tables (Aadhaar check digit)
_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
INDIAN_MOBILE_RE = re.compile(r"^(\+91)?[6-9][0-9]{9}$")
PINCODE_IN_RE = re.compile(r"^[1-9][0-9]{5}$")
POSTCODE_RE = re.compile(r"^[A-Za-z0-9 \-]{3,10}$")
NAME_RE = re.compile(r"^[^\d<>{}\[\]\\;]{2,150}$")
PASSWORD_MIN = 10


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    v = re.sub(r"[\s\-()]", "", value.strip())
    return v or None


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_RE.match(value))


def normalize_aadhaar(value: str | None) -> str | None:
    if value is None:
        return None
    v = re.sub(r"[\s\-]", "", value.strip())
    return v or None


def is_valid_aadhaar(value: str) -> bool:
    if not re.fullmatch(r"[2-9][0-9]{11}", value):
        return False
    c = 0
    for i, ch in enumerate(reversed(value)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def is_valid_pincode(value: str, country: str | None) -> bool:
    if (country or "India").strip().lower() == "india":
        return bool(PINCODE_IN_RE.match(value))
    return bool(POSTCODE_RE.match(value))


def is_valid_blood_group(value: str) -> bool:
    return value in BLOOD_GROUPS


def age_on(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < PASSWORD_MIN:
        problems.append(f"at least {PASSWORD_MIN} characters")
    if not re.search(r"[A-Za-z]", password):
        problems.append("a letter")
    if not re.search(r"[0-9]", password):
        problems.append("a number")
    if len(password) > 128:
        problems.append("at most 128 characters")
    return problems


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    v = re.sub(r"\s+", " ", value).strip()
    return v or None


def clean_multiline(value: str | None) -> str | None:
    if value is None:
        return None
    v = "\n".join(line.strip() for line in value.strip().splitlines())
    return v or None
