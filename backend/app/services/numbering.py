"""Membership and application number generation.

Membership numbers are generated only when an application is APPROVED, inside
the approval transaction. The sequence row is locked with SELECT ... FOR UPDATE
so concurrent approvals serialise; the UNIQUE constraint on
members.membership_number is the final guard. Numbers already used by
manually-entered existing members are skipped automatically.

The organisation's real format must be configured with MEMBERSHIP_NUMBER_TEMPLATE
(see README – "Membership number format").
"""
from datetime import datetime

from sqlalchemy import exists, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.types import utcnow
from app.models import Member, MemberApplication, MembershipSequence


class _Fmt(dict):
    def __missing__(self, key):
        raise KeyError(f"Unknown placeholder {{{key}}} in MEMBERSHIP_NUMBER_TEMPLATE")


def format_membership_number(seq: int, when: datetime | None = None) -> str:
    when = when or utcnow()
    return settings.MEMBERSHIP_NUMBER_TEMPLATE.format_map(
        _Fmt(seq=seq, year=when.year, yy=f"{when.year % 100:02d}", prefix=settings.MEMBERSHIP_NUMBER_PREFIX)
    )


def sequence_name(when: datetime | None = None) -> str:
    when = when or utcnow()
    return str(when.year) if settings.MEMBERSHIP_SEQUENCE_PER_YEAR else "default"


def _locked_sequence(db: Session, name: str, start: int | None = None) -> MembershipSequence:
    stmt = select(MembershipSequence).where(MembershipSequence.name == name).with_for_update()
    # Non-locking existence check first: a locking read of a missing row would take a gap lock.
    exists_row = db.scalar(select(MembershipSequence.id).where(MembershipSequence.name == name))
    seq = db.scalar(stmt) if exists_row else None
    if seq is None:
        # Create the row in its own short transaction so concurrent first-use cannot
        # deadlock on gap locks; a duplicate insert by a competitor is harmless.
        try:
            with db.get_bind().connect() as conn:
                conn.execute(insert(MembershipSequence).values(
                    name=name, next_value=start if start is not None else settings.MEMBERSHIP_SEQUENCE_START,
                    created_at=utcnow().replace(tzinfo=None, microsecond=0),
                    updated_at=utcnow().replace(tzinfo=None, microsecond=0)))
                conn.commit()
        except IntegrityError:
            pass
        seq = db.scalar(stmt)  # locking read sees the latest committed row
    return seq


def next_membership_number(db: Session) -> str:
    """Must be called inside the approval transaction."""
    now = utcnow()
    seq = _locked_sequence(db, sequence_name(now))
    for _ in range(100_000):
        candidate = format_membership_number(seq.next_value, now)
        seq.next_value += 1
        if not db.scalar(select(exists().where(Member.membership_number == candidate))):
            db.flush()
            return candidate
    raise RuntimeError("Could not allocate a membership number")


def preview_numbers(db: Session, count: int = 3) -> dict:
    name = sequence_name()
    seq = db.scalar(select(MembershipSequence).where(MembershipSequence.name == name))
    start = seq.next_value if seq else settings.MEMBERSHIP_SEQUENCE_START
    return {"sequence": name, "next_value": start, "template": settings.MEMBERSHIP_NUMBER_TEMPLATE,
            "prefix": settings.MEMBERSHIP_NUMBER_PREFIX, "per_year": settings.MEMBERSHIP_SEQUENCE_PER_YEAR,
            "examples": [format_membership_number(start + i) for i in range(count)]}


def set_next_value(db: Session, value: int) -> MembershipSequence:
    seq = _locked_sequence(db, sequence_name())
    seq.next_value = value
    return seq


def next_application_number(db: Session) -> str:
    """Internal tracking number for applications (not a membership number)."""
    year = utcnow().year
    prefix = f"{settings.APPLICATION_NUMBER_PREFIX}-{year}-"
    seq = _locked_sequence(db, f"application-{year}", start=1)
    while True:
        candidate = f"{prefix}{seq.next_value:06d}"
        seq.next_value += 1
        if not db.scalar(select(func.count()).where(MemberApplication.application_number == candidate)):
            return candidate
