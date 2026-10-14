---
name: run-local
description: Start ExamSentinel locally without Docker — FastAPI backend on :8000 (SQLite) and Next.js frontend on :3000 — seed demo users and smoke-test login. Use when asked to run, start, launch, or demo the app locally.
argument-hint: "[backend|frontend|both]"
allowed-tools: Bash, Read
---

# Run ExamSentinel locally

Native dev setup verified on Windows 11, 2026-10-14. No Postgres, Redis or Docker required.

## Prerequisites (one-time)

- Python **3.12** (3.14/3.15 lack wheels for pyyaml etc.): `py install 3.12`
- Node.js LTS: `winget install -e --id OpenJS.NodeJS.LTS` (installs to `C:\Program Files\nodejs`)
- Backend venv at the repo root:
  ```bash
  py -3.12 -m venv .venv
  .venv/Scripts/python.exe -m pip install -r backend/requirements.txt
  ```
- Frontend deps: `cd frontend && npm install`

## Config files (git-ignored, create if missing)

`backend/.env` — pydantic-settings reads `.env` relative to the cwd, so it must live in `backend/`:
```
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///./examsentinel_dev.db
REDIS_URL=redis://localhost:6379/0
```

`frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

## Code runner (Piston, needs Docker Desktop)

The public Piston API is whitelist-only since 2026-02-15, so code execution
(practice problems, playground, coding exam questions) uses our own container:

```bash
docker compose -f docker-compose.piston.yml up -d --build
.venv/Scripts/python.exe scripts/install_piston_runtimes.py   # once; runtimes persist in a volume
```
The backend reaches it at `PISTON_URL` (default `http://localhost:2000/api/v2/execute`).
`infra/piston/Dockerfile` raises Piston's 100 kB request limit to 8 MB.

## Start

Preferred: the Browser pane via `.claude/launch.json` configs `backend` then `frontend` (`preview_start`).

Manual equivalent:
```bash
cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

With a `sqlite` DATABASE_URL the backend creates the schema on startup (`app/main.py` lifespan). Alembic migrations are Postgres-only — do not run `alembic upgrade` against SQLite.

## Seed demo users (once per fresh DB)

```bash
cd backend && ../.venv/Scripts/python.exe seed_admin.py
```
Creates `admin@`, `proctor@`, `reviewer@`, `candidate@sentinel.edu`; the shared demo password is in `seed_admin.py`.

Seed the practice problem bank (idempotent):
```bash
cd backend && ../.venv/Scripts/python.exe seed_practice.py
```

## Smoke test

1. `curl localhost:8000/api/health` → 200 with `database: healthy`; without Redis the status is `degraded` (Redis is optional).
2. Open `http://localhost:3000/auth/login`, sign in as `reviewer@sentinel.edu` → lands on `/reviewer/dashboard`; `GET /api/proctoring/review-queue` returns 200.
3. `python scripts/e2e_roles_smoke.py` → every step passes (exam lifecycle for all roles, coding grading, practice).

## Known limits in local mode

- No Redis → reset codes live in process memory and rate limiting is skipped (fine for one local process).
- No email provider → in DEBUG the password-reset code is written to the backend log.
- Docker Desktop stopped → the code runner is down; restart Docker and the `examsentinel-piston` container comes back.
- Without the Piston container, runs return `SYSTEM_ERROR` ("engine unavailable") and coding exam answers fall back to manual grading.
- YOLO / Whisper packages are not installed → proctoring vision and interview transcription use mock fallbacks.
