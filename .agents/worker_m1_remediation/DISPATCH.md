# Dispatch: Milestone 1 Remediation Worker

## Identity
- Role: Platform Foundation Remediation Implementer
- Agent Name: `worker_m1_remediation`
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1_remediation\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`

## Mandatory References
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (MUST read first)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md`
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\remediation_plan.md` (MUST follow step-by-step)
4. `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
You exclusively own:
- `backend/app/` (models, schemas, api routes, security, database, deps)
- `backend/alembic/` (migrations)
- `backend/tests/` (unit, integration, and remediation tests)
- `execution-workers/` (scaffold files)
- `docker-compose.yml`
DO NOT touch `docs/` or `e2e-tests/`.

## Tasks & Responsibilities
Implement the complete file-by-file remediation plan from `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\remediation_plan.md`:
1. **DEF-01: Fix Role Escalation**:
   - In `backend/app/api/auth.py`, force `user.role = UserRole.CANDIDATE` unconditionally on public registration.
   - Create `backend/app/api/users.py` with `POST /api/users` protected by `require_roles([UserRole.ADMIN])` for provisioning staff accounts (`proctor`, `reviewer`, `admin`).
   - Register the new router in `backend/app/api/router.py`.
2. **DEF-02: Fix Refresh Token Revocation & Replay**:
   - Create `backend/app/models/refresh_token.py` (`RefreshToken` model tracking `id`, `user_id`, `jti`, `revoked`, `expires_at`, `created_at`).
   - Export in `backend/app/models/__init__.py`.
   - Update `backend/app/api/auth.py`: On login, record `RefreshToken`. On `/refresh`, verify that `jti` exists in DB and `revoked is False`. Mark it `revoked = True`. Issue new tokens and record the new refresh token. If a revoked token is presented, reject with HTTP 401. Add `POST /api/auth/logout`.
3. **DEF-03: Create `execution-workers/` Scaffold**:
   - Create `execution-workers/Dockerfile`, `execution-workers/requirements.txt`, and `execution-workers/runner.py` so `docker compose build` succeeds.
4. **DEF-04: Fix Concurrency Crash & Foreign Key Validation**:
   - In `register_user`, check `institution_id` existence if provided.
   - Wrap user creation commit in `try...except IntegrityError:` and return clean `HTTPException(400, detail="A user with this email address already exists")`.
5. **DEF-05: Fix Audit Log Blindspots & User-Agent Truncation**:
   - In `backend/app/api/auth.py`, log `LOGIN_FAILED` audit events on bad password or non-existent user.
   - In `backend/app/api/deps.py`, log `ACCESS_DENIED` in `require_roles` on 403 Forbidden.
   - In `backend/app/api/deps.py:log_audit_event()`, truncate `user_agent` to 500 characters (`user_agent[:500] if user_agent else None`).
6. **DEF-06: Fix Enum Mismatch**:
   - In `backend/app/models/user.py`, ensure `role` is defined with `name="user_role_enum", native_enum=True` matching Alembic migration `001_initial_core_schema.py`.
   - Update Alembic migration if needed to ensure `refresh_tokens` table is created or create migration `002_add_refresh_tokens.py`.
7. **Run All Tests**:
   - Run `pytest tests/test_adversarial.py`, `pytest tests/test_adversarial_m1_2.py`, `pytest tests/test_auth.py`, `pytest tests/test_rbac.py`, `pytest tests/test_health.py`.
   - Ensure ALL test suites pass (100% pass rate).

## Deliverables
- Fully working, tested code.
- Write your comprehensive handoff report to `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1_remediation\handoff.md` detailing test commands, execution outputs, and changes made.
- Send completion message to parent orchestrator.
