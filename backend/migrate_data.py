"""Back up the local SQLite data and copy it into the production database.

    python migrate_data.py backup                 # snapshot avtbvs.db + uploads into ../backups/
    python migrate_data.py push --dry-run         # rehearse the copy, then roll back
    python migrate_data.py push                   # copy for real

`push` reads these environment variables (never put them in a file in the repo):
    TARGET_DATABASE_URL      production DB URL (TiDB). A Linux ssl_ca path is swapped
                             for certifi's bundle automatically when run on Windows.
    NEW_DATA_ENCRYPTION_KEY  production DATA_ENCRYPTION_KEY (from Render)
    NEW_DATA_HASH_KEY        production DATA_HASH_KEY (from Render)
    OLD_DATA_ENCRYPTION_KEY / OLD_DATA_HASH_KEY   optional; default = keys of the local backend/.env

What it does:
  * copies every table in foreign-key order, keeping ids;
  * re-encrypts Aadhaar numbers and recomputes Aadhaar hashes with the production keys;
  * skips login sessions and one-time codes (refresh_tokens, otp_codes);
  * replaces the target's membership_sequences row(s) with the local counters;
  * locks demo accounts (@avtbvs.test / @example.com): no password, role USER.
    Their member records stay visible; nobody can log in with the public demo passwords.

The target must already have the schema (Render runs `alembic upgrade head`) and no users.
Uploaded files are NOT copied: Render's free plan has no persistent disk or shell.
"""
import argparse
import hashlib
import hmac
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import column, create_engine, inspect, table, text

from app.core.config import settings
from app.models import Base  # noqa: F401  (registers every model on Base.metadata)

HERE = Path(__file__).resolve().parent
SKIP_TABLES = {"refresh_tokens", "otp_codes"}
AADHAAR_TABLES = {"member_profiles", "member_applications"}
DEMO_SUFFIXES = ("@avtbvs.test", "@example.com")


def backup(args) -> int:
    src = HERE / args.source
    if not src.exists():
        print(f"Source database not found: {src}")
        return 1
    dest = HERE.parent / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    dest.mkdir(parents=True)
    # sqlite3 backup API gives a consistent copy even if the app is running.
    with sqlite3.connect(src) as s, sqlite3.connect(dest / src.name) as d:
        s.backup(d)
    storage = HERE / "storage"
    if storage.exists():
        shutil.make_archive(str(dest / "storage"), "zip", storage)
    print(f"Backup written to {dest}")
    for p in sorted(dest.iterdir()):
        print(f"  {p.name}  {p.stat().st_size:,} bytes")
    return 0


def _target_url() -> str:
    url = os.environ.get("TARGET_DATABASE_URL", "").strip().replace("@ ", "@")
    if not url:
        sys.exit("Set TARGET_DATABASE_URL first (see the docstring).")
    linux_ca = "/etc/ssl/certs/ca-certificates.crt"
    if linux_ca in url and not Path(linux_ca).exists():
        import certifi
        url = url.replace(linux_ca, certifi.where().replace("\\", "/"))
    return url


def push(args) -> int:
    new_enc = os.environ.get("NEW_DATA_ENCRYPTION_KEY", "").strip()
    new_hash = os.environ.get("NEW_DATA_HASH_KEY", "").strip()
    if not new_enc or not new_hash:
        sys.exit("Set NEW_DATA_ENCRYPTION_KEY and NEW_DATA_HASH_KEY (the values in Render).")
    old_f = Fernet(os.environ.get("OLD_DATA_ENCRYPTION_KEY", settings.DATA_ENCRYPTION_KEY).encode())
    new_f = Fernet(new_enc.encode())

    def new_keyed_hash(v: str) -> str:
        return hmac.new(new_hash.encode(), v.encode(), hashlib.sha256).hexdigest()

    src = create_engine(f"sqlite:///{HERE / args.source}")
    url = _target_url()
    dst = create_engine(url, connect_args={} if url.startswith("sqlite") else {"connect_timeout": 20})
    src_tables = set(inspect(src).get_table_names())
    dst_insp = inspect(dst)
    dst_tables = set(dst_insp.get_table_names())
    if "alembic_version" not in dst_tables:
        sys.exit("Target has no schema yet. Let Render deploy once (it runs alembic upgrade head).")

    with dst.connect() as d:
        if d.execute(text("SELECT COUNT(*) FROM users")).scalar():
            sys.exit("Target already has users. This tool only fills an empty production database.")

    fk_off, fk_on = (("PRAGMA foreign_keys=OFF", "PRAGMA foreign_keys=ON") if dst.dialect.name == "sqlite"
                     else ("SET FOREIGN_KEY_CHECKS=0", "SET FOREIGN_KEY_CHECKS=1"))
    total = 0
    with src.connect() as s, dst.connect() as d:
        trans = d.begin()
        d.execute(text(fk_off))
        d.execute(text("DELETE FROM membership_sequences"))
        for t in Base.metadata.sorted_tables:
            name = t.name
            if name in SKIP_TABLES or name not in src_tables:
                continue
            if name not in dst_tables:
                print(f"  ! {name}: missing in target, skipped")
                continue
            dst_cols = {c["name"] for c in dst_insp.get_columns(name)}
            order = " ORDER BY id" if "id" in t.c else ""
            rows = [dict(r) for r in s.execute(text(f'SELECT * FROM "{name}"{order}')).mappings()]
            missing = set(rows[0]) - dst_cols if rows else set()
            if missing:
                print(f"  ! {name}: columns not in target, dropped: {sorted(missing)}")
            rows = [{k: v for k, v in r.items() if k in dst_cols} for r in rows]

            for r in rows:
                if name in AADHAAR_TABLES and r.get("aadhaar_number"):
                    try:
                        plain = old_f.decrypt(r["aadhaar_number"].encode()).decode()
                    except InvalidToken:
                        sys.exit(f"{name} id {r.get('id')}: Aadhaar cannot be decrypted with the old key.")
                    r["aadhaar_number"] = new_f.encrypt(plain.encode()).decode()
                    r["aadhaar_hash"] = new_keyed_hash(plain)
                if name == "users" and str(r.get("email", "")).lower().endswith(DEMO_SUFFIXES):
                    r["password_hash"] = None
                    r["role"] = "USER"

            if rows:
                d.execute(table(name, *[column(c) for c in rows[0]]).insert(), rows)
            print(f"  {name}: {len(rows)} rows")
            total += len(rows)
        d.execute(text(fk_on))
        if args.dry_run:
            trans.rollback()  # leave target untouched
            print(f"Dry run OK: {total} rows would be copied. Nothing was written.")
            return 0
        trans.commit()
    print(f"Done: {total} rows copied to production.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--source", default="avtbvs.db")
    b.set_defaults(func=backup)
    u = sub.add_parser("push")
    u.add_argument("--source", default="avtbvs.db")
    u.add_argument("--dry-run", action="store_true")
    u.set_defaults(func=push)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
