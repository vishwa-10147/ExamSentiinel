# Setup

How to install and run ExamSentinel on a development machine, as a full Docker stack, and where
to go for production. Every path below was run on 2026-10-16 unless marked otherwise.

## Contents

- [Choose a setup](#choose-a-setup)
- [Prerequisites](#prerequisites)
- [Option A: one command on Windows](#option-a-one-command-on-windows)
- [Option B: manual setup on Windows, Linux or macOS](#option-b-manual-setup-on-windows-linux-or-macos)
- [Option C: the whole stack in Docker](#option-c-the-whole-stack-in-docker)
- [Demo accounts](#demo-accounts)
- [Verify the installation](#verify-the-installation)
- [Optional AI features](#optional-ai-features)
- [Production](#production)
- [Next steps](#next-steps)

## Choose a setup

| Goal | Use | Database | Verified |
|---|---|---|---|
| Develop on Windows with the least effort | [Option A](#option-a-one-command-on-windows) `start-local.cmd` | SQLite | Windows 11 |
| Develop on any OS, step by step | [Option B](#option-b-manual-setup-on-windows-linux-or-macos) | SQLite | Windows 11 (the same commands apply to Linux and macOS; see the platform notes) |
| Try the full stack with PostgreSQL and Redis | [Option C](#option-c-the-whole-stack-in-docker) `docker compose` | PostgreSQL 16 | Windows 11 + Docker Desktop |
| Run it for real users | [Production](#production) | PostgreSQL 16 | Rehearsed locally; see [Production readiness](docs/PRODUCTION_READINESS.md) |

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Git | any recent | cloning |
| Python | **3.12** | the API (newer versions may lack wheels for some dependencies) |
| Node.js | **20 LTS** or newer, with npm | the web app |
| Docker | Docker Desktop, or Docker Engine with the Compose plugin | the code-execution engine (always), and Option C |

Docker is required even for local development: Run, Submit, the playground and coding exam
questions execute code in the Piston container.

**Platform notes**

- **Windows 10/11:** fully supported; `start-local.cmd` automates Option B.
- **Linux (x86-64):** the API, web app and engine run natively or in Docker. The production
  images and the [campus server kit](deploy/campus/README.md) are Linux containers and were
  verified there; the native development steps were verified on Windows only.
- **macOS:** the Python and Node parts work as on Linux. The code-execution engine image is
  **amd64-only**: on Intel Macs it runs normally; on Apple Silicon Docker Desktop must emulate it,
  which has **not** been verified.

## Option A: one command on Windows

```bat
git clone https://github.com/vishwa-10147/ExamSentiinel.git
cd ExamSentiinel
start-local.cmd
```

The first run creates the virtual environment, installs the dependencies, writes
`backend/.env` (with a generated `SECRET_KEY`) and `frontend/.env.local`, starts Docker Desktop if
needed, starts the code-execution engine and installs its runtimes, launches the API and web app
in their own windows, seeds demo data, and opens the browser when everything is healthy. Later
runs skip what is already done.

| Command | Effect |
|---|---|
| `start-local.cmd` | Start everything |
| `start-local.cmd --seed` | Start and re-run the (idempotent) seeders |
| `start-local.cmd stop` | Stop the API, web app and engine; data is kept |

Set `NO_BROWSER=1` to skip opening the browser.

## Option B: manual setup on Windows, Linux or macOS

Commands use `.venv/bin/python` (Linux, macOS). On Windows use `.venv\Scripts\python`.

**1. Install dependencies**

```bash
git clone https://github.com/vishwa-10147/ExamSentiinel.git
cd ExamSentiinel
python3.12 -m venv .venv                         # Windows: py -3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd frontend && npm install && cd ..
```

`requirements.txt` is what the production image installs; `requirements-dev.txt` adds SQLite
support and pytest.

**2. Configure**

```bash
cp .env.example backend/.env
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\nNEXT_PUBLIC_SITE_URL=http://localhost:3000\n' > frontend/.env.local
```

Set `SECRET_KEY` in `backend/.env` (for example the output of `openssl rand -hex 32`). The file
is git-ignored and loaded by `backend/app/core/config.py`; real environment variables take
precedence. The defaults use a SQLite file (`backend/examsentinel_dev.db`) and the engine at
`127.0.0.1:2000`. Every variable is explained in [Configuration](docs/CONFIGURATION.md).

**3. Start the code-execution engine**

```bash
docker compose -f docker-compose.piston.yml up -d --build
.venv/bin/python scripts/install_piston_runtimes.py
```

The runtimes (Python 3.12, Node.js 20, Java 15, GCC 10.2 for C and C++, SQLite 3.36) download
once (about 1 GB) into the `piston_packages` volume.

**4. Start the API and the web app** (two terminals)

```bash
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload
```

```bash
cd frontend && npm run dev
```

With SQLite the API creates the schema on start-up, and adds columns introduced by newer
versions to an older local database. Alembic migrations are for PostgreSQL.

**5. Seed data**

```bash
cd backend
../.venv/bin/python seed_admin.py        # demo accounts (development only)
../.venv/bin/python seed_practice.py     # 116 DSA + 11 SQL problems, about 30 s
```

Both seeders are idempotent. Open <http://localhost:3000>; the interactive API reference is at
<http://localhost:8000/docs> (development only: it is switched off when `DEBUG=false`).

## Option C: the whole stack in Docker

Runs PostgreSQL, Redis, the API, the production build of the web app, and the engine in
containers (`docker-compose.yml`).

```bash
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env   # read by docker-compose.yml only
docker compose up -d --build
python scripts/install_piston_runtimes.py
docker compose exec backend alembic upgrade head
docker compose exec backend python seed_admin.py
docker compose exec backend python seed_practice.py
```

Do not copy `.env.example` to the root `.env` for this option: its development values (a SQLite
`DATABASE_URL`, `PISTON_URL` on `127.0.0.1`) would be passed into the containers. The stack's own
defaults are used for everything else; if you set `POSTGRES_PASSWORD`, set a matching
`DATABASE_URL` too.

The web app is at <http://localhost:3000> and the API at <http://localhost:8000>. Do not also run
`docker-compose.piston.yml`: both define the `examsentinel-piston` container (they share the
runtimes volume). Stop with `docker compose down`; add `-v` to delete the database.

## Demo accounts

`seed_admin.py` creates these accounts only when `ENVIRONMENT` is not `production`:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@sentinel.edu` | `DemoPass123!` |
| Proctor | `proctor@sentinel.edu` | `DemoPass123!` |
| Reviewer | `reviewer@sentinel.edu` | `DemoPass123!` |
| Candidate | `candidate@sentinel.edu` | `DemoPass123!` |

In production it creates a single administrator from `ADMIN_EMAIL` and `ADMIN_PASSWORD`
instead. Each account allows one active session: signing in elsewhere ends the previous one.

## Verify the installation

```bash
curl http://localhost:8000/api/health
```

`database` and `code_engine` should be `healthy`. An overall `degraded` because `redis` is
unhealthy is expected in Options A and B (Redis is optional for a single API process).

Then sign in as the candidate, open **Problem Set → Pair With Target Sum** and press **Run**;
the sample tests should pass within a few seconds. To check everything, run the test suites in
[Testing](docs/TESTING.md).

## Optional AI features

Server-side webcam analysis (phone and extra-person detection with YOLO11n) and interview
speech-to-text (faster-whisper) need CPU PyTorch and related packages:

```bash
.venv/bin/python -m pip install -r backend/requirements-ai.txt
```

Without them the API runs normally and reports phone detection as unavailable; in-browser face
detection works either way. Docker images include them when built with `WITH_AI=true`.

## Production

| Target | Guide |
|---|---|
| One college or company server (Linux + Docker), HTTPS, nightly backups | [deploy/campus/README.md](deploy/campus/README.md) |
| AWS (ECS, RDS, ElastiCache, S3, EC2 for the engine) | [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) |
| Which to choose, rollback and recovery | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

Production differs from development in ways the API enforces: it refuses to start with debug
mode, a default secret key, non-HTTPS origins, SQLite or other unsafe settings, and it never
creates demo accounts.

## Next steps

- Something not working: [Troubleshooting](docs/TROUBLESHOOTING.md)
- How it fits together: [Architecture](docs/ARCHITECTURE.md)
- Running exams and reviewing: [Staff guide](docs/STAFF_GUIDE.md)
- Contributing: [Contributing](docs/CONTRIBUTING.md)

---

[Back to README](README.md) · [Documentation index](docs/README.md)
