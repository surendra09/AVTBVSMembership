# AVTBVS Membership – notes for Claude

Membership web app for Ayira Vaisyar Telugu Beri Vysya Sabha. See [README.md](../README.md) for the full guide and [docs/OPEN-ITEMS.md](../docs/OPEN-ITEMS.md) for go-live blockers.

## Layout
- `backend/` – FastAPI + SQLAlchemy 2 + Alembic (Python 3.12). App code in `backend/app/`, tests in `backend/tests/`.
- `frontend/` – React 18 + TypeScript + Vite + Tailwind. Pages in `frontend/src/pages/{public,user,admin}`, routes in `frontend/src/routes/AppRoutes.tsx`, nav in `frontend/src/layouts/PublicLayout.tsx`.
- `deployment/` – Dockerfiles, Nginx, scripts. `render.yaml` (Render API) and `vercel.json` (Vercel frontend + `/api` proxy) at repo root.
- `e2e/` – walkthrough script and sample upload files.

## Commands
Backend (from `backend/`, venv in `backend/.venv`):
- Run: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`
- Tests: `.\.venv\Scripts\python.exe -m pytest`
- Migrations: `alembic upgrade head`
- Local demo data: `python seed_demo.py` (SQLite only)

Frontend (from `frontend/`): `npm run dev`, `npm run build`, `npm run typecheck`, `npm test`.

## Local demo setup
- `backend/.env` uses SQLite (`sqlite:///./avtbvs.db`), `ENVIRONMENT=development`, console email/SMS.
- Demo users: `{handle}@avtbvs.test` / `{handle}1234` (arjun = Super Admin; priya, karthik = Admin; others = User).
- In development the OTP `123456` verifies email and mobile (`backend/app/services/auth.py`).

## Hosting (free demo)
- Frontend: Vercel – https://avtbvsmembership.vercel.app (rewrites `/api/*` to Render so cookies stay first-party).
- Backend: Render – `avtbvs-api` (Docker, runs `alembic upgrade head` on start; sleeps when idle; uploads are not persistent).
- Database: TiDB Cloud Starter (MySQL-compatible, TLS required, port 4000).
- If the Render URL changes, update the rewrite in both `vercel.json` and `frontend/vercel.json`.

## Rules
- Never commit or print secrets: `.env` files, `*.db`, and the credentials file outside the repo stay private.
- Never run `seed_demo.py` against TiDB/production – its passwords are public.
- Do not invent facts about the Sabha or community; use its config data or text the user supplies.
- The user runs git commit/push themselves unless they ask otherwise.
