# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

ExamSentinel: online exam platform with AI proctoring. Next.js 14 frontend (`frontend/`) → FastAPI backend (`backend/app/`) → PostgreSQL + Redis in Docker, or SQLite locally. `ai/` holds standalone YOLO / Whisper / MOSS modules; the backend does not import them (it uses `backend/app/services/*`).

## Skills

- `/run-local` — start backend + frontend natively (SQLite, no Docker), seed users, smoke test.
- `/backend-tests` — run pytest + frontend `tsc`.

## Layout

- `backend/app/api/` — route modules, all mounted under `/api` in `router.py`. `sessions` is mounted at both `/exam/sessions` and `/sessions`; `proctoring` at both `/proctoring` and `/telemetry`.
- `backend/app/services/` — business logic: `risk_engine.py` (weighted event score → LOW/MEDIUM/HIGH/CRITICAL; opens a ReviewCase at MEDIUM), `grading_service.py`, `sandbox_service.py` (Piston), `irt_service.py`.
- `backend/app/models/` — SQLAlchemy 2 models; `backend/alembic/versions/` — Postgres-only migrations.
- `frontend/services/apiClient.ts` — the single API client; tokens live in localStorage (no cookies). Only `app/admin/layout.tsx` guards routes by role.

## Rules

- AI risk scores are advisory. Never add code that penalises a candidate automatically; humans decide via `/reviewer` and `/api/reviews`.
- Model changes need a new Alembic migration (models and migrations have drifted before — see `011_*`). Guard Postgres-only SQL with a dialect check.
- Run `/backend-tests` after backend changes; keep the suite green.
- Settings come from `backend/app/core/config.py`, but several services read `os.getenv` directly (OPENAI_API_KEY, GEMINI_API_KEY, SMTP_*, AWS_*); those must be real env vars.
- `backend/.env`, `frontend/.env.local`, `*.db` are git-ignored — never commit secrets.
- Python 3.12 venv at repo root `.venv`; Node LTS at `C:\Program Files\nodejs`.
