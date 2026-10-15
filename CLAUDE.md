# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

ExamSentinel: online exam platform with AI proctoring. Next.js 14 frontend (`frontend/`) → FastAPI backend (`backend/app/`) → PostgreSQL + Redis in Docker, or SQLite locally. `ai/` holds standalone YOLO / Whisper / MOSS modules; the backend does not import them (it uses `backend/app/services/*`).

## Skills

- `/run-local` — start backend + frontend natively (SQLite), the Piston code runner (Docker), seed data, smoke test.
- `/backend-tests` — run pytest, frontend `tsc`, and the live E2E script.
- `/practice-problems` — author/validate LeetCode-style problems; how the judge harness works.
- `/ai-proctoring` — cheating-detection signal flow, YOLO/BlazeFace, de-dup windows, auto-submit rules.
- `/backend`, `/frontend` — conventions to follow before changing either side.
- `/aws-deploy` — release checklist (manual only); full guide in `docs/AWS_DEPLOYMENT.md`.

## Layout

- `backend/app/api/` — route modules, all mounted under `/api` in `router.py`. `sessions` is mounted at both `/exam/sessions` and `/sessions`; `proctoring` at both `/proctoring` and `/telemetry`.
- `backend/app/services/` — business logic: `risk_engine.py` (weighted event score → LOW/MEDIUM/HIGH/CRITICAL; opens a ReviewCase at MEDIUM), `grading_service.py` (coding answers run on the sandbox), `sandbox_service.py` (self-hosted Piston via `PISTON_URL`), `practice_judge.py` (LeetCode-style judge), `judge_queue.py` (DB-backed queue for practice submissions: PENDING → workers; Submit waits ≤20 s then 202 + polling), `irt_service.py`. Load test: `scripts/load_test.py` (500 simultaneous students: all judged, ~33 verdicts/s; one API process saturates before Piston's ~75/s). `sandbox_service` keeps one pooled keep-alive httpx client per event loop - never open a client per call (cost 150-400 ms each).
- Code execution: `docker-compose.piston.yml` + `infra/piston/` (our Piston image). The public emkc.org API is whitelist-only — never point back at it. Large inputs go in files, not stdin (Piston truncates stdin past ~200 kB).
- `backend/app/models/` — SQLAlchemy 2 models; `backend/alembic/versions/` — Postgres-only migrations.
- `backend/practice_bank/` — 116 DSA + 11 SQL practice problems (permanent `number`s; append-only, shared seeded RNG); `seed_practice.py` computes expected outputs by running references. Docs: `docs/DSA_QUESTION_BANK.md`, `docs/CODE_EXECUTION.md`, `docs/SECURITY.md` (only verified controls), `docs/API.md`.
- `backend/tests/test_sandbox_engine.py` — real-Piston tests (isolation, limits, all references); skipped when the engine is down.
- `backend/requirements-ai.txt` — optional CPU PyTorch + ultralytics for webcam phone/person detection (`ai/models/yolo11n.pt`).
- Auth: password login and OpenID Connect SSO (`app/api/sso.py`, `services/sso_service.py`; providers via `SSO_*`
  env vars) share `issue_login_session` in `app/api/auth.py`. Password reset codes live in `services/otp_store.py`.
- Live interviews: `app/api/interviews.py` (consent, transcript, scores), `app/api/interview_ws.py` (WebRTC
  signalling relay, in-memory rooms), `services/transcription_service.py` (faster-whisper). UI: `/interview/[id]`,
  `/admin/interviews`.
- `frontend/services/apiClient.ts` — the single API client. Browser sessions are httpOnly cookies (`app/core/auth_cookies.py`): requests send `credentials: "include"`, `X-Auth-Mode: cookie` and `X-Requested-With` (required for cookie-authenticated writes); tokens never touch localStorage. Scripts/tests may still use `Authorization: Bearer`. `components/RoleAreaLayout.tsx` guards each role area in the UI; the API enforces roles regardless.

## Rules

- AI risk scores are advisory. Never add code that penalises a candidate automatically; humans decide via `/reviewer` and `/api/reviews`.
- Model changes need a new Alembic migration (models and migrations have drifted before — see `011_*`). Guard Postgres-only SQL with a dialect check.
- Run `/backend-tests` after backend changes; keep the suite green.
- Every caller of Redis has a fallback; use `redis_breaker` (`app/core/redis_client.py`) so an outage costs one timeout per 30 s, not one per request.
- Settings come from `backend/app/core/config.py`; several services read `os.getenv` directly (PISTON_URL, OPENAI_API_KEY, GEMINI_API_KEY, SMTP_*, AWS_*). `config.py` loads `backend/.env` into the environment for them; real env vars win.
- `backend/.env`, `frontend/.env.local`, `*.db` are git-ignored — never commit secrets.
- Python 3.12 venv at repo root `.venv`; Node LTS at `C:\Program Files\nodejs`.
