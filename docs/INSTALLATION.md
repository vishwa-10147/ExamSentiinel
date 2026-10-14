# Installation

This guide covers running ExamSentinel on a development machine — with a single command on
Windows, manually on any operating system, or as a full Docker Compose stack. For production,
see [AWS deployment](AWS_DEPLOYMENT.md).

## Contents

- [Prerequisites](#prerequisites)
- [1. Local development](#1-local-development)
  - [Option A: one command (Windows)](#option-a-one-command-windows)
  - [Option B: manual setup](#option-b-manual-setup)
- [2. Docker Compose (full stack)](#2-docker-compose-full-stack)
- [Demo accounts](#demo-accounts)
- [Verifying the installation](#verifying-the-installation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | Newer versions may lack wheels for some dependencies |
| Node.js | 20 LTS or newer | |
| Docker | Docker Desktop, or Docker Engine with Compose v2 | Runs the code-execution engine |
| Git | Any recent version | |

Code execution (Run, Submit, the playground and coding exam questions) always needs the Piston
container, so Docker is required even for local development.

## 1. Local development

The local setup runs the API and web app natively against a SQLite database. Redis is optional.

### Option A: one command (Windows)

```bat
start-local.cmd
```

On the first run the script creates the virtual environment, installs dependencies, writes
`backend/.env` (with a generated `SECRET_KEY`) and `frontend/.env.local`, starts Docker Desktop if
needed, starts the code-execution engine and installs its runtimes, launches the API and web app
in their own windows, seeds demo data, and opens the browser once everything is healthy. Later
runs skip the steps that are already done.

| Command | Effect |
|---|---|
| `start-local.cmd` | Start everything |
| `start-local.cmd --seed` | Start and re-run the (idempotent) seeders |
| `stop-local.cmd` | Stop the API, web app and engine; data is kept |

Set `NO_BROWSER=1` to skip opening the browser.

### Option B: manual setup

The commands use `.venv/bin/python` (macOS and Linux). On Windows use `.venv\Scripts\python`.

**1. Install dependencies**

```bash
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

Optional AI features (webcam phone and person detection, interview transcription) need CPU
PyTorch, Ultralytics and faster-whisper:

```bash
.venv/bin/python -m pip install -r backend/requirements-ai.txt
```

**2. Configure**

```bash
cp .env.example backend/.env
```

Set `SECRET_KEY` in `backend/.env` (for example, the output of `openssl rand -hex 32`). The file
is git-ignored and loaded by `backend/app/core/config.py`; real environment variables take
precedence. The defaults use SQLite (`backend/examsentinel_dev.db`) and point `PISTON_URL` at
`localhost:2000`.

Create `frontend/.env.local`:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

**3. Start the code-execution engine**

```bash
docker compose -f docker-compose.piston.yml up -d --build
.venv/bin/python scripts/install_piston_runtimes.py
```

The runtimes (Python, Node.js, Java, GCC and SQLite) are stored in the `piston_packages` volume
and only need to be installed once.

**4. Start the API and web app** (two terminals)

```bash
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload
```

```bash
cd frontend && npm run dev
```

With a SQLite `DATABASE_URL`, the API creates the schema on startup. Alembic migrations are for
PostgreSQL only.

**5. Seed data**

```bash
cd backend
../.venv/bin/python seed_admin.py
../.venv/bin/python seed_practice.py
```

`seed_practice.py` loads 116 DSA and 11 SQL problems in about 30 seconds. Both seeders are
idempotent.

## 2. Docker Compose (full stack)

Runs PostgreSQL, Redis, the API, the web app and the code-execution engine in containers.

```bash
cp .env.example .env
docker compose up -d --build
python scripts/install_piston_runtimes.py
docker compose exec backend alembic upgrade head
docker compose exec backend python seed_admin.py
docker compose exec backend python seed_practice.py
```

The web app is served on <http://localhost:3000> and the API on <http://localhost:8000>. Inside
the stack the API reaches the engine at `http://piston:2000/api/v2/execute`. Do not also start
`docker-compose.piston.yml`: both files define the `examsentinel-piston` container.

> The Docker Compose path is provided for convenience; the native setup is the one verified most
> recently (2026-10-14).

## Demo accounts

`seed_admin.py` creates these accounts in development environments only:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@sentinel.edu` | `DemoPass123!` |
| Proctor | `proctor@sentinel.edu` | `DemoPass123!` |
| Reviewer | `reviewer@sentinel.edu` | `DemoPass123!` |
| Candidate | `candidate@sentinel.edu` | `DemoPass123!` |

In production, `seed_admin.py` instead creates a single administrator from `ADMIN_EMAIL` and
`ADMIN_PASSWORD`. Each account allows one active session at a time.

## Verifying the installation

```bash
curl http://localhost:8000/api/health
```

The database should report `healthy`. An overall status of `degraded` only means Redis is not
running, which is expected for local development.

Then open <http://localhost:3000>, sign in as the candidate, open **Problem Set →
Pair With Target Sum** and press **Run**. The sample tests should pass in a few seconds.

## Troubleshooting

| Symptom | Resolution |
|---|---|
| Run or Submit reports *execution engine unavailable* | Check `docker ps` lists `examsentinel-piston`; start it and run `scripts/install_piston_runtimes.py` |
| `PayloadTooLargeError` in the API log | The stock Piston image is running. Rebuild ours: `docker compose -f docker-compose.piston.yml up -d --build` |
| Every run fails with *runtime unknown* | Runtimes are not installed in the volume; run `scripts/install_piston_runtimes.py` |
| The API tries to connect to PostgreSQL | `backend/.env` is missing, so the PostgreSQL default is used. Copy `.env.example` |
| Pages stay on *Checking access…* | A stale `.next` build from another dev server. Stop it, delete `frontend/.next`, run `npm run dev` |
| *Logged in from another browser/session* | The account signed in elsewhere; sign in again |
| `stop-local.cmd` reports a port used by another program | Something other than ExamSentinel is listening on 8000 or 3000; it is left running |
| pytest permission error on `.pytest_cache` | Run pytest with `-p no:cacheprovider` |
| Git reports *dubious ownership* on Windows | The checkout belongs to another user account: `git config --global --add safe.directory <path>` |

---

[Back to README](../README.md) · [Documentation index](README.md)
