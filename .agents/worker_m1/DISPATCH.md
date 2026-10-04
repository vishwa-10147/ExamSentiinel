# Dispatch: Milestone 1 Worker (Platform Foundation, Documentation & Core Services)

## Identity
- Role: Platform Foundation Implementer
- Agent Name: `worker_m1`
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`

## Mandatory References
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (MUST read before starting)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md`
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\survey_report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
You exclusively own:
- `docs/` (`docs/readme.md`, `docs/plan.md`, `docs/explain.md`, `docs/prompt.md`)
- `docker-compose.yml`, `.env.example`, `.gitignore`
- `backend/` (`backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/Dockerfile`, `backend/requirements.txt`)
- `frontend/` (`frontend/app/`, `frontend/components/`, `frontend/hooks/`, `frontend/services/`, `frontend/package.json`, `frontend/Dockerfile`)
DO NOT touch `e2e-tests/` or `TEST_INFRA.md` (owned by `test_writer_e2e`).

## Implementation Scope (Milestone 1 — Features 1 to 7)
1. **Documentation Suite**:
   Create the exact 4 files in `docs/`:
   - `docs/readme.md`: 8 tracks, tech stack, getting started, 5 design principles.
   - `docs/plan.md`: 20-phase build plan, repo structure, database tables catalog, build order, DoD.
   - `docs/explain.md`: System design rationale for all 16 subsystem areas.
   - `docs/prompt.md`: AI coding agent rules, 8 ground rules, 12 non-negotiable constraints.
   (Follow the exact content and structure specified in `ORIGINAL_REQUEST.md` lines 14–497).

2. **Docker Compose & Environment**:
   - `docker-compose.yml` with services: `postgres` (PostgreSQL 16), `redis` (Redis 7), `backend` (FastAPI), `frontend` (Next.js 14), `sandbox-worker`.
   - Health checks, persistent volumes, environment variables (`.env.example`).

3. **Backend Foundation & Database**:
   - FastAPI application setup with async SQLAlchemy 2.0 and asyncpg.
   - Database connection and session management (`backend/app/core/database.py`).
   - Security & JWT utilities (`backend/app/core/security.py`, access & refresh tokens, bcrypt password hashing).
   - Configuration management via pydantic-settings (`backend/app/core/config.py`).
   - Alembic migrations setup (`backend/alembic/`) with initial migration creating `institutions`, `users`, `audit_logs`.
   - User roles: `admin`, `proctor`, `reviewer`, `candidate`.
   - Endpoints:
     - `POST /api/auth/register` (Register new user with hashed password)
     - `POST /api/auth/login` (Authenticate and issue JWT access + refresh tokens)
     - `POST /api/auth/refresh` (Refresh access token)
     - `GET /api/auth/me` (Return current user profile and role)
     - `GET /api/health` (Service health check verifying DB and Redis connectivity)
   - RBAC dependency / middleware ensuring role-based protection on routes.
   - Structlog structured JSON logging with request correlation ID middleware.

4. **Frontend Base Shell**:
   - Next.js 14+ App Router structure with TypeScript and Tailwind CSS.
   - Root layout with responsive header, navigation, and theme.
   - Auth Context (`frontend/contexts/AuthContext.tsx`) and API client (`frontend/services/apiClient.ts`).
   - Login page (`frontend/app/auth/login/page.tsx`) with form validation and JWT token storage.
   - Dashboard shell (`frontend/app/dashboard/page.tsx`) with role-based routing.

5. **Testing & Verification**:
   - Write unit and API integration tests in `backend/tests/` verifying:
     * User registration with password hashing
     * JWT login and token expiration / validation
     * Refresh token rotation
     * Protected route access (admin vs candidate)
     * Health check endpoint
   - Run the tests using pytest.
   - Document commands executed and full pass/fail output in your handoff report.

## Deliverables
- Fully working, tested code in `docs/`, `backend/`, `frontend/`, `docker-compose.yml`.
- Write your self-contained report to `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\handoff.md`.
- Include commands run, test execution outputs, and verification details.
- Notify parent orchestrator via `send_message` when complete.

## 2026-09-16T10:51:19Z
<USER_REQUEST>
You are worker_m1, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\
Read d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md, d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md, and d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\DISPATCH.md.
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Your task: Implement Milestone 1 (Features 1–7):
1. Documentation in docs/ (readme.md, plan.md, explain.md, prompt.md) matching ORIGINAL_REQUEST.md.
2. docker-compose.yml, .env.example, .gitignore.
3. Backend setup: FastAPI, async SQLAlchemy, PostgreSQL models (institutions, users, audit_logs), Alembic migrations, security/JWT auth, RBAC (admin, proctor, reviewer, candidate), auth endpoints (/api/auth/register, /login, /refresh, /me), and /api/health.
4. Frontend base: Next.js 14, Tailwind CSS, Auth Context, Login page, Dashboard shell.
5. Write unit and API tests in backend/tests/ and execute pytest to verify all tests pass.
Write your comprehensive handoff report to d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\handoff.md including test commands and pass/fail outputs. Update your progress.md regularly. When finished, send a message to the orchestrator.
</USER_REQUEST>
