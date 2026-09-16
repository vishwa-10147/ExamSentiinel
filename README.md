# ExamSentinel

ExamSentinel is a full-stack examination platform for scheduled exams, candidate answer capture, proctoring signals, risk scoring, and human review. The system surfaces evidence for reviewers; it does not make an automated misconduct decision.

This README is for developers and testers who need to run the development stack, verify the API, and try the candidate exam flow locally.

## What is available

The repository includes:

- FastAPI backend with JWT authentication and role-based access control.
- PostgreSQL and Redis services managed by Docker Compose.
- Exam, question bank, enrollment, session, answer auto-save, and submission APIs.
- Candidate portal with question navigation, flagging, timer, and auto-save.
- Browser telemetry and proctoring event ingestion.
- Configurable risk scoring with human-review thresholds.
- WebSocket channels for dashboard, exam, and session monitoring.
- Human review queue, evidence retrieval, reviewer actions, and audit logging.
- Isolated execution-worker service scaffolding for later coding-exam work.
- Backend integration tests for authentication, authorization, exam sessions, and telemetry.

The coding-exam, interview, adaptive-testing, compliance, enterprise-integration, and production operations tracks remain under development. Do not treat this development stack as production-ready.

## Repository layout

```text
ExamSentinel/
├── backend/              FastAPI application, models, migrations, and tests
├── frontend/             Next.js candidate and dashboard application
├── execution-workers/    Redis-backed execution worker scaffold
├── e2e-tests/            Opaque-box feature and boundary test suites
├── docs/                 Product plan, design rationale, and agent guidance
├── docker-compose.yml    Local PostgreSQL, Redis, backend, frontend, and worker stack
└── .env.example          Development environment template
```

## Prerequisites

Install the following tools before you begin:

- Docker Desktop with Docker Compose.
- Git.
- Python 3.11 or later for tests run outside Docker.
- Node.js 20 or later and npm for frontend work outside Docker.

Docker is the recommended path because it supplies PostgreSQL, Redis, and the service network expected by the application.

## Configure the environment

Copy the development environment template to `.env` from the repository root.

```powershell
Copy-Item .env.example .env
```

The template uses development-only PostgreSQL credentials and a development JWT secret. Replace `SECRET_KEY` before using the application outside a local development environment. Never commit `.env` or real credentials.

The most useful variables are:

| Variable | Development value | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/examsentinel` | Async backend database URL inside Compose |
| `REDIS_URL` | `redis://redis:6379/0` | Redis queue and cache URL inside Compose |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser URL for the backend API |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | Browser URL for WebSocket connections |
| `SANDBOX_TIMEOUT_SEC` | `5.0` | Development execution timeout setting |

## Start the development stack

From the repository root, build and start all services:

```powershell
docker compose up -d --build
```

Apply the database migrations:

```powershell
docker compose exec backend python -m alembic upgrade head
```

Seed repeatable development data for manual trials:

```powershell
docker compose exec backend python /scripts/seed_demo_data.py
```

The command prints demo credentials and the created exam ID. To run the seed
script from the host instead, install the backend requirements and run:

```powershell
python scripts/seed_demo_data.py
```

Check service status:

```powershell
docker compose ps
```

Open these URLs after the services start:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend health: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Swagger API reference: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc API reference: [http://localhost:8000/redoc](http://localhost:8000/redoc)

To follow backend logs:

```powershell
docker compose logs -f backend
```

To stop the stack without deleting database data:

```powershell
docker compose down
```

To remove the local database and Redis volumes as well, use this destructive command:

```powershell
docker compose down -v
```

## Run backend tests

Run the complete backend test suite in the backend container:

```powershell
docker compose exec backend pytest tests -q
```

Run the focused exam-engine and telemetry suites:

```powershell
docker compose exec backend pytest tests/test_exam_engine.py tests/test_proctoring.py -q
```

If you installed the backend requirements locally, run the same commands from `backend`:

```powershell
Set-Location backend
python -m pytest tests -q
```

The test suite creates an isolated SQLite database for each test. It does not modify the Compose PostgreSQL database.

## Run frontend checks

Install frontend dependencies when you work outside the frontend container:

```powershell
Set-Location frontend
npm install
```

Run the development server:

```powershell
npm run dev
```

Run the production build check:

```powershell
npm run build
```

Run the configured lint command:

```powershell
npm run lint
```

The frontend reads `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` from the environment. When you run the frontend on the host, use `localhost` URLs. When frontend code runs inside Compose, the browser still needs a URL reachable from the host browser, so keep the public values set to `http://localhost:8000` and `ws://localhost:8000`.

## Try the candidate exam flow

Use the Swagger UI for the first trial because it displays request and response schemas.

1. Open [Swagger UI](http://localhost:8000/docs).
2. Register a development user with `POST /api/auth/register` or use an existing user.
3. Sign in with `POST /api/auth/login` and copy the access token.
4. Click **Authorize** and enter `Bearer ACCESS_TOKEN`.
5. As an administrator, create a question with `POST /api/questions`.
6. Create an exam with `POST /api/exams`.
7. Assign the question with `POST /api/exams/{exam_id}/questions`.
8. Publish the exam with `POST /api/exams/{exam_id}/publish`.
9. Enroll a candidate with `POST /api/exams/{exam_id}/enroll`.
10. Sign in as the candidate and call `POST /api/exam/sessions/start`.
11. Save an answer with `POST /api/exam/sessions/{session_id}/answers`.
12. Submit a browser signal with `POST /api/telemetry/events`.
13. Read the updated score with `GET /api/proctoring/risk/{session_id}`.
14. Submit the exam with `POST /api/exam/sessions/{session_id}/submit`.
15. As a reviewer, inspect `/api/reviews` and the case evidence endpoint.

The candidate portal is available at [http://localhost:3000/dashboard](http://localhost:3000/dashboard). A candidate can open an enrolled exam, complete the readiness step, answer questions, flag questions, and submit the session.

## Useful API paths

| Area | Paths |
| --- | --- |
| Authentication | `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me` |
| Exams | `/api/exams`, `/api/exams/{exam_id}/publish`, `/api/exams/{exam_id}/enroll` |
| Questions | `/api/questions` |
| Candidate sessions | `/api/exam/sessions/start`, `/api/exam/sessions/{session_id}` |
| Answers | `/api/exam/sessions/{session_id}/answers` |
| Proctoring | `/api/proctoring/events`, `/api/telemetry/events`, `/api/proctoring/risk/{session_id}` |
| Human review | `/api/reviews`, `/api/reviews/{case_id}/evidence`, `/api/reviews/{case_id}/actions` |
| Dashboard | `/api/dashboard/active-sessions`, `/api/dashboard/stats` |
| WebSockets | `/api/ws/dashboard`, `/api/ws/exam/{exam_id}`, `/api/ws/session/{session_id}` |

WebSocket authentication uses the access token as a query parameter because the browser WebSocket API does not support custom authorization headers:

```text
ws://localhost:8000/api/ws/dashboard?token=ACCESS_TOKEN
```

## Database migrations

Show the current migration revision:

```powershell
docker compose exec backend python -m alembic current
```

Apply pending migrations:

```powershell
docker compose exec backend python -m alembic upgrade head
```

Create a migration after changing SQLAlchemy models:

```powershell
docker compose exec backend python -m alembic revision -m "describe the schema change"
```

Review generated migrations before applying them. A migration must preserve UUID keys, foreign-key behavior, indexes, and timestamp columns used by the existing models.

## Test the development E2E clients

The `e2e-tests` directory contains Python clients and tiered tests that exercise a running backend. Start the Compose stack first, then install its dependencies:

```powershell
Set-Location e2e-tests
python -m pip install -r requirements.txt
python runner.py
```

Some E2E cases describe planned milestone behavior and may be skipped or require additional seed data while the later milestones are being implemented. Treat backend integration tests as the reliable regression gate for the implemented API surface.

## Development principles

- Risk scores and detector output are reviewer-facing signals, never automated guilt findings.
- VPN, device, tab, and browser signals never block a candidate automatically.
- Candidate work must survive reconnects and out-of-order auto-save requests.
- Monitoring capability must be disclosed before capture begins.
- New event types must be registered with the risk engine and covered by tests.
- Security-sensitive integrations must fail closed or report an explicit unavailable state; they must not claim coverage they do not provide.
- Do not place secrets in source code, frontend bundles, test fixtures, or documentation.

## Current development boundaries

The following areas are not complete production integrations yet:

- Webcam computer-vision inference and phone detection.
- Sandboxed multi-language code execution and autograding.
- Live and asynchronous interview rooms, recording, and transcription.
- Adaptive testing, offline IndexedDB replay, and LMS/SSO connectors.
- Retention jobs, appeals, notifications, calendar providers, cost governance, and disaster-recovery drills.
- Production deployment, monitoring, and backup verification.

Use `docs/plan.md` for the phased delivery plan and `docs/explain.md` for the design rationale. Update this README when a development boundary becomes a verified, tested capability.

## Troubleshooting

### The backend cannot connect to PostgreSQL

Check that PostgreSQL is healthy:

```powershell
docker compose ps postgres
```

Then inspect its logs:

```powershell
docker compose logs postgres
```

Inside Compose, the database host is `postgres`. From a host-installed backend, use `localhost` and the published PostgreSQL port instead.

### The frontend shows API connection errors

Confirm that the backend responds at [http://localhost:8000/api/health](http://localhost:8000/api/health), then check `NEXT_PUBLIC_API_URL` in `.env`. Restart the frontend after changing a `NEXT_PUBLIC_*` variable.

### A migration command is not found

Run Alembic through the backend Python environment instead of calling the executable directly:

```powershell
docker compose exec backend python -m alembic upgrade head
```

### The application has stale development data

Stop the stack and remove the development volumes, then start it again:

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec backend python -m alembic upgrade head
```

This permanently deletes local PostgreSQL and Redis data.
