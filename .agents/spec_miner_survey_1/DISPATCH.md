# Survey Task: Core Exam Platform & Documentation (Phases 1–10)

## Objective
Thoroughly inspect and mine all requirements, specifications, schemas, endpoints, algorithms, constraints, and edge cases from `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`.

## Focus Scope
1. Documentation requirements:
   - docs/readme.md
   - docs/plan.md
   - docs/explain.md
   - docs/prompt.md
2. Phases 1–10 (Core Exam Platform):
   - Auth & Roles (JWT, role-based permissions: Admin, Proctor, Candidate, Reviewer)
   - Exam Builder & Question Bank (MCQ, Short Answer, Coding, Rubric, Rich Text, tags, categories)
   - Candidate / Student Exam Portal (Timed sessions, lock-in, state preservation)
   - Browser & Tab Monitoring (Blur, fullscreen change, tab switch, devtools detection)
   - Webcam Face & Phone Detector (Face absence, multiple faces, cell phone detection)
   - Real-time Risk Engine (Weighted risk scores, event triggers, anomaly thresholds)
   - Proctor / Admin Live Dashboard with WebSockets (Real-time live feed, event streams, flags)
   - Review Center with Evidence Viewer (Timeline playback, flag review, audit log)
   - Reporting & Analytics (PDF/CSV export, per-student report cards, aggregate statistics)
   - Deployment & Tooling (Docker Compose, seed demo data script, full integration test harness)

## Deliverables
Write your comprehensive analysis to:
- `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\survey_report.md`
- `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\handoff.md`

Notify the orchestrator via `send_message` when done.

## 2026-09-16T10:46:25Z
You are spec_miner_survey_1, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\
Read d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md and d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\DISPATCH.md.
Mine and extract all requirements, specifications, schemas, endpoints, algorithms, constraints, and edge cases for:
- Documentation in docs/ (docs/readme.md, docs/plan.md, docs/explain.md, docs/prompt.md)
- Phases 1–10: Core Exam Platform (JWT auth, multi-role access, exam builder, question bank, student portal, browser monitoring, webcam face/phone detector, real-time risk engine, admin dashboard with WebSockets, review center with evidence viewer, reporting & CSV export, Docker Compose, seed demo data script, integration tests).
Write your findings to d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\survey_report.md and a self-contained handoff to d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\handoff.md. Update your progress.md as you work.
When finished, send a brief completion message to your parent orchestrator.

