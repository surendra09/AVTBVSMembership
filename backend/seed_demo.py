"""Seed the local SQLite demo database with 10 members and login accounts.

Run from the backend/ directory with the venv active:

    python seed_demo.py

Every person gets a login account AND an official (approved) membership record
so they all appear in the public directory. Login identifier = email.
Password = "<handle>1234" (e.g. arjun -> arjun1234).
"""
from datetime import date

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database.session import SessionLocal, engine
from app.database.types import utcnow
from app.models.base import Base
# Import the entities module so every table is registered on Base.metadata.
from app.models import entities as _entities  # noqa: F401
from app.models import (
    Member, MemberProfile, MembershipSequence, MemberSource, MembershipStatus, Role, User,
)

# handle, full name, father's name, city, state, role
PEOPLE = [
    ("arjun",   "Arjun Varma",        "Ramesh Varma",       "Chennai",     "Tamil Nadu",     Role.SUPER_ADMIN),
    ("priya",   "Priya Lakshmi",      "Venkatesh Reddy",    "Hyderabad",   "Telangana",      Role.ADMIN),
    ("karthik", "Karthik Srinivasan", "Srinivasan Iyer",    "Coimbatore",  "Tamil Nadu",     Role.ADMIN),
    ("deepak",  "Deepak Chetty",      "Mohan Chetty",       "Bengaluru",   "Karnataka",      Role.USER),
    ("sneha",   "Sneha Rao",          "Anand Rao",          "Chennai",     "Tamil Nadu",     Role.USER),
    ("vijay",   "Vijay Kumar",        "Suresh Kumar",       "Vijayawada",  "Andhra Pradesh", Role.USER),
    ("anitha",  "Anitha Devi",        "Prakash Babu",       "Madurai",     "Tamil Nadu",     Role.USER),
    ("ravi",    "Ravi Teja",          "Narayana Murthy",    "Guntur",      "Andhra Pradesh", Role.USER),
    ("lavanya", "Lavanya Sundar",     "Sundaram Pillai",    "Salem",       "Tamil Nadu",     Role.USER),
    ("manoj",   "Manoj Krishnan",     "Krishnan Nair",      "Tiruchirapalli", "Tamil Nadu",  Role.USER),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    now = utcnow()
    with SessionLocal() as db:
        # Membership sequence (used by the real numbering service elsewhere).
        if not db.scalar(select(MembershipSequence).where(MembershipSequence.name == "default")):
            db.add(MembershipSequence(name="default", next_value=1))

        existing = db.scalar(select(func.count()).select_from(User))
        if existing:
            print(f"Database already has {existing} user(s); skipping seed to avoid duplicates.")
            return

        for i, (handle, full_name, father, city, state, role) in enumerate(PEOPLE, start=1):
            email = f"{handle}@avtbvs.test"
            phone = f"90000000{i:02d}"            # unique 10-digit mobile
            password = f"{handle}1234"

            user = User(
                full_name=full_name, email=email, phone=phone,
                password_hash=hash_password(password), role=role, is_active=True,
                email_verified_at=now, phone_verified_at=now, password_changed_at=now,
            )
            db.add(user)
            db.flush()  # assign user.id

            profile = MemberProfile(
                user_id=user.id,
                full_name=full_name, father_name=father,
                address_line1=f"{i} Temple Street", city=city, state=state,
                country="India", pincode=f"6000{i:02d}",
                cell=phone, email=email,
                date_of_birth=date(1985, (i % 12) + 1, (i % 27) + 1),
                show_contact_in_directory=True, show_address_in_directory=True,
            )
            db.add(profile)
            db.flush()  # assign profile.id

            member = Member(
                member_profile_id=profile.id,
                membership_number=f"AVT{i:04d}",
                status=MembershipStatus.ACTIVE,
                source=MemberSource.MANUAL_ENTRY,
                enrolled_at=now,
            )
            db.add(member)

        db.commit()

    print("Seeded 10 members. Login with email (e.g. arjun@avtbvs.test) and password '<handle>1234'.")


if __name__ == "__main__":
    main()
