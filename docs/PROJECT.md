# Project: ExamSentinel

ExamSentinel is a production-ready, full-stack AI-powered examination integrity platform adhering to all requirements, specifications, and acceptance criteria in `ORIGINAL_REQUEST.md`.

## Architecture
- **Frontend**: Next.js 14+ (App Router), React, TypeScript, Tailwind CSS, Monaco Editor, Lucide Icons, WebRTC (LiveKit/Daily client), IndexedDB (Dexie/idb).
- **Backend**: FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2.0 (async), Alembic, Uvicorn, PostgreSQL, Redis (pub/sub, event queue, caching).
- **AI & Detectors**: OpenCV, YOLO (Ultralytics / ONNX Runtime), Whisper transcription service, MOSS-style winnowing token similarity, 2PL IRT Bayesian estimation engine.
- **Workers & Sandbox**: Stateless execution runner with resource limits (cgroups/Docker isolation), strictly zero network access (`--net=none`), CPU/memory/time bounds.
- **Observability & Ops**: Structlog structured logging, Prometheus metrics, GitHub Actions CI/CD, k6 load testing scripts, Docker Compose orchestration.

### Data Flow
1. **Candidate Exam Session**: Candidate authenticates via JWT / SSO -> launches timed exam -> state continuously mirrored to local IndexedDB.
2. **Telemetry & Detection**: Browser events (blur, fullscreen, paste, devtools) and webcam frame snapshots stream to backend -> CV models detect face count and phone presence -> events emitted to Redis.
3. **Risk Engine**: Consumes events from Redis -> computes real-time cumulative weighted risk score -> publishes live alerts over WebSockets.
4. **Proctor & Review Center**: Proctors view active session grid with real-time risk badges -> reviewers inspect flagged sessions with timestamped evidence, bounding boxes, and audit logs.
5. **Coding & Interview Tracks**: Code submissions sent to isolated zero-network sandbox -> autograded against visible/hidden tests. Live interviews run via WebRTC with multi-panelist independent scoring; async interviews transcribed with Whisper and indexed for clickable navigation.
6. **Adaptive Testing**: 2PL IRT dynamically selects next question to maximize Fisher Information based on current Bayesian ability estimate $\hat{\theta}$.
7. **Compliance & Hardening**: Strict reviewer separation on student appeals, automated data retention/deletion jobs, versioned consent, and zero auto-blocking on VPN or multi-tab anomalies.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Documentation Suite | `docs/readme.md`, `docs/plan.md`, `docs/explain.md`, `docs/prompt.md` verbatim specs | M1 | Survey 1 |
| 2 | Docker Compose Environment | Multi-service orchestration (Postgres, Redis, Backend, Frontend, Worker) | M1 | Survey 1 |
| 3 | Core Database Schema & Migrations | Alembic migrations, SQLAlchemy models, UUID keys, audit timestamps | M1 | Survey 1 |
| 4 | Authentication & JWT Service | Access/refresh tokens, password hashing (bcrypt), token revocation | M1 | Survey 1 |
| 5 | Role-Based Access Control (RBAC) | Admin, Proctor, Reviewer, Candidate roles and route guards | M1 | Survey 1 |
| 6 | Base API Infrastructure | FastAPI CORS, error handling middleware, structlog request IDs, health checks | M1 | Survey 1 |
| 7 | Base Frontend Shell | Next.js layout, Tailwind design system, auth context, responsive navigation | M1 | Survey 1 |
| 8 | Exam CRUD & Management | Exam configuration, duration, schedule window, late entry tolerance | M2 | Survey 1 |
| 9 | Question Bank Management | Question creation, tags, difficulty, category, rich text, options | M2 | Survey 1 |
| 10 | Standard Question Types | Multiple Choice (single/multi select), Short Answer, Long Essay with rubrics | M2 | Survey 1 |
| 11 | Candidate Enrollment & Scheduling | Candidate assignment, exam access codes, scheduling enforcement | M2 | Survey 1 |
| 12 | Candidate Exam Portal | Exam launch screen, system readiness check, consent agreement | M2 | Survey 1 |
| 13 | Exam Taking Interface | Question navigation palette, flag for review, progress indicator, countdown timer | M2 | Survey 1 |
| 14 | Client-Side Auto-Save | Debounced answer persistence, save status indicators | M2 | Survey 1 |
| 15 | Exam Timer & Auto-Submit | Server-synchronized countdown, grace period, automatic submission on timeout | M2 | Survey 1 |
| 16 | Browser Telemetry Interception | Window blur/focus, fullscreen change, copy/paste/cut attempts, devtools detection | M3 | Survey 1 |
| 17 | Webcam Media Capture | Client-side video stream capture, periodic frame sampling (configurable rate) | M3 | Survey 1 |
| 18 | Computer Vision Detection Service | OpenCV / YOLO inference for face presence, multi-face count, cell phone detection | M3 | Survey 1 |
| 19 | Real-Time Risk Engine | Configurable event weights, score accumulation, Low/Med/High/Critical classification | M3 | Survey 1 |
| 20 | WebSocket Telemetry Stream | Live streaming of proctoring events and risk updates to backend | M3 | Survey 1 |
| 21 | Proctor Live Dashboard | Real-time candidate cards grid, color-coded risk indicators, live event stream | M3 | Survey 1 |
| 22 | Review Center & Evidence Viewer | Flagged session queue, timeline scrubber, snapshot gallery with bounding boxes | M3 | Survey 1 |
| 23 | Human Reviewer Workflow | Dismiss, escalate, record formal findings, immutable reviewer audit log | M3 | Survey 1 |
| 24 | Exam Reporting & CSV Export | Per-student score cards, integrity summary, CSV & PDF export | M3 | Survey 1 |
| 25 | Demo Data Seeding Script | `scripts/seed_demo_data.py` populating users, exams, questions, sessions, events | M3 | Survey 1 |
| 26 | Monaco Code Editor Integration | Multi-language code editor (Python & JavaScript minimum), syntax highlighting | M4 | Survey 2 |
| 27 | Sandboxed Code Execution Worker | Isolated execution runner, resource limits (CPU/RAM/timeout), zero network (`--net=none`) | M4 | Survey 2 |
| 28 | Visible & Hidden Test Case Runner | Iterative feedback on visible tests; final scoring on hidden test cases | M4 | Survey 2 |
| 29 | Autograding Engine | Weighted test case scoring, compilation/runtime error reporting, execution stats | M4 | Survey 2 |
| 30 | Large Paste Detection | Detection of paste events (>10 lines), content diffing, risk signal emission | M4 | Survey 2 |
| 31 | Typing Cadence Analysis | Keystroke interval delta tracking, burstiness & uniformity scoring | M4 | Survey 2 |
| 32 | MOSS-Style Token Similarity | Tokenized k-gram winnowing algorithm, post-exam batch cross-submission comparison | M4 | Survey 2 |
| 33 | Pre-Publish Test Case Validation | Blocking publish validation ensuring test cases pass against reference solution | M4 | Survey 2 |
| 34 | Live WebRTC Video Room | Multi-party video room integration for live interview exams | M4 | Survey 2 |
| 35 | Interview Question Script UI | Synchronized question script view for interviewers alongside candidate feed | M4 | Survey 2 |
| 36 | Rubric-Based Panel Scoring | Criterion-based scoring sliders/rubrics for interviewers | M4 | Survey 2 |
| 37 | Multi-Panelist Independent Scoring | Isolated scoring per panelist to prevent anchoring; consensus score aggregation | M4 | Survey 2 |
| 38 | Async Interview Mode | Timed video/audio response recording for preset interview questions | M4 | Survey 2 |
| 39 | Whisper Transcription Pipeline | Time-aligned speech-to-text transcription of interview recordings | M4 | Survey 2 |
| 40 | Clickable Transcript Highlights | Transcript viewer with clickable timestamps jumping directly to video/audio moments | M4 | Survey 2 |
| 41 | Interview Screen-Share Detection | Detection of unauthorized screen-share events emitting proctoring alerts | M4 | Survey 2 |
| 42 | 2PL IRT Adaptive Engine | Item Response Theory difficulty ($b$) & discrimination ($a$) ability estimation ($\hat{\theta}$) | M5 | Survey 3 |
| 43 | Fisher Information Item Selection | Dynamic next-question selection maximizing information at current ability $\hat{\theta}$ | M5 | Survey 3 |
| 44 | Ability Confidence Intervals | Standard error calculation and reporting ($\hat{\theta} \pm z \cdot \text{SE}$) | M5 | Survey 3 |
| 45 | Diagram Labeling Question Type | Coordinate-based drag-and-drop / click target label placement with tolerance | M5 | Survey 3 |
| 46 | Whiteboard Question Type | Vector canvas with stroke serialization, replay scrubber, and submission | M5 | Survey 3 |
| 47 | Audio Response Question Type | In-browser audio recording, waveform display, playback, and transcript linkage | M5 | Survey 3 |
| 48 | Offline Resilience via IndexedDB | Local state mirroring in IndexedDB, offline input queuing, reconnect replay | M5 | Survey 3 |
| 49 | LMS Connector / LTI 1.3 | LTI 1.3 OIDC authentication, NRPS roster sync, AGS grade pushback | M5 | Survey 3 |
| 50 | Enterprise SSO Integration | SAML2 / OAuth2 / OIDC authentication flow and user auto-provisioning | M5 | Survey 3 |
| 51 | Mobile Exam Mode | Transparent capability disclosure, responsive mobile view, feature restriction tags | M5 | Survey 3 |
| 52 | Versioned Consent Capture | Multi-point consent (webcam, audio, monitoring, retention), versioned audit log | M6 | Survey 3 |
| 53 | Data Retention & Deletion Engine | Per-institution retention policies, scheduled deletion/anonymization background jobs | M6 | Survey 3 |
| 54 | Student Appeals Flow | Formal contestation workflow, strict reviewer role separation, audit trail | M6 | Survey 3 |
| 55 | WCAG 2.1 AA Accessibility | Keyboard navigation, ARIA landmarks, screen reader support, contrast compliance | M6 | Survey 3 |
| 56 | CI/CD GitHub Actions Pipeline | Automated linting, unit testing, integration tests, and build verification | M6 | Survey 3 |
| 57 | Structured Logging & Tracing | Structlog JSON logging, correlation IDs across HTTP requests and WebSockets | M6 | Survey 3 |
| 58 | Prometheus Metrics & Alerting | Metrics exporter (queue depth, WS connections, error rates, latencies) | M6 | Survey 3 |
| 59 | k6 / Locust Load Testing Scripts | Realistic load profiles (ramp-up, exam-start spike, submission burst), breaking point | M6 | Survey 3 |
| 60 | Backup & DR Restore Drill Script | Database snapshot automation, DR restore drill execution script | M6 | Survey 3 |
| 61 | VPN & Proxy Detection | IP intelligence check feeding risk engine without auto-blocking candidates | M6 | Survey 3 |
| 62 | Multi-Device & Multi-Tab Detection | Active session collision detection emitting proctoring alerts without auto-blocking | M6 | Survey 3 |
| 63 | Question-Leak Detection | Text fingerprinting / batch comparison to detect published question leaks | M6 | Survey 3 |
| 64 | Cost & Usage Metering | Tracking sandbox-minutes, video-minutes, transcription-minutes per institution | M6 | Survey 3 |
| 65 | Budget Alerts & Non-Interruptive Throttling | Threshold warnings (80%, 100%), non-interruptive throttling of new launches | M6 | Survey 3 |
| 66 | Notification Service | Email & SMS notification dispatch (invitations, reminders, appeal updates) | M6 | Survey 3 |
| 67 | Calendar Integration | Google Calendar, Outlook Calendar sync, and standard `.ics` file generation | M6 | Survey 3 |
| 68 | Opaque-Box E2E Test Suite (Tiers 1-4) | Systematic requirement-driven verification across all features | M7 | E2E Track |
| 69 | Adversarial Coverage Hardening (Tier 5) | White-box stress tests, edge cases, and forensic integrity audit | M7 | Final Gate |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Platform Foundation, Documentation & Core Services | Features 1–7: `docs/`, Docker Compose, Postgres/Redis schemas, JWT auth, RBAC, FastAPI base, Next.js base | none | DONE |
| M2 | Core Exam Engine & Candidate Portal | Features 8–15: Exam CRUD, Question Bank, MCQ/Short/Essay, Scheduling, Candidate Portal, Taking interface, Auto-save, Auto-submit | M1 | IN_PROGRESS |
| M3 | Proctoring Telemetry, CV & Real-Time Risk Engine | Features 16–25: Browser monitoring, Webcam CV (face & phone), Risk Engine, WebSocket live push, Proctor Dashboard, Review Center, Reporting, Demo seed | M1, M2 | PLANNED |
| M4 | Coding Exam Track & Interview Exam Track | Features 26–41: Monaco Editor, Isolated Sandbox Worker, Autograding, Paste/Cadence/MOSS similarity, Pre-publish validation, WebRTC Live Room, Rubric scoring, Consensus, Async interview with Whisper, Clickable Highlights | M1, M2, M3 | PLANNED |
| M5 | Digital Exam Extensions & Enterprise Integrations | Features 42–51: 2PL IRT Adaptive Engine, Diagram labeling, Whiteboard stroke replay, Audio questions, Offline IndexedDB sync & replay, LTI 1.3 LMS, SAML2 SSO, Mobile mode | M1, M2 | PLANNED |
| M6 | Compliance, Security Hardening, Operations & Governance | Features 52–67: Versioned consent, Data retention & deletion, Student appeals, WCAG 2.1 AA, CI/CD, Structlog, Prometheus metrics, k6 load tests, DR restore, VPN/Multi-tab, Question leak, Cost metering, Notifications, Calendar | M1–M5 | PLANNED |
| M7 | Final Acceptance: 100% E2E Pass & Adversarial Hardening | Features 68–69: Phase 1 (100% E2E test pass across Tiers 1–4) + Phase 2 (Tier 5 adversarial hardening and forensic audit) | M1–M6, TEST_READY.md | PLANNED |

---

## Interface Contracts

### 1. Auth ↔ All Modules
- Header: `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- User Payload: `{ user_id: UUID, email: string, role: "admin" | "proctor" | "reviewer" | "candidate", institution_id: UUID }`
- Exceptions: 401 Unauthorized (invalid/expired), 403 Forbidden (role mismatch).

### 2. Candidate Portal ↔ Exam Session Engine
- `POST /api/exam/sessions/{session_id}/answers`
  - Payload: `{ question_id: UUID, response_data: JSON, client_timestamp: ISO8601, sequence_id: int }`
  - Response: `{ status: "saved", question_id: UUID, server_timestamp: ISO8601 }`
- `POST /api/exam/sessions/{session_id}/submit`
  - Response: `{ status: "submitted", submitted_at: ISO8601, session_id: UUID }`

### 3. Client Telemetry ↔ Risk Engine
- `POST /api/telemetry/events`
  - Payload: `{ session_id: UUID, event_type: string, payload: JSON, timestamp: ISO8601 }`
- `WS /ws/proctor/stream?token=<JWT>`
  - Event Push: `{ session_id: UUID, candidate_name: string, risk_score: float, risk_level: "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", latest_event: { type: string, description: string, timestamp: ISO8601 } }`

### 4. Code Execution ↔ Sandbox Worker
- Job Message: `{ submission_id: UUID, language: "python" | "javascript", source_code: string, stdin: string, time_limit_sec: float, memory_limit_mb: int }`
- Result Message: `{ submission_id: UUID, stdout: string, stderr: string, exit_code: int, wall_time_ms: int, peak_memory_kb: int, status: "SUCCESS" | "TIME_LIMIT_EXCEEDED" | "MEMORY_LIMIT_EXCEEDED" | "RUNTIME_ERROR" }`

### 5. Review Center ↔ Appeals Module
- Appeal creation links to `review_finding_id`, assigning a distinct reviewer (`appeal_reviewer_id != original_reviewer_id`).
- Immutable snapshot of session evidence frozen at time of finding.

---

## Code Layout
```
ExamSentinel/
├── docs/                                # Authoritative documentation
│   ├── readme.md
│   ├── plan.md
│   ├── explain.md
│   └── prompt.md
├── backend/                             # FastAPI Backend Service
│   ├── app/
│   │   ├── api/                         # REST endpoints (auth, exams, questions, coding, interviews, adaptive, appeals, etc.)
│   │   ├── core/                        # Config, security, database session, redis client
│   │   ├── models/                      # SQLAlchemy ORM models
│   │   ├── schemas/                     # Pydantic schemas (requests/responses)
│   │   ├── services/                    # Business logic & engines (risk, CV, IRT, sandbox, retention, appeals)
│   │   └── websocket/                   # WebSocket handlers (proctor stream, interview)
│   ├── alembic/                         # Database migrations
│   ├── tests/                           # Unit and API integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                            # Next.js Frontend Application
│   ├── app/                             # Next.js App Router pages
│   │   ├── auth/                        # Login, SSO callback
│   │   ├── dashboard/                   # Admin & Proctor live dashboard
│   │   ├── review/                      # Review center & evidence viewer
│   │   ├── exam/                        # Candidate portal (standard, coding, interview, adaptive)
│   │   └── appeals/                     # Appeals management portal
│   ├── components/                      # Reusable UI components
│   │   ├── code-editor/                 # Monaco integration
│   │   ├── interview/                   # WebRTC video room & question script
│   │   ├── proctoring/                  # Webcam capture & browser monitors
│   │   └── whiteboard/                  # Vector whiteboard canvas
│   ├── hooks/                           # React hooks (useTelemetry, useOfflineSync, useWebRTC)
│   ├── services/                        # API client services
│   ├── Dockerfile
│   └── package.json
├── execution-workers/                   # Code sandbox runner
│   ├── runner.py                        # Isolated execution daemon
│   ├── Dockerfile                       # Hardened container with no network
│   └── requirements.txt
├── ai/                                  # AI & ML modules
│   ├── proctoring/                      # OpenCV / YOLO detector models
│   ├── code-integrity/                  # MOSS winnowing & typing cadence
│   └── interview-analysis/              # Whisper transcription pipeline
├── scripts/                             # Operational & seed scripts
│   ├── seed_demo_data.py
│   ├── dr_restore_drill.py
│   └── run_tests.py
├── load-testing/                        # k6 & Locust load scripts
│   └── exam_start_spike.js
├── .github/workflows/                   # CI/CD Workflows
│   └── ci.yml
├── e2e-tests/                           # Requirement-driven Opaque-Box E2E Test Suite
│   ├── runner/
│   ├── tier1_feature_coverage/
│   ├── tier2_boundary_corner/
│   ├── tier3_pairwise_interactions/
│   └── tier4_real_world_workloads/
└── docker-compose.yml                   # Full local stack orchestration
```
