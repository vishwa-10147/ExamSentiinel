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
- Contests: `app/api/contests.py` (+ `/api/admin/contests`), `models/contest.py`. Contest submissions are
  practice submissions with `contest_id`, judged by the same queue; problems of a published, unfinished contest
  are hidden from practice (`practice.contest_locked_problem_ids`). UI: `/candidate/contests`, `/admin/contests`;
  the problem workspace takes `?contest=<slug>`.
- Several API processes: Redis carries live events (`websocket/manager.py`, own echoes skipped by `INSTANCE_ID`),
  interview rooms (`services/interview_hub.py`) and run slots (`core/user_slots.py`). Pub/sub readers must poll
  `get_message(timeout=PUBSUB_POLL_SECONDS)` — `listen()` dies on the client's 2 s socket timeout. Real check:
  `scripts/multi_process_check.py --a URL --b URL`.
- Production: `production_problems` in `app/core/config.py` refuses unsafe settings at start-up. Client IP =
  `request.client` only (uvicorn resolves it from `FORWARDED_ALLOW_IPS`); never read IP headers directly. Never
  import `practice_bank` from the API (5.8 s of CPU; topics live in `app/core/practice_topics.py`). Judging must not
  hold a DB connection while the engine runs. Monaco and the BlazeFace model are self-hosted (CSP in
  `frontend/next.config.js`). Rehearsal of the AWS topology: `deploy/rehearsal/`; schema check:
  `backend/check_migrations.py`; readiness status: `docs/PRODUCTION_READINESS.md`.
- Exams: one session per (exam, candidate) - a DB constraint (migration 017); `start` resumes, and a losing concurrent
  start resumes the winner. Answers go through `frontend/services/answerSync.ts` (latest per question, persisted,
  retried, flushed before submit); never report a submit the server has not confirmed. Metrics: CloudWatch EMF lines
  from `app/core/metrics.py` (production). Python deps: `requirements.txt` = the image; `requirements-dev.txt` adds
  SQLite and pytest. The frontend's API origin is `API_BASE_URL` in `services/apiClient.ts` only.
- Local SQLite: `create_all` plus `_sqlite_add_missing_columns` (app/main.py) adds new nullable/defaulted columns
  to an older dev database; Postgres still needs the Alembic migration.
- `frontend/services/apiClient.ts` — the single API client. Browser sessions are httpOnly cookies (`app/core/auth_cookies.py`): requests send `credentials: "include"`, `X-Auth-Mode: cookie` and `X-Requested-With` (required for cookie-authenticated writes); tokens never touch localStorage. Scripts/tests may still use `Authorization: Bearer`. `components/RoleAreaLayout.tsx` guards each role area in the UI; the API enforces roles regardless.

## Rules

- AI risk scores are advisory. Never add code that penalises a candidate automatically; humans decide via `/reviewer` and `/api/reviews`.
- Model changes need a new Alembic migration (models and migrations have drifted before — see `011_*`). Guard Postgres-only SQL with a dialect check.
- Run `/backend-tests` after backend changes; keep the suite green.
- Every caller of Redis has a fallback; use `redis_breaker` (`app/core/redis_client.py`) so an outage costs one timeout per 30 s, not one per request.
- Settings come from `backend/app/core/config.py`; several services read `os.getenv` directly (PISTON_URL, OPENAI_API_KEY, GEMINI_API_KEY, SMTP_*, AWS_*). `config.py` loads `backend/.env` into the environment for them; real env vars win.
- `backend/.env`, `frontend/.env.local`, `*.db` are git-ignored — never commit secrets.
- Python 3.12 venv at repo root `.venv`; Node LTS at `C:\Program Files\nodejs`.
