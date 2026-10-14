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
