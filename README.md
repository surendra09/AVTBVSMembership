# AVTBVS Membership

Membership management web application for **Ayira Vaisyar Telugu Beri Vysya Sabha** (Regd. No. 101/1955), formerly Telugu Beri Vysya Kulabhimana Sabha. It digitises the paper *Life Membership Application Form*: online applications, verification by the Membership Enrollment Committee, automatic membership numbers, entry of existing paper members, public and member-only directories, a 24-hour supervised profile-editing workflow, and notifications by website, email and SMS.

> **Before go-live:** read [`docs/OPEN-ITEMS.md`](docs/OPEN-ITEMS.md). The membership-number format and a high-resolution logo still have to come from the Sabha.

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router, Tailwind CSS, Axios, React Hook Form, Zod, Lucide icons |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, PyJWT, Argon2 |
| Database | MySQL 8.0+ |
| API docs | Swagger UI at `/docs`, ReDoc at `/redoc` |
| Deployment | Docker Compose (MySQL, API, notification worker, Nginx) |

---

## Contents

1. [Project layout](#project-layout)
2. [Prerequisites](#prerequisites)
3. [Running locally](#running-locally)
4. [Environment variables](#environment-variables)
5. [Database and migrations](#database-and-migrations)
6. [Creating the first Super Admin](#creating-the-first-super-admin)
7. [Swagger documentation](#swagger-documentation)
8. [Roles and workflows](#roles-and-workflows)
9. [Security](#security)
10. [Notifications](#notifications)
11. [Testing](#testing)
12. [Production deployment](#production-deployment)
13. [Backups and recovery](#backups-and-recovery)
14. [Troubleshooting](#troubleshooting)

---

## Project layout

```
avtbvs-membership/
├── backend/
│   ├── app/
│   │   ├── api/routes/        auth, applications, members, admin, super_admin, notifications, public
│   │   ├── core/              config, security (JWT/cookies/Argon2), crypto, RBAC deps, rate limiting
│   │   ├── models/            SQLAlchemy entities (13 required tables + otp_codes, refresh_tokens)
│   │   ├── schemas/           Pydantic request/response models (public vs member vs admin views)
│   │   ├── services/          business logic: membership, numbering, notifications, storage, audit
│   │   ├── middleware/        CSRF double-submit check, security headers, privacy-aware access log
│   │   ├── templates/email/   branded HTML email layout
│   │   ├── workers/           email/SMS delivery + edit-permission expiry worker
│   │   ├── cli.py             create-super-admin, init-sequences, check-config
│   │   └── main.py
│   ├── alembic/               migrations (0001_initial_schema)
│   ├── tests/                 pytest suite (runs against MySQL)
│   └── requirements.txt
├── frontend/
│   ├── public/brand/          tree emblem extracted from the official PDF
│   └── src/
│       ├── components/        Button, Form fields, Modal/ConfirmDialog, Table, Pagination, FileUpload…
│       ├── features/          auth, registration (official form), members, admin, notifications
│       ├── layouts/           public layout, dashboard layout with sidebar, footer
│       ├── pages/             public, user, admin, super-admin, shared
│       ├── routes/            route table with role guards
│       └── services/api.ts    Axios client (cookies, CSRF header, silent token refresh)
├── deployment/
│   ├── docker/                backend.Dockerfile, frontend.Dockerfile
│   ├── nginx/                 container config + host HTTPS example
│   └── scripts/               backup.sh, restore.sh
├── docs/                      ER diagram, open items, reference scans of the PDFs
├── docker-compose.yml
└── .env.example
```

## Prerequisites

* **Docker** 24+ with the Compose plugin (production and the quickest local start), or for development without Docker:
* **Python** 3.12 or newer
* **Node.js** 20 or newer, with npm
* **MySQL** 8.0 or newer

## Running locally

### 1. MySQL

```sql
CREATE DATABASE avtbvs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE avtbvs_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;   -- for tests
CREATE USER 'avtbvs'@'localhost' IDENTIFIED BY 'devpassword';
GRANT ALL ON avtbvs.* TO 'avtbvs'@'localhost';
GRANT ALL ON avtbvs_test.* TO 'avtbvs'@'localhost';
```

Or run only the database in Docker: `docker run -d --name avtbvs-mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=avtbvs -e MYSQL_USER=avtbvs -e MYSQL_PASSWORD=devpassword mysql:8.0`

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                    # development defaults: console email/SMS
alembic upgrade head
python -m app.cli init-sequences
python -m app.cli create-super-admin --name "Your Name" --email you@example.org --phone 9876543210
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 – /api is proxied to http://127.0.0.1:8000
```

In development, emails and SMS (including OTP codes) are **not sent**. They are written to `backend/storage/outbox.log`, one JSON line per message, so you can read verification codes from there.

## Environment variables

Every setting is read from the environment (or `.env`) by `backend/app/core/config.py`. [`.env.example`](.env.example) lists them all with comments. The ones that matter most:

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `production` makes the API refuse to start with development secrets or `COOKIE_SECURE=false` |
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/avtbvs?charset=utf8mb4` |
| `SECRET_KEY` | JWT signing key (≥ 48 random characters) |
| `DATA_ENCRYPTION_KEY` | Fernet key that encrypts Aadhaar numbers at rest. **Back it up: data can't be decrypted without it.** |
| `DATA_HASH_KEY` | HMAC key used to detect duplicate Aadhaar numbers without decrypting |
| `PUBLIC_APP_URL`, `CORS_ORIGINS` | Public URL of the site (used in email links) and allowed origins |
| `COOKIE_SECURE` | `true` in production (cookies only over HTTPS) |
| `MEMBERSHIP_NUMBER_TEMPLATE`, `_PREFIX`, `_SEQUENCE_START`, `_SEQUENCE_PER_YEAR` | Membership-number format, see [`docs/OPEN-ITEMS.md`](docs/OPEN-ITEMS.md) |
| `EMAIL_PROVIDER`, `SMTP_*`, `EMAIL_FROM` | `console` for development or `smtp` |
| `SMS_PROVIDER`, `MSG91_*`, `TWILIO_*` | `console`, `msg91` or `twilio` |
| `PRIVATE_STORAGE_DIR` | Where photographs and ID documents are kept (never web-served) |
| `ORG_*` | Organisation name, address, phone and email shown on the site and in emails |

### Generating secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"                                   # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"      # DATA_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"                                   # DATA_HASH_KEY
```

`python -m app.cli check-config` reports configuration problems.

## Database and migrations

* Models: `backend/app/models/entities.py`. ER diagram and integrity rules: [`docs/ER-diagram.md`](docs/ER-diagram.md).
* Apply migrations: `alembic upgrade head`. The Docker image does this automatically on start.
* After changing a model: `alembic revision --autogenerate -m "describe change"`, review the file, then `alembic upgrade head`. `alembic check` confirms models and migrations agree.
* Initialisation procedure for a new server: create the database → `alembic upgrade head` → `python -m app.cli init-sequences` → create the first Super Admin → set the next membership sequence value in **Super Admin → System settings** after paper members are entered.

## Creating the first Super Admin

There are **no default accounts** and no web endpoint that can create the first Super Admin. Create it from a shell on the server:

```bash
# Docker
docker compose exec api python -m app.cli create-super-admin --name "K. Srinivasan" --email president@example.org --phone 9876543210
# without Docker
python -m app.cli create-super-admin --name "..." --email ... --phone ...
```

The password is prompted for interactively and never echoed. The command refuses to run once a Super Admin exists, unless `--allow-additional` is given for account recovery. The action is written to the audit log. Further admins are created from **Super Admin → Admin management**, either with an emailed set-password link (recommended) or a temporary password.

## Swagger documentation

* Swagger UI: `http://localhost:8000/docs` (in production: `https://your-domain/docs`)
* ReDoc: `/redoc`; raw schema: `/openapi.json`

To try protected endpoints in Swagger, click **Authorize** and log in with the OAuth2 password form (`/api/auth/token`). Requests then use a Bearer token. Browser clients use HttpOnly cookies instead. To hide the docs in production, remove the `/docs|/redoc|/openapi.json` block from `deployment/nginx/nginx.conf`.

## Roles and workflows

**A login account is not a membership.** Accounts (`users`), applications (`member_applications`) and official members (`member_profiles` + `members`) are separate tables.

| Who | Can |
|---|---|
| Visitor | Browse the public directory: member name and father's name only |
| Registered user (not a member) | Same public directory; fill in, upload documents for, submit and correct their own application; receive notifications |
| Member | Full directory (photos, consented contact/address, family details); own record and membership number; request profile edits; print own record |
| Admin | Review applications (approve / request corrections / reject); add existing paper members with their numbers; edit, deactivate and link member records; handle edit requests; notification delivery records; reports and CSV export |
| Super Admin | Everything an Admin can do, plus create admins, convert users to admins, edit/activate/deactivate admins, audit log, system settings. The last active Super Admin can't be demoted or deactivated |

**Application lifecycle:** `DRAFT → PENDING → (CORRECTION_REQUIRED → RESUBMITTED)* → APPROVED | REJECTED`. Applicants can edit only in `DRAFT` and `CORRECTION_REQUIRED`. Every transition is recorded in `application_history`.

**Approval** is one database transaction. It locks the application, the applicant and the number-sequence row, creates the member profile and member, copies the documents, assigns the next free membership number (skipping numbers held by paper members), writes history and audit records, and queues notifications.

**Profile editing:** member requests → admin approves → `edit_permissions` row with `expires_at = now + 24h`. Every `PUT /api/members/profile` checks the window against server time (UTC), so frontend timers can't extend it. Each changed field is written to `member_change_history` and admins are notified. When the window expires, the member is notified and must request again.

## Security

* Argon2id password hashing; JWT access tokens (15 min) and rotating refresh tokens (7 days) in **HttpOnly, Secure, SameSite=Lax cookies**. Reusing an old refresh token revokes all of that user's sessions. Nothing is stored in `localStorage`.
* Double-submit CSRF token on every state-changing cookie-authenticated request.
* Role checks on the **server** for every endpoint (`require_admin`, `require_super_admin`, `require_member_or_admin`). The public directory query selects only the name and father's name columns.
* Aadhaar is encrypted at rest (Fernet), masked everywhere except the admin verification view, and every admin view of a record containing it is audit-logged.
* Uploads: extension allow-list per document type, size limits, magic-byte check, images fully re-encoded with Pillow (strips EXIF/GPS and appended payloads), PDFs with scripts rejected. Files sit in private storage with random names, mode 0600, and are served only through `/api/files/{id}` after an ownership/role check. Unauthorised requests get 404.
* Rate limits on login, registration, OTP and password reset (application level and in Nginx). OTPs are hashed, expire after 10 minutes and lock after 5 attempts. Password reset responses don't reveal whether an account exists.
* Security headers (CSP, X-Frame-Options, nosniff, Referrer-Policy, HSTS at the HTTPS proxy). The access log records method, path and status only. OTP and reset-link message bodies are hidden even from admins.

## Notifications

Creating a notification only inserts rows (`notifications` for the website, `notification_deliveries` for email/SMS) in the same transaction as the business change, so a provider outage never blocks saving. The worker (`python -m app.workers.notifications`, the `worker` service in Compose) delivers queued messages with exponential back-off (1, 2, 4, 8… minutes, up to `NOTIFICATION_MAX_ATTEMPTS`), records provider IDs and errors, recovers rows stuck mid-send, and sends edit-window expiry notices. Several workers can run at once (`SELECT … FOR UPDATE SKIP LOCKED`). Admins can see delivery status and retry failed messages in **Notifications → Email and SMS records**.

Templates for every event (registration, OTP, submission, correction request, resubmission, approval, number assignment, rejection, edit request/approval/rejection/expiry, admin alerts) are in `backend/app/services/notification_templates.py`. The branded HTML email layout is in `backend/app/templates/email/base.html`.

**Email:** set `EMAIL_PROVIDER=smtp` and the `SMTP_*` values (works with Google Workspace, Amazon SES SMTP, Zoho, etc.).
**SMS:** `SMS_PROVIDER=msg91` (India; register a DLT sender ID and flow template whose single variable is `message`) or `twilio`.

## Testing

```bash
# backend – needs MySQL; uses TEST_DATABASE_URL (default: avtbvs_test on localhost)
cd backend && pytest -q
# frontend
cd frontend && npm test && npm run typecheck && npm run build
```

The backend suite (94 tests) covers registration, login, invalid credentials, email/phone OTP, password reset, refresh rotation, CSRF and rate limiting. It also covers authorisation (public vs non-member vs member vs admin vs super admin), every mandatory-field rule including each introducer field, declaration, photographs and invalid files, approval, corrections, rejection, number generation (including 8 concurrent approvals), duplicate-number prevention, manual members and account linking. Further tests cover the 24-hour editing window (grant, edit, expiry, revocation), notification creation, delivery, retry and failure, and super-admin safeguards.

## Production deployment

1. Provision a Linux server with Docker and point your domain at it.
2. `git clone` the project to `/opt/avtbvs`, then `cp .env.example .env` and fill in real values (secrets, SMTP, SMS, `PUBLIC_APP_URL`, membership-number format). `chmod 600 .env`.
3. `docker compose up -d --build`. This starts MySQL, the API (migrations run automatically), the notification worker and Nginx on `127.0.0.1:8080`.
4. HTTPS: install Nginx and Certbot on the host and use [`deployment/nginx/https-host.conf.example`](deployment/nginx/https-host.conf.example) (`sudo certbot --nginx -d your-domain`). Keep `COOKIE_SECURE=true`.
5. Create the first Super Admin (see above), sign in, check **System settings**, enter existing paper members, then set the next membership sequence value.
6. Schedule backups (below) and test a restore.

Useful commands: `docker compose logs -f api worker`, `docker compose exec api python -m app.cli check-config`, update with `git pull && docker compose up -d --build`.

## Backups and recovery

```bash
deployment/scripts/backup.sh /var/backups/avtbvs      # MySQL dump + private documents, 30-day retention
# cron:  0 2 * * * /opt/avtbvs/deployment/scripts/backup.sh /var/backups/avtbvs
deployment/scripts/restore.sh /var/backups/avtbvs/db-YYYYMMDD-HHMMSS.sql.gz /var/backups/avtbvs/files-YYYYMMDD-HHMMSS.tar.gz
```

Copy backups off the server, encrypted. Keep a separate, safe copy of `.env`: without `DATA_ENCRYPTION_KEY`, Aadhaar numbers in a backup can't be read.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "CSRF validation failed" | Reload the page. API clients should use a Bearer token, not cookies. |
| Logged out on every request in production | The site must be served over HTTPS when `COOKIE_SECURE=true`, and the frontend and `/api` must be on the same domain. |
| API refuses to start: "Refusing to start in production" | Replace the development secrets listed in the error (see *Generating secrets*). |
| No OTP email/SMS | In development, read `backend/storage/outbox.log`. In production, check **Notifications → Email and SMS records** for the error, and `docker compose logs worker`. |
| `Access denied for user` / can't connect to MySQL | Check `DATABASE_URL` and the user grants; in Docker, wait for the `db` healthcheck. |
| `(1213) Deadlock` / lock wait during approvals | Run `python -m app.cli init-sequences` once so the sequence row exists. |
| Upload rejected | Photos and signatures: JPG/PNG up to 2 MB and at least 80 px. ID proof: JPG/PNG/PDF up to 5 MB, no scripts. |
| `alembic check` reports changes | Generate and review a new migration. |
| Lost Super Admin access | `python -m app.cli create-super-admin --allow-additional ...` on the server. |
