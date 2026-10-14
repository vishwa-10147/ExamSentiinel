# Installation

Two ways to run ExamSentinel: **natively** (fastest for development; SQLite, no Redis) or
with **Docker Compose** (Postgres, Redis, backend, frontend, code runner). Either way, code
execution needs the Piston container, so Docker is required for Run/Submit.

The native setup with the Piston container was verified on Windows 11 with Python 3.12,
Node.js LTS and Docker Desktop (2026-10-14). The full `docker compose up` stack was not
re-run in that verification. On macOS/Linux use `.venv/bin/python` instead of
`.venv/Scripts/python`.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | 3.13+ may lack wheels for some dependencies |
| Node.js | 20+ LTS | |
| Docker | Desktop or Engine with Compose v2 | for Piston (and the full stack) |
| Git | any | |

## 1. Native development setup

```bash
git clone <repository-url> ExamSentinel
cd ExamSentinel

# Backend dependencies (virtualenv at the repo root)
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
# Optional: webcam phone/person detection and interview transcription (CPU PyTorch, ultralytics, faster-whisper)
.venv/Scripts/python -m pip install -r backend/requirements-ai.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### Configuration

```bash
cp .env.example backend/.env          # then edit: at least SECRET_KEY
```

`backend/.env` is git-ignored and loaded by `backend/app/core/config.py`; real environment
variables override it. The defaults in `.env.example` use SQLite
(`backend/examsentinel_dev.db`) and point `PISTON_URL` at `localhost:2000`.

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

### Code runner (Piston)

```bash
docker compose -f docker-compose.piston.yml up -d --build
.venv/Scripts/python scripts/install_piston_runtimes.py     # once: python, node, java, gcc, sqlite3
curl http://localhost:2000/api/v2/runtimes                   # lists the installed runtimes
```

Runtimes live in the `piston_packages` Docker volume and survive restarts.

### Start

```bash
# terminal 1
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000 --reload
# terminal 2
cd frontend && npm run dev
```

With a SQLite `DATABASE_URL` the backend creates the schema on startup. Alembic migrations
are for PostgreSQL only.

### Seed data

```bash
cd backend
../.venv/Scripts/python seed_admin.py       # demo admin/proctor/reviewer/candidate accounts (development only)
../.venv/Scripts/python seed_practice.py    # 116 DSA + 11 SQL problems; idempotent, ~30 s
```

The demo accounts are `admin@`, `proctor@`, `reviewer@` and `candidate@sentinel.edu`;
their shared development password is printed by `seed_admin.py`. In production use
`ADMIN_EMAIL`/`ADMIN_PASSWORD` instead (see [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)).

### Check it works

```bash
curl http://localhost:8000/api/health        # database healthy; "degraded" without Redis is expected
```

Open http://localhost:3000, sign in as the candidate, go to **Problem Set**, open
*Pair With Target Sum* and press **Run**.

## 2. Docker Compose (full stack)

```bash
cp .env.example .env                        # compose reads .env from the repo root
docker compose up -d --build                # postgres, redis, backend, frontend, piston
python scripts/install_piston_runtimes.py   # once
docker compose exec backend alembic upgrade head
docker compose exec backend python seed_admin.py
docker compose exec backend python seed_practice.py
```

Frontend http://localhost:3000, API http://localhost:8000/docs. The backend reaches the
engine at `http://piston:2000/api/v2/execute`. Do not also start
`docker-compose.piston.yml` — both define the `examsentinel-piston` container.

## 3. Production

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) (`docker-compose.prod.yml`, ECS/EC2, RDS,
ElastiCache, S3) and the security requirements in [SECURITY.md](SECURITY.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Run/Submit says *execution engine unavailable* | `docker ps` should show `examsentinel-piston`; start it and run `install_piston_runtimes.py` |
| `PayloadTooLargeError` in backend logs | the stock Piston image is running; rebuild ours: `docker compose -f docker-compose.piston.yml up -d --build` |
| Every run fails with *runtime unknown* | runtimes not installed in the volume — run `scripts/install_piston_runtimes.py` |
| `/api/health` shows `degraded` | Redis is not running; this is fine locally (features fall back) |
| Backend fails to start: cannot connect to Postgres | `backend/.env` is missing, so the Postgres default is used; set the SQLite `DATABASE_URL` |
| Frontend pages stuck on "Checking access…" | stale `.next` build from another dev server: stop it, delete `frontend/.next`, `npm run dev` |
| Login says *Logged in from another browser/session* | single-session lock: the account signed in elsewhere; sign in again |
| `pytest` permission error on `.pytest_cache` | run with `-p no:cacheprovider` |
| `PermissionError`/`dubious ownership` from git on Windows | the checkout is owned by another user SID: `git -c safe.directory=<path> …` |
