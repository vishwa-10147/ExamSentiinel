# Dispatch: Challenger 1 (Milestone 1 — Platform Foundation & Docs)

## Identity
- Role: Adversarial Correctness Challenger
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\`
- Target: Empirically stress-test Milestone 1 work product by `worker_m1`

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (MUST read first)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md`
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\handoff.md`

## Challenge Instructions
1. Write adversarial test cases / scripts to empirically verify that the Milestone 1 authentication and foundation logic is robust:
   - Malformed/tampered JWT tokens (wrong signatures, changed roles in payload, expired timestamps).
   - Refresh token rotation (ensure reuse of old refresh token fails; ensure access token cannot be used to refresh).
   - Role escalation attempts (e.g. candidate user attempting to call admin/proctor/reviewer routes).
   - SQL injection / edge-case inputs in registration and login.
   - Concurrency / race conditions on registration and authentication.
2. Execute the tests against the backend models and API router.
3. Output your formal verdict in your handoff report:
   - `APPROVE` or `REJECT` (with concrete failure evidence).
4. Write your handoff to `d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\handoff.md` and notify the orchestrator.

## 2026-09-16T10:59:08Z
You are challenger_m1_1, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\
Read d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md, d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md, d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m1\handoff.md, and d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\DISPATCH.md.
Empirically stress-test Milestone 1 authentication, token tampering, refresh rotation, role escalation, and edge case inputs.
Write adversarial tests, run them, and record results.
Write your handoff report to d:\vishwa47\v47Studio\ExamSentinel\.agents\challenger_m1_1\handoff.md with your formal verdict (APPROVE or REJECT). Update progress.md. When done, send a message to orchestrator.
