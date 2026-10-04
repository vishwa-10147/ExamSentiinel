# Dispatch: Milestone 1 Sub-Orchestrator (Platform Foundation, Documentation & Core Services)

## Identity
- Role: Milestone 1 Sub-Orchestrator
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\sub_orch_m1\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`
- Parent Conversation ID: `ece9073c-dea0-4960-b4b8-49f426870db1`

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (Authoritative requirements)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md` (Architecture, Feature Inventory, Milestones, Code Layout)
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\survey_report.md` (Deep specs for docs & core platform)

## Milestone 1 Scope (Features 1–7)
1. **Documentation Suite in `docs/`**:
   - `docs/readme.md` (Tracks, tech stack, getting started, 5 design principles)
   - `docs/plan.md` (20-phase plan, repo layout, table list, build order)
   - `docs/explain.md` (Subsystem design rationale for all 16 areas)
   - `docs/prompt.md` (AI operating rules, 8 ground rules, 12 non-negotiable constraints)
   *Note*: Must match specifications in `ORIGINAL_REQUEST.md` verbatim.
2. **Containerization & Tooling**:
   - `docker-compose.yml` defining services: `postgres`, `redis`, `backend`, `frontend`, `sandbox-worker`.
   - Environment templates (`.env.example`) and health check endpoints.
3. **Database Foundation**:
   - PostgreSQL connection with async SQLAlchemy 2.0.
   - Alembic migration environment initialized.
   - Core tables: `institutions`, `users`, `audit_logs` with UUIDs and timestamp tracking.
4. **Authentication & Authorization**:
   - JWT token generation (access + refresh tokens) with bcrypt password hashing.
   - RBAC middleware supporting roles: `admin`, `proctor`, `reviewer`, `candidate`.
   - Endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`.
5. **Backend Project Structure**:
   - FastAPI modular layout (`backend/app/api/`, `backend/app/core/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`).
   - CORS, exception handlers, structlog request ID middleware.
6. **Frontend Project Shell**:
   - Next.js 14+ App Router shell with Tailwind CSS, Lucide icons, Auth Context, layout, and login page.
7. **Verification**:
   - Unit and API tests for auth endpoints, migrations, and health check passing.

## Execution Method
You are a sub-orchestrator. Apply the Project Pattern procedure:
- Create `SCOPE.md`, `BRIEFING.md`, `progress.md`.
- Dispatch Explorer -> Worker -> Reviewer(s) -> Challenger(s) -> Forensic Auditor (`teamwork_preview_auditor`).
- Gate check: all must pass; auditor has hard binary veto against cheating/stubs.
- Deliver passing milestone and handoff back to parent orchestrator.
