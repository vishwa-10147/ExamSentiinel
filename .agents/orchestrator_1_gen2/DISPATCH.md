# Dispatch: Project Orchestrator (Generation 2)

## Identity
- Role: Project Orchestrator (Generation 2 Successor)
- Archetype: orchestrator
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1_gen2\`
- Predecessor Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1\`
- Parent Conversation ID: `dd268f5f-3324-4370-a35f-670772f14753`

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (Authoritative user specification)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md` (Master architecture, Feature Inventory 1–69, Milestones)
3. `d:\vishwa47\v47Studio\ExamSentinel\TEST_INFRA.md` (E2E testing architecture)
4. `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1\handoff.md` (Generation 1 State Dump & Action Plan)
5. `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1\BRIEFING.md`
6. `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1\progress.md`
7. `d:\vishwa47\v47Studio\ExamSentinel\.agents\reviewer_m2\handoff.md` (Milestone 2 Defect Report)

## Immediate Instructions
1. Establish your working environment in `d:\vishwa47\v47Studio\ExamSentinel\.agents\orchestrator_1_gen2\` (BRIEFING.md, progress.md).
2. Start your heartbeat cron: `schedule(CronExpression="*/10 * * * *")`.
3. Your parent is `dd268f5f-3324-4370-a35f-670772f14753`. All escalation, reporting, and messages to your caller MUST be sent to this ID using `send_message`.
4. Immediate priority:
   - Remediate and gate Milestone 2 (Core Exam Engine & Candidate Portal): dispatch worker to fix the 3 issues identified in `reviewer_m2/handoff.md` (late entry reconnect lockout, auto-submit on timeout 400 rejection, alien question validation).
   - Re-verify Milestone 2 via reviewer and auditor; mark M2 DONE in `PROJECT.md`.
5. Subsequent execution:
   - Execute Milestone 3 (Proctoring Telemetry, CV & Real-Time Risk Engine).
   - Execute Milestone 4 (Coding & Interview Tracks).
   - Execute Milestone 5 (Digital Extensions, IRT, Offline Sync).
   - Execute Milestone 6 (Compliance, Security, Operations, Cost Governance).
   - Execute Milestone 7 (100% E2E test suite pass across Tiers 1–4, Tier 5 adversarial hardening, final forensic audit).
6. Successor Protocol:
   - If your spawn count reaches 16, self-succeed to Gen 3 following the same protocol.
