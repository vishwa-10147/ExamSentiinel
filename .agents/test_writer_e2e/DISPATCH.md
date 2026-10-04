# Dispatch: E2E Test Writer (Opaque-Box E2E Testing Track)

## Identity
- Role: E2E Test Architect & Writer
- Agent Name: `test_writer_e2e`
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\test_writer_e2e\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`

## Mandatory References
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (MUST read before starting)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md` (Architecture, Feature Inventory, Milestones, Code Layout)

## Exclusive File Ownership
You exclusively own:
- `TEST_INFRA.md` at project root
- `TEST_READY.md` at project root (when ready)
- `e2e-tests/` directory and all files inside (`e2e-tests/runner.py`, `e2e-tests/requirements.txt`, `e2e-tests/tier1_feature_coverage/`, `e2e-tests/tier2_boundary_corner/`, `e2e-tests/tier3_pairwise_interactions/`, `e2e-tests/tier4_real_world_workloads/`)
DO NOT modify application code in `backend/`, `frontend/`, or `docs/`.

## Mandatory Integrity Warning
DO NOT CHEAT. All tests must be authentic opaque-box verifications. DO NOT fabricate test results or write dummy assertions that pass vacuously. All assertions must evaluate real behavioral expectations.

## Tasks & Responsibilities
1. **Author `TEST_INFRA.md`** at `d:\vishwa47\v47Studio\ExamSentinel\TEST_INFRA.md`:
   - Follow the Project Pattern template:
     * Test Philosophy (opaque-box, requirement-driven, zero internal module coupling).
     * Feature Inventory table mapping every feature (1 to 69) to its test tiers.
     * Test Architecture & Runner design.
     * Real-World Application Scenarios (Tier 4) catalog.
     * Coverage Thresholds (Tier 1: >=5 per feature, Tier 2: >=5 per feature where boundaries exist, Tier 3: pairwise combinations, Tier 4: realistic scenarios).
2. **Build Test Runner & Infrastructure** in `e2e-tests/`:
   - Self-contained Python test runner (`e2e-tests/runner.py`) using `unittest` or `pytest` with clean CLI args (`--tier=1`, `--all`, `--verbose`), outputting clear reports and exit code 0 on pass, non-zero on failure.
   - HTTP client helper with session handling, JWT auth tokens, WebSockets test harness, and assertion utilities.
3. **Implement Tier 1 (Feature Coverage) Tests**:
   - Write comprehensive tests for Platform Foundation & Auth (Feature 1–7):
     * Health check endpoint returns 200 and healthy DB/Redis
     * Registration of Admin, Proctor, Reviewer, Candidate
     * Authentication with correct credentials returns valid JWT
     * Authentication with bad password returns 401
     * Protected endpoints reject unauthenticated requests (401)
     * Role authorization: Candidate rejected from Admin routes (403)
     * Token refresh exchanges valid refresh token for new access token
   - Write test skeletons and executable tests for subsequent features (Exam CRUD, Question Bank, Taking Portal, Telemetry, Risk, Coding, Interviews, Adaptive IRT, Consent, Appeals, etc.) designed to run against live endpoints as milestones complete.
4. **Implement Tier 2 (Boundary & Corner Cases) Tests**:
   - Expired tokens, malformed JWTs, SQL injection payloads in auth fields, empty strings, oversized inputs, Unicode passwords.
5. **Run the Runner against currently available endpoints (or verify self-contained harness execution)**:
   - Run tests, record full console output and exit code.
6. **Deliverable**:
   - `TEST_INFRA.md` at project root.
   - Complete test suite in `e2e-tests/`.
   - Write your handoff to `d:\vishwa47\v47Studio\ExamSentinel\.agents\test_writer_e2e\handoff.md`.
   - Send completion message to parent orchestrator.

## 2026-09-16T10:51:19Z
You are test_writer_e2e, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\test_writer_e2e\
Read d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md, d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md, and d:\vishwa47\v47Studio\ExamSentinel\.agents\test_writer_e2e\DISPATCH.md.
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All tests must be authentic opaque-box verifications. DO NOT fabricate test results or write dummy assertions that pass vacuously.
Your task: Build the E2E Testing Track infrastructure and test suites:
1. Author d:\vishwa47\v47Studio\ExamSentinel\TEST_INFRA.md following the Project Pattern template covering all 69 features across Tiers 1-4.
2. Build the test runner in e2e-tests/runner.py and test utilities in e2e-tests/.
3. Implement Tier 1 (Feature Coverage) and Tier 2 (Boundary & Corner Cases) test suites in e2e-tests/ covering auth, exams, taking, telemetry, risk engine, coding, interviews, adaptive IRT, compliance, and governance.
4. Run the test runner to verify test harness execution and report pass/fail outputs.
Write your comprehensive handoff report to d:\vishwa47\v47Studio\ExamSentinel\.agents\test_writer_e2e\handoff.md. Update your progress.md regularly. When finished, send a message to the orchestrator.
