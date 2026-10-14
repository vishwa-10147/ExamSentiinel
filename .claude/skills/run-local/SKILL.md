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

## Smoke test

1. `curl localhost:8000/api/health` → `database: healthy`. `redis: unhealthy` + HTTP 503 is expected without Redis; the app degrades gracefully.
2. Open `http://localhost:3000/auth/login`, sign in as `reviewer@sentinel.edu` → lands on `/reviewer/dashboard`; `GET /api/proctoring/review-queue` returns 200.

## Known limits in local mode

- No Redis → forgot-password / OTP endpoints return 500; coding answers fall back to manual grading.
- Code execution calls the public Piston API (`emkc.org`), which needs a whitelisted token — runs may return `system_error`.
- YOLO / Whisper packages are not installed → proctoring vision and interview transcription use mock fallbacks.
