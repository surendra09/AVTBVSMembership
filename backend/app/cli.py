"""Operational commands.

    python -m app.cli create-super-admin --name "Full Name" --email admin@example.org --phone 9876543210
    python -m app.cli init-sequences
    python -m app.cli check-config

The first Super Admin is created from the server shell only – there are no
default credentials and no HTTP endpoint that can create the first Super Admin.
"""
import argparse
import getpass
import os
import sys

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.database.types import utcnow
from app.models import AuditLog, MembershipSequence, Role, User
from app.schemas.auth import _check_password, _check_phone
from app.services.numbering import sequence_name


def create_super_admin(args) -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(User).where(User.role == Role.SUPER_ADMIN))
        if existing and not args.allow_additional:
            print("A Super Admin already exists. Create further Super Admins from the Super Admin dashboard, "
                  "or pass --allow-additional if you have lost access.", file=sys.stderr)
            return 1
        try:
            from pydantic import TypeAdapter, EmailStr
            email = TypeAdapter(EmailStr).validate_python(args.email.strip()).lower()
            phone = _check_phone(args.phone)
        except ValueError as exc:  # includes pydantic.ValidationError
            print(f"Invalid input: {exc}", file=sys.stderr)
            return 1
        if db.scalar(select(User).where((User.email == email) | (User.phone == phone))):
            print("An account with this email or phone already exists.", file=sys.stderr)
            return 1
        password = os.environ.get("SUPER_ADMIN_PASSWORD") or getpass.getpass("Password: ")
        if not os.environ.get("SUPER_ADMIN_PASSWORD") and password != getpass.getpass("Confirm password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
        try:
            _check_password(password)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        now = utcnow()
        user = User(full_name=args.name.strip(), email=email, phone=phone, role=Role.SUPER_ADMIN,
                    password_hash=hash_password(password), email_verified_at=now, phone_verified_at=now,
                    password_changed_at=now)
        db.add(user)
        db.flush()
        db.add(AuditLog(actor_id=None, action="cli.create_super_admin", entity_type="user", entity_id=str(user.id),
                        details={"email": email}))
        db.commit()
        print(f"Super Admin created: {email} (id {user.id})")
        return 0


def init_sequences(_args) -> int:
    with SessionLocal() as db:
        name = sequence_name()
        if not db.scalar(select(MembershipSequence).where(MembershipSequence.name == name)):
            db.add(MembershipSequence(name=name, next_value=settings.MEMBERSHIP_SEQUENCE_START))
            db.commit()
            print(f"Created membership sequence '{name}' starting at {settings.MEMBERSHIP_SEQUENCE_START}")
        else:
            print(f"Membership sequence '{name}' already exists")
    return 0


def check_config(_args) -> int:
    problems = settings.validate_production()
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Membership number template: {settings.MEMBERSHIP_NUMBER_TEMPLATE!r} prefix={settings.MEMBERSHIP_NUMBER_PREFIX!r}")
    print(f"Email provider: {settings.EMAIL_PROVIDER}; SMS provider: {settings.SMS_PROVIDER}")
    for p in problems:
        print(f"  ! {p}")
    return 1 if problems and settings.is_production else 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-super-admin", help="Create the first Super Admin (interactive password prompt)")
    p.add_argument("--name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--phone", required=True)
    p.add_argument("--allow-additional", action="store_true")
    p.set_defaults(func=create_super_admin)
    sub.add_parser("init-sequences", help="Create the membership sequence row").set_defaults(func=init_sequences)
    sub.add_parser("check-config", help="Validate configuration").set_defaults(func=check_config)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
