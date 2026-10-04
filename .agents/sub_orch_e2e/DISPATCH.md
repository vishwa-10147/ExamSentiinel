# Dispatch: E2E Testing Orchestrator (Dual Track)

## Identity
- Role: E2E Testing Track Orchestrator
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\sub_orch_e2e\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`
- Parent Conversation ID: `ece9073c-dea0-4960-b4b8-49f426870db1`

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (Authoritative requirements)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md` (Architecture, Feature Inventory, Milestones, Code Layout)

## Objective & Responsibilities
You own the independent, requirement-driven, opaque-box E2E Testing Track.
You do NOT implement product features. You design and implement the automated E2E test suite and test runner.

Your specific tasks:
1. **Initialize TEST_INFRA.md** at project root (`d:\vishwa47\v47Studio\ExamSentinel\TEST_INFRA.md`) following the Project Pattern template:
   - Test Philosophy (opaque-box, requirement-driven, zero internal module coupling).
   - Feature Inventory coverage mapping.
   - Test architecture, execution runner, directory layout (`e2e-tests/`).
   - Methodology: 4 tiers (Tier 1: Feature Coverage >=5 per feature, Tier 2: Boundary & Corner >=5 per feature, Tier 3: Cross-feature pairwise interactions, Tier 4: Real-world application scenarios).
2. **Implement Test Harness & Runner**:
   - Location: `d:\vishwa47\v47Studio\ExamSentinel\e2e-tests\`
   - Executable command to run all tests (e.g. `python -m unittest discover e2e-tests` or `pytest e2e-tests`).
   - Standard exit codes (0 on pass, non-zero on failure).
3. **Author Test Cases Across Tiers 1–4**:
   - Test against public API entry points, CLI scripts, and user flows.
   - Progressive testability: Tier 1 tests can pass against early milestones (e.g. auth, health check, exam CRUD), while later tiers verify full end-to-end flows.
4. **Publish TEST_READY.md** at project root (`d:\vishwa47\v47Studio\ExamSentinel\TEST_READY.md`) once the test suite is complete with coverage summary.

## Execution Method
You are a sub-orchestrator. Decompose your work into sub-milestones (e.g., test infra -> Tier 1/2 tests -> Tier 3/4 tests) or dispatch specialist test writers (`teamwork_preview_test_writer`) and workers via the iteration loop.
Maintain your own `BRIEFING.md` and `progress.md`.
Notify the parent orchestrator via `send_message` with regular progress and when `TEST_READY.md` is published.
