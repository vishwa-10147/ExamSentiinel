# Original User Request

## Initial Request — 2026-09-16T10:43:57Z

Build **ExamSentinel**, a production-ready, full-stack AI-powered examination integrity platform. The platform lets institutions run secure online exams — MCQ, short/long answer, live coding challenges, and structured interviews — with intelligent, human-reviewed integrity monitoring. No AI model ever issues a final verdict; every signal it surfaces is routed to a human reviewer.

Working directory: d:\vishwa47\v47Studio\ExamSentinel
Integrity mode: development

## Reference Material

The complete design documentation must be written into the repo at `docs/` as part of the build. The content for these files is provided inline below.

<details>
<summary><strong>docs/readme.md</strong> — Project overview and getting started</summary>

# ExamSentinel

AI-Powered Examination Integrity Platform — now extended with coding exams, interview exams, and adaptive digital exam capabilities.

ExamSentinel lets institutions run secure online exams — MCQ, short/long answer, live coding challenges, and structured interviews — with intelligent, human-reviewed integrity monitoring. No AI model ever issues a final verdict; every signal it surfaces is routed to a human reviewer.

## What's Included

| Track | Capabilities |
|-------|-------------|
| Core Exam Platform | Student portal, exam builder, question bank, browser + webcam proctoring, risk engine, live admin dashboard, review workflow, reporting |
| Coding Exams | In-browser code editor (Monaco), sandboxed multi-language execution, autograding, plagiarism/similarity detection, paste- and typing-pattern integrity signals |
| Interview Exams | Live video interviews (WebRTC), async recorded interviews, panel rubric scoring, auto-transcription, reviewer highlight navigation |
| Digital Exam Extensions | Adaptive (IRT-based) difficulty, offline-resilient exam state, LMS/SSO integration, mobile exam mode, multi-modal question types (diagram, whiteboard, audio) |
| Compliance & Legal | Versioned consent capture, per-institution data retention/deletion, student appeals process, accessibility (WCAG) audits, question-bank IP handling |
| Reliability & Operations | CI/CD gating, observability/alerting, exam-start load testing, backup & disaster recovery |
| Anti-Cheat Hardening | VPN/proxy detection, multi-device/multi-tab detection, interview screen-share detection, question-leak detection |
| Cost & Product Polish | Usage metering and budget alerts, notifications (email/SMS), calendar integration for interviews, pre-publish autograder validation |

## Tech Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Monaco Editor
- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy, WebSockets
- **Database**: PostgreSQL
- **AI / Computer Vision**: OpenCV, YOLO, MediaPipe, NumPy, scikit-learn
- **Code Execution**: Judge0 (or custom gVisor/Firecracker-isolated workers)
- **Video Interviews**: LiveKit / Daily
- **Transcription**: Whisper-class model
- **Infrastructure**: Docker, Docker Compose, Redis

## Getting Started

```bash
git clone <repo-url>
cd exam-sentinel
cp .env.example .env
docker compose up -d
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000
- API Docs (Swagger) → http://localhost:8000/docs

Seed demo data:
```bash
docker compose exec backend python scripts/seed_demo_data.py
```

## Design Principles

1. **No automated guilt.** The platform calculates risk scores and surfaces evidence; only a human reviewer decides on misconduct.
2. **Signals, not verdicts.** Every detector feeds a review queue, never an auto-penalty.
3. **No overclaiming.** The platform never implies monitoring coverage it doesn't actually have.
4. **Privacy by design.** Data minimization, configurable retention, role-based access to evidence, and explicit consent before any capture.
5. **Human review at every consequential step.**

</details>

<details>
<summary><strong>docs/plan.md</strong> — Full build plan (Phases 1–20)</summary>

# ExamSentinel — Extension Build Plan

## 1. Scope

| Track | What it adds |
|-------|-------------|
| Coding Exams | In-browser code editor, sandboxed execution, autograding, code-specific integrity signals |
| Interview Exams | Live video interviews, async recorded interviews, panel scoring, transcription |
| Digital Exams | Adaptive testing, offline resilience, LMS/SSO integration, mobile mode, multi-modal questions |
| Compliance & Legal | Consent management, data retention/deletion, appeals process, accessibility compliance, question-bank IP handling |
| Security, Ops & Reliability | CI/CD, observability, load testing, backup/disaster recovery, exam-environment anti-cheat hardening |
| Cost Governance | Usage metering and budget guardrails for sandbox execution, video minutes, and transcription |
| Product/UX Polish | Notifications, calendar integration, question-leak prevention, autograder correctness validation |

## 2. Repository Structure

```
exam-sentinel/
├── frontend/
│   ├── app/
│   │   ├── exam/
│   │   │   ├── coding/
│   │   │   └── interview/
│   │   └── appeals/
│   ├── components/
│   │   ├── code-editor/
│   │   ├── interview/
│   │   ├── adaptive/
│   │   ├── notifications/
│   │   └── consent/
│   ├── hooks/
│   │   ├── useCodeExecution.ts
│   │   ├── useInterviewRoom.ts
│   │   ├── useOfflineSync.ts
│   │   └── useDeviceFingerprint.ts
│   └── services/
│       ├── codeExecutionService.ts
│       ├── interviewService.ts
│       ├── notificationService.ts
│       └── calendarService.ts
├── backend/
│   └── app/
│       ├── api/
│       │   ├── code_execution.py
│       │   ├── interviews.py
│       │   ├── adaptive.py
│       │   ├── appeals.py
│       │   ├── consent.py
│       │   ├── notifications.py
│       │   └── calendar_sync.py
│       ├── services/
│       │   ├── sandbox_service.py
│       │   ├── plagiarism_service.py
│       │   ├── transcription_service.py
│       │   ├── irt_service.py
│       │   ├── retention_service.py
│       │   ├── device_integrity_service.py
│       │   ├── screen_share_detection_service.py
│       │   ├── cost_metering_service.py
│       │   └── test_case_validation_service.py
│       ├── models/
│       │   ├── code_submission.py
│       │   ├── test_case.py
│       │   ├── interview_session.py
│       │   ├── question_irt_params.py
│       │   ├── consent_record.py
│       │   ├── retention_policy.py
│       │   ├── appeal_case.py
│       │   ├── device_session.py
│       │   └── usage_log.py
│       └── websocket/
│           └── interview_ws.py
├── execution-workers/
├── ai/
│   ├── detectors/
│   ├── code-integrity/
│   └── interview-analysis/
├── connectors/
├── compliance/
│   ├── retention-policies/
│   ├── consent-flows/
│   └── accessibility-audits/
├── .github/workflows/
├── observability/
├── load-testing/
├── infra/
│   ├── backup/
│   └── disaster-recovery/
├── database/
│   └── migrations/
├── docs/
└── docker-compose.yml
```

## 3. New Technology Additions

| Need | Technology |
|------|-----------|
| Code editor | Monaco Editor |
| Code execution sandbox | Judge0, or custom gVisor/Firecracker-isolated Docker workers |
| Job queue | Redis + RQ or Celery |
| Live video interviews | LiveKit or Daily.co |
| Transcription | Whisper (self-hosted) or hosted STT API |
| Adaptive testing | 2-parameter IRT model, server-side |
| Plagiarism/similarity | MOSS-style tokenized diff (code), embedding cosine similarity (text) |
| SSO | SAML2 / OAuth2 via authlib or an identity provider |
| CI/CD | GitHub Actions |
| Observability | Structured logging (structlog), Prometheus + Grafana |
| Load testing | k6 or Locust |
| Backup/DR | Managed Postgres point-in-time recovery + scheduled object-storage snapshots |
| Device/VPN detection | IP intelligence API + browser fingerprinting library |
| Screen-share detection | WebRTC track metadata inspection |
| Notifications | Email (SES/SendGrid) + SMS (Twilio) |
| Calendar integration | Google Calendar / Microsoft Graph API, iCal fallback |

## 4. Database Tables

### Coding
`code_submissions`, `test_cases`, `execution_results`, `language_configs`, `test_case_validation_runs`

### Interviews
`interview_sessions`, `interview_questions`, `interview_recordings`, `interview_scores`, `screen_share_flags`

### Adaptive
`question_irt_params`, `student_ability_est`

### LMS/SSO
`lms_sync_jobs`

### Compliance & Legal
`consent_records`, `data_retention_policies`, `retention_deletion_jobs`, `appeal_cases`, `appeal_actions`, `accessibility_audit_logs`

### Security & Device Integrity
`device_sessions`, `vpn_proxy_flags`, `multi_tab_events`

### Cost Governance
`usage_logs`, `budget_alerts`

### Product/UX
`notification_logs`, `calendar_syncs`, `question_leak_reports`

All follow existing conventions: UUID PKs, created_at/updated_at, FK constraints, indexes on session/student lookups.

## 5. Build Order (Phases 1–20)

### Phases 1–10 — Core Platform

**Phase 1 — Project Setup & Authentication**
- Next.js app with TypeScript, Tailwind, shadcn/ui
- FastAPI backend with SQLAlchemy, Pydantic
- PostgreSQL database with Alembic migrations
- JWT-based auth with role-based access (admin, invigilator, student)
- Docker Compose for local development
- `.env.example` with all required variables

**Phase 2 — Exam Engine**
- Exam CRUD (create, read, update, delete) with exam settings
- Question bank with MCQ, short answer, long answer question types
- Exam scheduling (start time, duration, late entry window)
- Student exam enrollment and access control
- Exam session management (start, submit, auto-submit on timeout)

**Phase 3 — Exam-Taking Experience**
- Student exam portal with question navigation
- Answer submission and auto-save
- Timer with warnings at configurable intervals
- Question flagging for review
- Exam submission confirmation

**Phase 4 — Browser Monitoring**
- Tab focus/blur detection
- Fullscreen enforcement and exit detection
- Copy/paste attempt detection
- Right-click disable
- Browser resize detection
- All events fed to risk engine as signals

**Phase 5 — Webcam Monitoring**
- Pre-exam webcam check and consent
- Periodic snapshot capture
- Face detection (OpenCV/YOLO) — presence, count, position
- Phone/object detection
- Events feed risk engine (FACE_NOT_DETECTED, MULTIPLE_FACES, PHONE_DETECTED)

**Phase 6 — Risk Engine**
- Configurable risk-weight table (event type → weight)
- Real-time risk score calculation per student session
- Risk level thresholds (low/medium/high/critical)
- Risk score history and timeline
- WebSocket push of risk updates to admin dashboard

**Phase 7 — Admin Dashboard**
- Live exam monitoring view — grid of all active student sessions
- Per-student detail view with risk timeline
- Real-time risk indicators with color coding
- Active session counts and statistics
- WebSocket-driven live updates

**Phase 8 — Review Center**
- Review queue of flagged sessions
- Evidence viewer: snapshots, event timeline, risk breakdown
- Reviewer actions: dismiss, escalate, record finding
- Review assignment and status tracking
- Review audit trail

**Phase 9 — Reporting**
- Exam results with score distribution
- Integrity report per exam (flags, reviews, outcomes)
- Student report across exams
- Export to CSV/PDF
- Institution-level analytics

**Phase 10 — Core Polish & Integration Testing**
- End-to-end tests for complete exam flow
- API integration tests
- Seed script for demo data
- Documentation updates
- Performance baseline

### Phases 11–16 — Feature Tracks

**Phase 11 — Code Execution Foundation**
- Monaco editor component with language picker (Python, JavaScript, Java, C++ minimum)
- Code submission API (POST /api/code/submit)
- Redis job queue for execution requests
- Execution worker service with container isolation
- CPU/memory/time limits per execution
- No network access inside sandbox
- Test case runner: visible test cases (student feedback) + hidden test cases (scoring)
- WebSocket streaming of execution results
- TIMEOUT and RUNTIME_ERROR handling

**Phase 12 — Coding Exam Integrity & Autograding**
- Large paste detection (content size + diff against prior editor state)
- Typing cadence analysis (keystroke timing, burstiness score)
- Cross-submission similarity (MOSS-style tokenized structural comparison, batch post-exam)
- Autograding: pass/fail per test case, weighted scoring
- All new signals integrated into risk engine weight table
- Coding exam as a new exam type with feature flag

**Phase 13 — Interview Mode (Live)**
- Interview as a new exam type with scheduling
- WebRTC video room (LiveKit/Daily SDK integration)
- Interview question script UI for interviewer
- Rubric-based scoring panel (per-criterion scores)
- Multi-panelist support with independent scoring
- Panel score aggregation (mean, with per-institution config)
- Session recording with consent capture
- Reconnection handling for dropped connections

**Phase 14 — Interview Mode (Async + Transcription)**
- Async interview: candidate records timed responses to preset questions
- Recording upload and storage
- Whisper-class transcription with time-aligned output
- Transcript viewer with clickable highlights (pauses, filler density, proctoring event overlap)
- Highlights are navigation aids for reviewers, never verdicts

**Phase 15 — Adaptive & Multi-Modal Digital Exams**
- IRT (2-parameter logistic) ability estimation
- Adaptive question selection (maximize information per question)
- Ability estimate + confidence interval reporting
- New question types: diagram labeling (clickable hotspots), whiteboard (stroke-based canvas with replay), audio response (MediaRecorder + optional transcription)
- Each new type has its own answer schema

**Phase 16 — Platform Resilience & Integrations**
- Offline sync: IndexedDB mirroring of exam state, queue-and-replay on reconnect
- NETWORK_DISCONNECT events fed to risk engine
- LMS connector (Moodle/LTI): roster import, grade pushback
- SSO integration (SAML2/OAuth2) alongside existing JWT auth
- Mobile exam mode with honest capability disclosure

### Phases 17–20 — Compliance, Reliability & Hardening

**Phase 17 — Compliance, Consent & Appeals**
- Consent capture at every data collection point (versioned notice text, auditable records)
- Data retention policies per institution per data type
- Scheduled retention_service.py: deletion/anonymization past retention window
- Right-to-deletion requests with audit trail
- Student appeals flow: submit appeal against review decision or autograder result
- Appeal reviewer queue (distinct from original reviewer)
- Appeal audit trail (reviewer identity, timestamp, decision, reasoning)
- WCAG 2.1 AA accessibility audit on code editor and interview UI

**Phase 18 — Reliability & Operations**
- CI/CD: GitHub Actions (lint, type-check, unit tests, integration tests, staged deploy)
- Structured logging (structlog) across backend, execution-workers, video integration
- Metrics and alerting: sandbox queue depth, WebSocket disconnect rate, video-room join failures
- Load testing: k6/Locust scripts simulating exam-start thundering herd (500 students, 60-second window)
- Document breaking point
- Backup & DR: Postgres point-in-time recovery, object-storage snapshots
- Tested restore drill with documented recovery time

**Phase 19 — Anti-Cheat Hardening**
- VPN/proxy detection via IP intelligence API (low-weight risk signal, never auto-block)
- Multi-device/multi-tab detection (concurrent distinct sessions)
- Screen-share detection in interview mode (WebRTC track metadata)
- Question-leak detection: batch comparison of question bank vs public sources and prior appeals
- All signals route to risk engine, never auto-penalize

**Phase 20 — Cost Governance & Product Polish**
- Usage metering: sandbox-minutes, video-minutes, transcription-minutes per institution
- Budget thresholds and alerts (80%, 100%)
- Graduated throttling (never interrupt in-progress exams)
- Notifications: email (SES/SendGrid) + SMS (Twilio) for reminders, confirmations, appeal updates
- Calendar integration: Google Calendar/Microsoft Graph + iCal fallback
- Autograder validation: test_case_validation_service runs all test cases against reference solution before exam publishes; block publish on failure

## 6. Working Method (per phase)

1. Contract first — API schemas and DB migration before UI or business logic
2. Backend before frontend — verify via FastAPI /docs
3. Isolate the risky part — prove integrations standalone before embedding
4. Test failure paths — timeouts, dropped calls, offline sync conflicts
5. Update risk engine weight table in same PR as any new signal
6. Feature flag per exam/institution
7. Compliance and reliability (Phases 17–18) are equal priority to features

## 7. Definition of Done

- **Coding exams**: write/run/submit code in ≥2 languages; autograding scores correctly; paste and similarity signals feed risk engine; test cases pre-validated
- **Interview exams**: live and async both work; transcripts auto-generate; multi-panelist scoring with aggregation; unauthorized screen-share flagged
- **Digital exams**: adaptive exam end-to-end; network drop tolerance; one LMS connector functional; mobile mode with honest capability disclosure
- **Compliance**: consent captured and versioned; retention policies delete on schedule; appeals process with audit trail; accessibility audit run
- **Reliability**: CI/CD gates every deploy; load tests establish capacity; DR restore drilled and timed
- **Cost**: usage metered with budget alerting
- **Product polish**: reminders send reliably; calendar integration works; question-leak detection runs routinely

</details>

<details>
<summary><strong>docs/explain.md</strong> — Design rationale for each subsystem</summary>

# ExamSentinel — Extension Explainer

## 1. Code Execution Sandbox
Student code → Monaco editor → POST /api/code/submit → Redis job queue → isolated worker (gVisor/Firecracker, NOT plain Docker) → results stream via WebSocket. No network access inside sandbox. Hard timeouts and memory caps. Hidden test cases for scoring, visible for feedback. Workers are stateless and idempotent.

## 2. Code-Specific Integrity Signals
- **Large paste detection**: record paste size + diff against prior state
- **Typing cadence**: keystroke timing deltas → burstiness/uniformity score (low-weight signal only)
- **Cross-submission similarity**: MOSS-style tokenized structural comparison, post-exam batch job
- All stay "signals," never verdicts — similar code is legitimate for simple problems; typing varies by person

## 3. Live Interview Mode
WebRTC room (LiveKit/Daily) with interview question script UI, rubric scoring, multi-panelist independent scores, session recording with consent. Use WebRTC-as-a-service — don't build signaling from scratch.

## 4. Async Interview + Transcription
Candidate records timed responses → upload → Whisper transcription → time-aligned transcript with clickable highlights (pauses, filler density, proctoring event overlap). Highlights are navigation aids for reviewers.

## 5. Adaptive Testing (IRT)
2-parameter logistic model. Each question has difficulty (b) and discrimination (a). Student ability (θ) updates after each answer. Next question selected to maximize information. Cold start: seed with instructor estimates, recalibrate from data. Report ability estimates with confidence intervals, not raw scores.

## 6. Offline Resilience
Exam state mirrored to IndexedDB on every change. On disconnect: keep accepting input locally, queue sync payload. On reconnect: replay to backend with last-write-wins per question and audit entry. Never silently drop student work.

## 7. LMS/SSO Integration
LTI for roster import and grade pushback. SAML2/OAuth2 for SSO alongside existing JWT. Use LTI standard rather than bespoke integrations.

## 8. Mobile Exam Mode
Responsive mobile view with reduced monitoring signal set. Pre-exam security check honestly reports what monitoring is possible. Mobile sessions visibly tagged with different monitoring profile.

## 9. Multi-Modal Question Types
Diagram labeling (image + clickable hotspots), whiteboard (stroke-based canvas with replay), audio response (MediaRecorder + transcription). Store strokes as vector data for process replay.

## 10. Consent & Retention
Consent capture at every collection point with versioned notice text. Per-institution retention policies. Scheduled deletion/anonymization. Right-to-deletion with audit trail. Retention must be configurable per institution.

## 11. Appeals Process
Student submits appeal against any decision. Routes to distinct reviewer queue. Full audit trail. Necessary because autograder verdicts and interview panel scores need contestability.

## 12. Accessibility
Monaco editor accessibility mode must be explicitly enabled and tested. Live captioning reuses transcription pipeline. Extended-time accommodations per student. Manual audit with assistive technology required.

## 13. CI/CD, Observability, Load Testing & DR
CI gates every merge. Key alerts: sandbox queue depth, WebSocket disconnect rate, video-room join failures. Load test the thundering herd pattern. Backup only counts as verified after a tested restore drill.

## 14. Anti-Cheat Hardening
VPN/proxy: low-weight contextual signal, never auto-block. Multi-device/multi-tab: stronger signal than VPN. Screen-share detection: WebRTC track metadata. Question-leak detection: batch comparison job. All signals → reviewer, never auto-penalty.

## 15. Cost Governance
Meter sandbox-minutes, video-minutes, transcription-minutes per institution. Budget alerts at thresholds. Graduated throttling — never interrupt in-progress exams.

## 16. Notifications, Calendar, Autograder Validation
Transactional email + SMS. Calendar integration for interview scheduling. Autograder validation: run test cases against reference solution before publish; block publish on failure.

</details>

<details>
<summary><strong>docs/prompt.md</strong> — AI agent operating instructions</summary>

# ExamSentinel Extension — AI Coding Agent Build Prompt

## Role
Implementing production-grade features on an existing platform. Read plan.md and explain.md fully before writing code.

## Ground Rules
1. Work one phase at a time (Phase 1 → 20). Don't start next phase until current demo checkpoint met.
2. Never guess at security-sensitive design (isolation, sandbox, auth/SSO).
3. Every new signal must reach the risk engine in the same change.
4. Never let AI output become a verdict — always human-reviewer-facing evidence.
5. Contract-first: API schemas + DB migration before UI/logic.
6. Backend before frontend, verified via /docs.
7. Feature-flag everything per exam/institution.
8. Test failure paths: timeouts, dropped calls, offline conflicts, cold-start IRT.

## Non-Negotiable Constraints
- No automated "cheating" verdicts
- No inference from demographics, appearance, disability, or emotion
- No plaintext secrets, no client-side-only auth checks
- No silent overclaiming of monitoring capability
- No student work lost on disconnect
- No untracked data collection
- No silent deletion or silent retention
- No decision without an appeal path
- No VPN/device/multi-tab signal may auto-block a student
- No budget enforcement may interrupt an exam in progress
- No production deploy without CI passing
- No claim of DR readiness without a tested restore

</details>

## Requirements

### R1. Core Exam Platform (Phases 1–10)
Build a complete exam platform with: JWT-based multi-role authentication (admin, invigilator, student); exam builder with question bank (MCQ, short answer, long answer); scheduled exam sessions with auto-submit; browser monitoring (tab focus, fullscreen, copy/paste detection); webcam monitoring (face detection, phone detection via OpenCV/YOLO); a configurable risk engine that calculates real-time risk scores from all signals; a live admin dashboard with WebSocket-driven updates; a review center where human reviewers evaluate flagged sessions with full evidence; and reporting with export capabilities. All in Docker Compose with PostgreSQL, Redis, seed demo data script.

### R2. Coding Exam Track (Phases 11–12)
Add in-browser coding exams with: Monaco editor supporting ≥2 languages; sandboxed code execution via Judge0 or isolated workers (no network access, hard resource limits); visible + hidden test cases; autograding with weighted scoring; code-specific integrity signals (large paste detection, typing cadence analysis, cross-submission MOSS-style similarity) all feeding the risk engine as human-reviewable signals; and pre-publish test case validation against reference solutions.

### R3. Interview Exam Track (Phases 13–14)
Add live and async interview capabilities: WebRTC video rooms via LiveKit/Daily SDK; interview question scripts with rubric-based scoring; multi-panelist independent scoring with aggregated views; session recording with consent; async mode with timed recorded responses; Whisper-class transcription with time-aligned output; transcript viewer with clickable highlights for reviewers; reconnection handling.

### R4. Digital Exam Extensions (Phases 15–16)
Add adaptive testing (2PL IRT model with ability estimation and adaptive question selection); multi-modal question types (diagram labeling, whiteboard with stroke replay, audio response); offline resilience (IndexedDB sync with queue-and-replay); LMS integration via LTI (roster import, grade pushback); SSO (SAML2/OAuth2); and mobile exam mode with honest capability disclosure.

### R5. Compliance & Legal (Phase 17)
Build versioned consent capture at every data collection point; per-institution configurable data retention policies with scheduled deletion/anonymization; right-to-deletion requests with audit trail; student appeals flow (submit, review, resolve with full audit trail); and WCAG 2.1 AA accessibility audit specifically on code editor and interview UI.

### R6. Reliability & Operations (Phase 18)
Implement CI/CD via GitHub Actions (lint, type-check, test, staged deploy); structured logging and metrics with alerting on critical signals (sandbox queue depth, WebSocket disconnects, video join failures); load testing scripts simulating exam-start thundering herd with documented breaking point; backup and disaster recovery with a tested restore drill.

### R7. Security Hardening (Phase 19)
Add VPN/proxy detection (IP intelligence, low-weight risk signal), multi-device/multi-tab detection, interview screen-share detection (WebRTC track metadata), and question-leak detection (batch comparison). All signals route to risk engine as reviewer-visible flags, never auto-blocking students.

### R8. Cost Governance & Polish (Phase 20)
Build usage metering per institution (sandbox-minutes, video-minutes, transcription-minutes) with budget alerts and graduated throttling (never interrupt in-progress exams); notification delivery (email/SMS); calendar integration for interview scheduling (Google Calendar/Outlook + iCal fallback); autograder validation that blocks exam publish if test cases fail against reference solution.

## Acceptance Criteria

### Platform Foundation
- [ ] `docker compose up -d` starts the full stack (frontend, backend, database, Redis) without errors
- [ ] `docker compose exec backend python scripts/seed_demo_data.py` seeds a demo institution with admins, invigilators, students, sample exams, and simulated monitoring events
- [ ] A student can log in, start a scheduled exam, answer questions (MCQ, short, long answer), and submit — with auto-submit on timeout
- [ ] Browser monitoring events (tab blur, fullscreen exit, paste attempt) are captured and visible in the risk engine
- [ ] Webcam monitoring detects face presence/absence and phone presence, feeding the risk engine
- [ ] The risk engine produces real-time risk scores with configurable weights, pushed via WebSocket to the admin dashboard
- [ ] An admin sees a live grid of all active student sessions with risk indicators updating in real time
- [ ] A reviewer can open a flagged session, view evidence (snapshots, event timeline, risk breakdown), and record a finding
- [ ] Exam results can be exported to CSV with integrity reports

### Coding Exams
- [ ] A student can write, run, and submit code in at least Python and JavaScript using the in-browser Monaco editor
- [ ] Code executes in a sandboxed environment with no network access and hard CPU/memory/time limits
- [ ] Visible test cases show pass/fail during the exam; hidden test cases are used for final scoring
- [ ] Autograding produces correct weighted scores based on test case results
- [ ] Large paste events (>10 lines) are detected and appear as risk signals in the review center
- [ ] Cross-submission similarity analysis runs as a post-exam batch job and flags high-similarity pairs for reviewer attention
- [ ] A coding exam cannot be published if any test case fails against the provided reference solution

### Interview Exams
- [ ] A live video interview can be started, with both interviewer and candidate joining a WebRTC room
- [ ] The interviewer sees the question script and rubric scoring panel alongside the video feed
- [ ] Multiple panelists can score the same session independently; an aggregated view shows all scores
- [ ] An async interview allows a candidate to record timed responses to preset questions
- [ ] Recordings are automatically transcribed with time-aligned output
- [ ] Reviewers can navigate to specific moments via clickable transcript highlights
- [ ] Consent is captured before any recording begins

### Adaptive & Digital Extensions
- [ ] An adaptive exam adjusts question difficulty based on student performance using the IRT model
- [ ] A student's ability estimate and confidence interval are reported alongside scores
- [ ] Diagram labeling, whiteboard (with stroke replay), and audio response question types function correctly
- [ ] If a student's network drops mid-exam, answers are preserved locally and synced on reconnect without data loss
- [ ] At least one LMS connector (Moodle/LTI) successfully imports a roster and pushes grades back
- [ ] Mobile exam mode explicitly discloses its reduced monitoring capability to the student and in session metadata

### Compliance
- [ ] Consent records are created with versioned notice text at every data collection point (webcam, recording, keystroke logging)
- [ ] Data past its retention window is actually deleted or anonymized by the scheduled retention job
- [ ] A student can submit an appeal against a review decision or autograder result; a different reviewer can review and resolve it with a full audit trail
- [ ] An accessibility audit has been run on the code editor and interview UI, with results logged

### Reliability
- [ ] A merge to main cannot proceed without all CI checks passing (lint, type-check, unit tests, integration tests)
- [ ] Structured logs and metrics are emitted; alerts fire when sandbox queue depth or WebSocket disconnect rate exceeds thresholds
- [ ] A load test simulating 500 concurrent exam starts produces a documented report of the system's breaking point
- [ ] A backup restore drill has been performed and the recovery time documented

### Security
- [ ] A VPN connection generates a low-weight risk signal visible to reviewers, without blocking the student
- [ ] Concurrent sessions from the same credential on different devices are detected and flagged
- [ ] An unauthorized screen-share during an interview generates a reviewer-visible flag
- [ ] Question-leak detection runs as a batch job comparing question content against prior submissions

### Cost & Polish
- [ ] Usage (sandbox-minutes, video-minutes, transcription-minutes) is tracked per institution
- [ ] Budget alerts fire at configured thresholds; in-progress exams are never interrupted by budget enforcement
- [ ] Exam reminders and interview confirmations are sent via email with delivery status logged
- [ ] Interview scheduling integrates with at least one calendar provider (Google Calendar or Outlook) and produces iCal files as fallback
- [ ] No exam type can be published with unvalidated autograder test cases

## Follow-up — 2026-09-16T16:30:08Z

Continue building **ExamSentinel** from where the previous team left off. The project is at `d:\vishwa47\v47Studio\ExamSentinel`.

Working directory: d:\vishwa47\v47Studio\ExamSentinel
Integrity mode: development

## Current State — What Has Been Built

Milestone 1 (Project Setup & Auth) is COMPLETE and passed adversarial review:
- Docker Compose (PostgreSQL, Redis, backend, frontend, worker)
- FastAPI backend with SQLAlchemy, Pydantic, Alembic migrations
- JWT auth with RBAC (admin, invigilator, student), refresh tokens, audit logging
- Next.js frontend with TypeScript, Tailwind CSS
- Execution workers scaffolded with Redis job runner
- 63 tests passing (unit, RBAC, adversarial, remediation)
- All 6 security defects (role escalation, token replay, registration concurrency, etc.) fixed

Milestone 2 (Exam Engine & Portal) implementation is COMPLETE but was in review when interrupted:
- Database models: exam.py, question.py, session.py, response.py
- API routes: exams.py (503 lines), questions.py, sessions.py (487 lines)
- Frontend: QuestionPalette, TimerBanner, QuestionCard, AutoSaveIndicator, SubmitModal
- test_exam_engine.py (723 lines), 71 tests passing

## What Still Needs to Be Built

Pick up from Milestone 2 review and continue through all remaining milestones:

**Milestone 3 — Browser & Webcam Monitoring + Risk Engine**
- Tab focus/blur, fullscreen, copy/paste, right-click, resize detection
- Webcam: face detection (OpenCV/YOLO), phone detection
- Risk engine: configurable weight table, real-time scoring, WebSocket push
- Risk level thresholds (low/medium/high/critical)

**Milestone 4 — Admin Dashboard + Review Center + Reporting**
- Live monitoring grid of active sessions with WebSocket updates
- Per-student detail with risk timeline
- Review queue, evidence viewer, reviewer actions, audit trail
- Reporting: score distribution, integrity reports, CSV/PDF export

**Milestone 5 — Coding Exams (Phases 11-12)**
- Monaco editor with language picker (Python, JS, Java, C++)
- Sandboxed code execution (Judge0 or isolated workers, no network)
- Visible + hidden test cases, autograding
- Integrity signals: large paste detection, typing cadence, MOSS-style similarity
- Pre-publish test case validation

**Milestone 6 — Interview Exams (Phases 13-14)**
- Live WebRTC video rooms (LiveKit/Daily SDK)
- Interview scripts, rubric scoring, multi-panelist
- Async interviews with timed recordings
- Whisper transcription, transcript viewer with highlights
- Consent captured before recording

**Milestone 7 — Digital Extensions, Compliance, Reliability, Security, Polish (Phases 15-20)**
- Adaptive testing (IRT 2PL)
- Multi-modal questions (diagram, whiteboard, audio)
- Offline resilience (IndexedDB sync)
- LMS/SSO integration
- Consent management, retention policies, appeals
- CI/CD, observability, load testing, DR
- VPN/device/screen-share detection
- Cost metering, notifications, calendar integration
- Autograder validation

## Non-Negotiable Constraints
- No automated "cheating" verdicts — every signal is reviewer-facing evidence
- No inference from demographics, appearance, disability, or emotion
- No plaintext secrets, no client-side-only auth checks
- No silent overclaiming of monitoring capability
- No student work lost on disconnect
- No untracked data collection
- No decision without an appeal path
- No VPN/device/multi-tab signal may auto-block a student
- No budget enforcement may interrupt an exam in progress

## Acceptance Criteria

### Platform Foundation
- [ ] `docker compose up -d` starts the full stack without errors
- [ ] Seed script creates demo data
- [ ] Student can take a full exam with auto-submit
- [ ] Browser/webcam monitoring feeds risk engine
- [ ] Admin sees live dashboard with WebSocket updates
- [ ] Reviewer can evaluate flagged sessions
- [ ] Results export to CSV

### Coding Exams
- [ ] Monaco editor with Python + JavaScript minimum
- [ ] Sandboxed execution with no network, hard limits
- [ ] Visible + hidden test cases, autograding
- [ ] Large paste detection + similarity analysis as risk signals
- [ ] Pre-publish test case validation blocks publish on failure

### Interview Exams
- [ ] Live WebRTC video room
- [ ] Rubric scoring with multi-panelist support
- [ ] Async interview with timed recordings
- [ ] Auto-transcription with clickable highlights
- [ ] Consent captured before recording

### Digital Extensions
- [ ] Adaptive exam with IRT model
- [ ] Diagram, whiteboard, audio question types
- [ ] Offline sync preserves answers on disconnect
- [ ] LMS connector imports roster + pushes grades
- [ ] Mobile mode discloses reduced monitoring

### Compliance
- [ ] Versioned consent at every collection point
- [ ] Retention policies actually delete/anonymize on schedule
- [ ] Appeals flow with full audit trail
- [ ] Accessibility audit on code editor + interview UI

### Reliability
- [ ] CI/CD gates every merge
- [ ] Alerting on sandbox queue depth, WebSocket disconnects
- [ ] Load test documents breaking point
- [ ] DR restore drill performed and timed

### Security
- [ ] VPN detection as low-weight signal (no auto-block)
- [ ] Multi-device/multi-tab detection
- [ ] Screen-share detection in interviews
- [ ] Question-leak batch detection

### Cost & Polish
- [ ] Usage metering per institution
- [ ] Budget alerts (never interrupt in-progress exams)
- [ ] Email notifications with delivery logging
- [ ] Calendar integration + iCal fallback
- [ ] Autograder validation blocks unvalidated test cases

