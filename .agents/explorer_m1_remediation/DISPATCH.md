# Dispatch: Milestone 1 Remediation Explorer

## Identity
- Role: Remediation Explorer
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\`
- Target: Produce concrete fix strategy for Milestone 1 gate defects

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md`
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\handoff.md`
4. `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_2\handoff.md`
5. `d:\vishwa47\v47Studio\ExamSentinel\.agents\reviewer_m1_2\handoff.md`
6. `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1\GATE_STATUS.md`

## Defect Inventory to Address
1. **CRITICAL — Privilege Escalation in `register_user`**:
   `POST /api/auth/register` accepts client-provided `role`. Public registration MUST force `role = UserRole.CANDIDATE`. Admin/Proctor/Reviewer accounts must be provisionable via an authenticated admin route (`POST /api/users` with `require_roles([UserRole.ADMIN])`).
2. **CRITICAL — Missing Refresh Token Revocation & Single-Use Rotation**:
   Rotated refresh tokens must be invalidated so that replaying an old refresh token returns HTTP 401. Design a clean, persistent token tracking mechanism (database table `refresh_tokens` or Redis) tracking `jti`, `user_id`, and `revoked` status.
3. **CRITICAL — Docker Compose Build Failure**:
   `docker-compose.yml` specifies `context: ./execution-workers`, but the directory does not exist. Create the scaffolded `execution-workers/` directory with `runner.py`, `Dockerfile`, and `requirements.txt`.
4. **HIGH — Concurrency Crash on Duplicate Registration**:
   Catch `IntegrityError` in `register_user` and return clean HTTP 400 Bad Request. Also check `institution_id` existence if provided to prevent foreign key crashes.
5. **MEDIUM — Audit Logging Gaps**:
   Add audit logging for failed logins (`LOGIN_FAILED`) and 403 Forbidden attempts (`ACCESS_DENIED`). Truncate `user_agent` to 500 chars before storing in `AuditLog`.
6. **MEDIUM — Enum Mismatch**:
   Align Alembic migration and SQLAlchemy `User.role` definition so PostgreSQL handles types consistently.

## Deliverables
- Write detailed, file-by-file remediation plan and exact code fix specifications to `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\remediation_plan.md` and `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\handoff.md`.
- Notify parent orchestrator when complete.

## 2026-09-16T11:05:00Z
Received dispatch request:
Synthesize all review and challenge feedback and formulate a precise, file-by-file remediation plan for Milestone 1:
1. Fix Role Escalation in register_user (force CANDIDATE on public registration; add admin endpoint for staff).
2. Fix Refresh Token Revocation & Single-Use Rotation (track jti, block replay with HTTP 401).
3. Fix Missing ./execution-workers directory for docker compose build.
4. Fix Concurrency Crash on Duplicate Registration (catch IntegrityError -> 400).
5. Fix Audit Log blindspots (failed logins, 403s) and user_agent truncation.
6. Fix Enum mismatch between Alembic migration and SQLAlchemy model.
