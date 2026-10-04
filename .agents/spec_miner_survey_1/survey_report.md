# ExamSentinel Survey & Specification Report: Docs & Phases 1–10 (Core Exam Platform)

**Author:** `spec_miner_survey_1`  
**Date:** 2026-09-16  
**Source Document:** `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`  
**Scope:** Design Documentation (`docs/readme.md`, `docs/plan.md`, `docs/explain.md`, `docs/prompt.md`) and Core Exam Platform (Phases 1–10).

---

## 1. Executive Summary

ExamSentinel is an AI-powered examination integrity platform built on the fundamental principle that **no AI model ever issues a final verdict; every signal it surfaces is routed to a human reviewer**. The platform provides secure online exams (MCQ, short answer, long answer, coding, and interviews) combined with real-time multi-modal monitoring (browser telemetry, webcam computer vision, and behavior anomaly detection).

This specification mining report covers:
1. **Core Documentation Specifications**: Exact contents, structure, and operational constraints for `docs/readme.md`, `docs/plan.md`, `docs/explain.md`, and `docs/prompt.md`.
2. **Phases 1–10 (Core Exam Platform)**:
   - Phase 1: Project Setup, Docker Compose, JWT Auth & Multi-Role RBAC (Admin, Invigilator, Student, Reviewer).
   - Phase 2: Exam Engine, Scheduling, Late Entry Windows, Question Bank (MCQ, Short, Long), Enrollment & Session Management.
   - Phase 3: Student Exam Experience, Question Navigation, Debounced Auto-Save, Timers & Warnings, Question Flagging, Auto-Submit.
   - Phase 4: Browser & Tab Monitoring (Focus/Blur, Fullscreen enforcement/exit, Copy/Paste/Cut prevention/logging, Right-click disable, Resize, DevTools).
   - Phase 5: Webcam Monitoring & Computer Vision (Pre-exam check/consent, Periodic snapshots, Face presence/absence, Multiple faces, Phone detection via OpenCV/YOLO).
   - Phase 6: Real-time Risk Engine (Configurable event weights, Score calculation, Risk levels Low/Medium/High/Critical, Score history, WebSocket push).
   - Phase 7: Admin / Invigilator Live Dashboard (Live session grid, color-coded badges, per-student detail view, aggregate stats, WebSockets).
   - Phase 8: Review Center & Evidence Viewer (Flagged session queue, Snapshot gallery with bounding boxes, Event timeline playback, Reviewer actions: dismiss/escalate/record finding, Audit trail).
   - Phase 9: Reporting & Analytics (Score distribution, Integrity reports, Student profiles, CSV & PDF export, Institution analytics).
   - Phase 10: Core Polish, Demo Data Seeding (`scripts/seed_demo_data.py`), and Integration Test Suite.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Documentation | `docs/readme.md` | Project overview, 8-track capability table, tech stack, getting started commands, and 5 non-negotiable design principles. | Repository context and spec metadata. | Complete Markdown file at `docs/readme.md`. | N/A (Static file). | ORIGINAL_REQUEST.md lines 15–73 |
| 2 | Documentation | `docs/plan.md` | Complete 20-phase build plan detailing repository layout, new technologies, DB tables, phase breakdown, working method, and Definition of Done. | Phase specifications and tech stack requirements. | Complete Markdown file at `docs/plan.md`. | N/A (Static file). | ORIGINAL_REQUEST.md lines 76–405 |
| 3 | Documentation | `docs/explain.md` | Architectural deep-dive and rationale across 16 subsystems explaining why each component is built with specific isolation, integrity, and privacy principles. | Architecture rationale and system design. | Complete Markdown file at `docs/explain.md`. | N/A (Static file). | ORIGINAL_REQUEST.md lines 408–463 |
| 4 | Documentation | `docs/prompt.md` | AI coding agent operating instructions detailing the 8 ground rules and 12 non-negotiable ethical/system constraints. | Operational guidelines and constraints. | Complete Markdown file at `docs/prompt.md`. | N/A (Static file). | ORIGINAL_REQUEST.md lines 466–497 |
| 5 | Phase 1: Auth & RBAC | User Registration & Login | Secure registration and login issuing signed JWT access and refresh tokens. Password hashing via bcrypt/argon2. | Email, password, full name, role (`admin`, `invigilator`, `student`, `reviewer`). | JWT access token, refresh token, user profile object. | 400 Bad Request on duplicate email; 401 Unauthorized on invalid credentials; 422 on malformed input. | ORIGINAL_REQUEST.md lines 225–232, 502, 528 |
| 6 | Phase 1: Auth & RBAC | Role-Based Access Control | Enforces fine-grained permission barriers across endpoints based on user role (`admin`, `invigilator`, `student`, `reviewer`). | Request headers with `Bearer <JWT>`. | Authorized execution or 403 Forbidden. | 401 on missing/expired token; 403 Forbidden on insufficient role. | ORIGINAL_REQUEST.md lines 229, 502 |
| 7 | Phase 1: Auth & RBAC | User Profile & Session Introspection | Endpoint `/api/auth/me` to retrieve current authenticated user info and institution affiliation. | JWT Bearer token. | User model (id, email, name, role, institution_id, created_at). | 401 Unauthorized if token invalid or user inactive. | ORIGINAL_REQUEST.md lines 229, 502 |
| 8 | Phase 1: Infrastructure | Docker Compose Stack | Multi-container setup orchestrating Next.js frontend, FastAPI backend, PostgreSQL 15+, and Redis 7+. | `docker compose up -d` | Healthy running containers on ports 3000, 8000, 5432, 6379. | Exit on missing port binding or failed dependency healthcheck. | ORIGINAL_REQUEST.md lines 49–59, 230, 528 |
| 9 | Phase 2: Exam Engine | Exam CRUD & Configuration | Admin/Invigilator creates, edits, archives, or deletes exams with title, description, duration, scheduling, and proctoring settings. | Exam payload (title, duration_minutes, start_time, end_time, late_entry_window, monitoring flags). | Exam entity with UUID, timestamps, status. | 400 on invalid time ranges (e.g., end_time <= start_time); 404 on not found. | ORIGINAL_REQUEST.md lines 234–239, 502 |
| 10 | Phase 2: Exam Engine | Question Bank Management | Create and curate questions across categories, tags, points, and types (MCQ, Short Answer, Long Answer). | Question payload (prompt, type, points, options/rubric, category, tags). | Stored Question object with UUID. | 400 on invalid question format (e.g. MCQ without correct option); 404 on not found. | ORIGINAL_REQUEST.md lines 235, 502 |
| 11 | Phase 2: Exam Engine | Exam Question Assignment | Associate questions from the question bank to specific exams with order indexing and custom point overrides. | Exam ID, Question IDs, order indices, points overrides. | Exam-Question mapping records. | 400 on duplicate question in exam; 404 if exam or question missing. | ORIGINAL_REQUEST.md lines 234–235 |
| 12 | Phase 2: Exam Engine | Student Enrollment & Access Control | Enroll students into scheduled exams and restrict access strictly to enrolled candidates during scheduled windows. | Exam ID, Student ID (or batch user IDs). | Enrollment record (`ENROLLED`, `IN_PROGRESS`, `COMPLETED`). | 409 Conflict if already enrolled; 403 Forbidden if student accesses non-enrolled exam. | ORIGINAL_REQUEST.md lines 237, 502 |
| 13 | Phase 2: Exam Engine | Scheduled Windows & Late Entry | Restrict exam start to designated time window; allow entry only within `late_entry_window_minutes`. | Session start request at current server time. | Allowed session creation or error. | 403 Forbidden with `EXAM_NOT_STARTED` or `LATE_ENTRY_WINDOW_EXPIRED`. | ORIGINAL_REQUEST.md lines 236, 502 |
| 14 | Phase 2: Exam Engine | Exam Session Lifecycle | Manage lifecycle transitions: `NOT_STARTED` -> `IN_PROGRESS` -> `SUBMITTED` / `AUTO_SUBMITTED` / `TERMINATED`. | Session start/submit commands. | Updated session object with state, timestamps, time remaining. | 400 on invalid state transition (e.g. submitting an already completed exam). | ORIGINAL_REQUEST.md lines 238–239, 530 |
| 15 | Phase 3: Student Portal | Pre-Exam Verification & System Check | Step-by-step checklist ensuring browser compatibility, camera access, and explicit informed consent acceptance. | Device check signals, candidate consent button click. | Verification status passed; unlocks "Start Exam" button. | Blocks start if camera permission denied or consent refused. | ORIGINAL_REQUEST.md lines 256, 554, 565 |
| 16 | Phase 3: Student Portal | Question Palette & Navigation | Client UI displaying list of all questions with real-time indicators: Unanswered (gray), Answered (green), Flagged (yellow). | Navigation click, current question index. | Renders active question view. | Bounds check prevents out-of-range question index. | ORIGINAL_REQUEST.md lines 241, 530 |
| 17 | Phase 3: Student Portal | Debounced Auto-Save Engine | Automatically saves candidate's answer input to backend after typing pauses or option selection, showing visual status. | Answer payload (session_id, question_id, response_data). | 200 OK with timestamp confirmation; updates UI status to "Saved". | Queues locally on network glitch, retries on reconnect; no data lost. | ORIGINAL_REQUEST.md lines 242, 431, 530 |
| 18 | Phase 3: Student Portal | Authoritative Exam Timer | Server-synchronized countdown timer with configurable warnings at 15m, 5m, and 1m remaining. | Current server time vs session end time. | Countdown display (HH:MM:SS), warning dialogs/banners. | Blocks client-side clock tampering; relies on backend timestamps. | ORIGINAL_REQUEST.md lines 243, 530 |
| 19 | Phase 3: Student Portal | Question Review Flagging | Candidate can toggle a "Flag for review" marker on any question to return to it later before submission. | Question ID, flag toggle boolean. | Answer record updated with `is_flagged=true/false`. | 404 if question or session invalid. | ORIGINAL_REQUEST.md lines 244 |
| 20 | Phase 3: Student Portal | Exam Submission & Confirmation | Displays summary of answered/unanswered/flagged questions; requires explicit confirmation before final lock. | Submit button click, confirmation modal accept. | Session status updated to `SUBMITTED`, locks exam inputs, redirects to completion screen. | 400 if session is already completed or expired. | ORIGINAL_REQUEST.md lines 245, 530 |
| 21 | Phase 3: Student Portal | Auto-Submit on Timeout | Server-side and client-side auto-submission triggered precisely when allotted exam time expires. | Timer expiry trigger or background expiration worker. | Session status transitioned to `AUTO_SUBMITTED`, locks exam. | Rejects subsequent answer save requests with 403 Forbidden. | ORIGINAL_REQUEST.md lines 238, 502, 530 |
| 22 | Phase 4: Browser Proctoring | Tab Focus / Blur Detection | Detects when candidate switches tabs or minimizes browser window using `window.onblur` and `document.visibilitychange`. | Client window blur / visibility hidden events. | Emits `TAB_BLUR` / `TAB_FOCUS` events to backend with duration. | Silently fails if telemetry blocked, but logged as missing heartbeat. | ORIGINAL_REQUEST.md lines 248, 502, 531 |
| 23 | Phase 4: Browser Proctoring | Fullscreen Enforcement & Exit | Prompts candidate into fullscreen mode on exam start; detects when fullscreen is exited via `fullscreenchange`. | `document.fullscreenchange` event. | Emits `FULLSCREEN_EXIT` event to backend; displays warning banner to re-enter fullscreen. | Repeated exits escalate risk score. | ORIGINAL_REQUEST.md lines 249, 531 |
| 24 | Phase 4: Browser Proctoring | Copy / Paste / Cut Prevention & Logging | Prevents clipboard copy/cut/paste within exam interface and logs attempts as monitoring signals. | `oncopy`, `onpaste`, `oncut` event interceptors. | `event.preventDefault()`, emits `COPY_ATTEMPT` / `PASTE_ATTEMPT` to backend. | Does not crash page; logs text length and metadata. | ORIGINAL_REQUEST.md lines 250, 502, 531 |
| 25 | Phase 4: Browser Proctoring | Right-Click / Context Menu Disable | Disables browser right-click context menu to prevent inspecting elements or copying text. | `contextmenu` mouse event. | `event.preventDefault()`, emits `RIGHT_CLICK_ATTEMPT`. | Native context menu suppressed cleanly. | ORIGINAL_REQUEST.md lines 251 |
| 26 | Phase 4: Browser Proctoring | Window Resize & DevTools Detection | Detects unexpected window dimension changes or developer tools open events. | `window.onresize`, viewport difference checks. | Emits `WINDOW_RESIZE` or `DEVTOOLS_OPEN` event to backend. | Logged to event stream with new window dimensions. | ORIGINAL_REQUEST.md lines 252, 531 |
| 27 | Phase 5: Webcam Proctoring | Pre-Exam Webcam Check & Consent | Interactive camera preview allowing student to center face and capture consent record with timestamp. | Webcam video stream access, candidate confirmation. | Video stream active, consent record logged. | Halts progression if camera permission denied or camera hardware missing. | ORIGINAL_REQUEST.md lines 256, 554, 565 |
| 28 | Phase 5: Webcam Proctoring | Periodic Snapshot Capture | Client captures webcam video frame every $N$ seconds (e.g., 5-10s) and uploads compressed snapshot to backend. | HTML5 canvas capture from video element. | Multipart image upload to `POST /api/sessions/{session_id}/snapshots`. | Retry on transient network failure; log snapshot failure if persistent. | ORIGINAL_REQUEST.md lines 257, 502 |
| 29 | Phase 5: Webcam Proctoring | Face Presence & Absence Detection | Computer vision model (OpenCV / MediaPipe / Haar / YOLO) inspects snapshot for face presence. | Uploaded image frame. | Detected face count (0, 1, 2+). Emits `FACE_NOT_DETECTED` if count == 0. | Graceful fallback if image corrupted (logs `IMAGE_PROCESSING_ERROR`). | ORIGINAL_REQUEST.md lines 258, 260, 502, 532 |
| 30 | Phase 5: Webcam Proctoring | Multiple Faces Detection | Detects if more than one person is visible in the camera frame. | Uploaded image frame. | Face count >= 2. Emits `MULTIPLE_FACES` event with bounding boxes. | Non-blocking signal; flagged for human review. | ORIGINAL_REQUEST.md lines 258, 260, 532 |
| 31 | Phase 5: Webcam Proctoring | Phone & Object Detection | YOLO object detection model inspects snapshot for cell phones or unauthorized mobile devices. | Uploaded image frame. | Bounding box coordinates, confidence score, emits `PHONE_DETECTED`. | False positives are routed to human reviewer; never auto-penalized. | ORIGINAL_REQUEST.md lines 259, 260, 502, 532 |
| 32 | Phase 6: Risk Engine | Configurable Risk-Weight Table | System configuration mapping every monitoring event type to a specific numerical risk weight (e.g. PHONE: +40, MULTIPLE_FACES: +30, FULLSCREEN_EXIT: +20). | Admin config table or default dictionary. | Weight lookup map for risk score calculator. | Reverts to system defaults if custom weight configuration missing. | ORIGINAL_REQUEST.md lines 263, 502, 533 |
| 33 | Phase 6: Risk Engine | Real-Time Risk Score Calculator | Ingests monitoring events, computes cumulative/decayed risk score (0–100), and records score progression. | Monitoring event payload, current session state. | Updated numerical risk score (0–100) and risk level classification. | Clamps score between 0 and 100; handles duplicate events idempotently. | ORIGINAL_REQUEST.md lines 264, 502, 533 |
| 34 | Phase 6: Risk Engine | Risk Level Threshold Classification | Maps numerical risk score to 4 discrete categories: `LOW` (0–29), `MEDIUM` (30–59), `HIGH` (60–79), `CRITICAL` (80–100). | Numerical risk score. | Risk level string (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). | Exact boundary mapping; logged in session record. | ORIGINAL_REQUEST.md lines 265, 533 |
| 35 | Phase 6: Risk Engine | Risk History & Timeline Recording | Maintains an append-only log of every risk score change, timestamp, and triggering event ID. | Risk calculation result, event reference. | `RiskScoreHistory` database record. | Database rollback on transaction error; event still acknowledged. | ORIGINAL_REQUEST.md lines 266, 533 |
| 36 | Phase 6: Risk Engine | WebSocket Push Dispatcher | Broadcasts real-time risk updates to active admin/invigilator WebSocket subscribers. | New risk event / score change. | JSON payload pushed to WebSocket topic `/api/ws/admin/exams/{exam_id}/live`. | Drops slow/disconnected consumers without blocking event pipeline. | ORIGINAL_REQUEST.md lines 267, 502, 533 |
| 37 | Phase 7: Live Admin Dashboard | Live Monitoring Grid View | Responsive grid displaying real-time cards for all active candidates taking an exam. | Exam ID, live WebSocket stream. | Rendered cards showing student name, email, risk badge, elapsed time, current score. | Displays "Connecting..." or fallback polling if WebSocket drops. | ORIGINAL_REQUEST.md lines 270, 502, 534 |
| 38 | Phase 7: Live Admin Dashboard | Real-Time Color-Coded Risk Badges | Dynamic UI badges showing Green (Low), Yellow (Medium), Orange (High), Red (Critical) with instant CSS pulse animations on update. | Current session risk level. | Color-coded visual indicator on student card. | Defaults to gray/neutral if session state unknown. | ORIGINAL_REQUEST.md lines 272, 534 |
| 39 | Phase 7: Live Admin Dashboard | Aggregate Session Metrics | Header banner displaying total enrolled, active sessions, submitted exams, and risk distribution breakdown. | Exam session collection. | Numeric counters and risk level pie/bar summary. | Auto-refreshes on session state change events. | ORIGINAL_REQUEST.md lines 273, 534 |
| 40 | Phase 7: Live Admin Dashboard | Per-Student Real-Time Modal View | Detailed modal accessible from any card displaying full chronological event feed, live risk timeline, and latest snapshots. | Student card click event. | Interactive slide-out or modal dialog with live timeline and snapshot carousel. | 404 if session terminates or data purged. | ORIGINAL_REQUEST.md lines 271, 534 |
| 41 | Phase 8: Review Center | Flagged Session Review Queue | Filterable list of completed/active sessions flagged by the risk engine (`HIGH`, `CRITICAL`, or manual proctor flag). | Filter parameters (exam_id, status, risk_level, reviewer_id). | Paginated table of flagged sessions awaiting human evaluation. | Empty state when no flagged sessions exist. | ORIGINAL_REQUEST.md lines 277, 502, 535 |
| 42 | Phase 8: Review Center | Comprehensive Evidence Viewer | Multi-pane UI with synchronized evidence: timeline scrubber, annotated snapshots with bounding boxes, event log, and student responses. | Session ID. | Visual playback interface linking video snapshots to specific timestamps and answers. | Graceful placeholder if snapshot storage unavailable. | ORIGINAL_REQUEST.md lines 278, 502, 535 |
| 43 | Phase 8: Review Center | Reviewer Action: Dismiss | Allows human reviewer to mark a flag as false positive (e.g. lighting glitch, natural stretching) with mandatory explanation. | Session ID, action=`DISMISS`, rationale text. | Review record updated to `DISMISSED`; session flag cleared. | Rejects action if rationale is blank. | ORIGINAL_REQUEST.md lines 279, 535 |
| 44 | Phase 8: Review Center | Reviewer Action: Escalate | Allows reviewer to escalate ambiguous or severe cases to senior integrity committee or faculty board. | Session ID, action=`ESCALATE`, escalation notes, target committee. | Review record updated to `ESCALATED`; notifies supervisor. | Requires escalation reason; audit record logged. | ORIGINAL_REQUEST.md lines 279, 535 |
| 45 | Phase 8: Review Center | Reviewer Action: Record Finding | Formally records a human verdict of confirmed academic misconduct with severity and penalty recommendations. | Session ID, action=`RECORD_FINDING`, violation type, severity, notes. | Review record updated to `VERIFIED_MISCONDUCT`; locks review. | Immutable once finalized (except via official student appeal). | ORIGINAL_REQUEST.md lines 279, 535 |
| 46 | Phase 8: Review Center | Review Assignment & Status Tracking | Assigns flagged sessions to specific reviewers and tracks review workflow states (`PENDING`, `IN_REVIEW`, `RESOLVED`). | Session ID, reviewer user ID. | Updated review assignment record. | 400 if user is not authorized reviewer. | ORIGINAL_REQUEST.md lines 280 |
| 47 | Phase 8: Review Center | Immutable Review Audit Trail | Logs every reviewer action, timestamp, reviewer identity, IP address, and decision reasoning into an audit log. | Reviewer interaction events. | `ReviewAuditTrail` records stored in PostgreSQL. | Append-only; deletion or modification prohibited by policy. | ORIGINAL_REQUEST.md lines 281, 490, 535 |
| 48 | Phase 9: Reporting | Exam Score Distribution & Item Analysis | Computes cohort statistics: mean, median, standard deviation, question-by-question pass rates and difficulty indices. | Exam ID. | Statistical summary JSON and chart representations. | Handles exams with zero completed submissions gracefully. | ORIGINAL_REQUEST.md lines 284, 502, 536 |
| 49 | Phase 9: Reporting | Integrity & Proctoring Summary Report | Aggregates all integrity data for an exam: total flags, breakdown of events by type, reviewer outcomes (dismissed vs confirmed). | Exam ID. | Comprehensive integrity report object. | 404 if exam does not exist. | ORIGINAL_REQUEST.md lines 285, 536 |
| 50 | Phase 9: Reporting | Student Longitudinal Profile | Tracks a student's integrity history, average risk scores, and review findings across multiple exams over time. | Student ID. | Student integrity dossier spanning all enrolled exams. | Restricted to Admin and authorized Reviewers. | ORIGINAL_REQUEST.md lines 286 |
| 51 | Phase 9: Reporting | CSV Export Engine | Exports tabular exam results, candidate scores, risk scores, event tallies, and reviewer decisions to downloadable CSV. | Exam ID, export filters. | Formatted CSV file download with standard RFC 4180 formatting. | Proper escaping of commas, quotes, and multiline text. | ORIGINAL_REQUEST.md lines 287, 502, 536 |
| 52 | Phase 9: Reporting | PDF Report Generation | Generates formal, printable PDF incident reports containing evidence snapshots, event timelines, and reviewer signatures. | Session ID / Exam ID. | Rendered binary PDF document stream. | Fallback text rendering if image snapshot rendering fails. | ORIGINAL_REQUEST.md lines 287 |
| 53 | Phase 10: Tooling | Demo Data Seeding Script | CLI script `scripts/seed_demo_data.py` that populates institution, users (admin, proctor, reviewer, students), exams, questions, sessions, events, and snapshots. | `python scripts/seed_demo_data.py` | Fully populated database ready for immediate UI/API exploration. | Idempotent execution; avoids duplicate key collisions. | ORIGINAL_REQUEST.md lines 60–63, 293, 529 |
| 54 | Phase 10: Tooling | End-to-End & API Integration Tests | Automated test suite verifying complete exam lifecycle: student login -> exam start -> monitoring events -> risk scoring -> review verdict. | `pytest tests/` | Test report with 100% passing core integration tests. | Clear assertion failures with detailed diagnostic trace. | ORIGINAL_REQUEST.md lines 290–296, 528–537 |

---

## 3. Edge Cases Discovered & Observed Behaviors

| # | Feature | Input / Condition | Observed / Required Behavior |
|---|---------|-------------------|-----------------------------|
| 1 | Exam Engine | Candidate attempts to start exam before `start_time`. | Endpoint returns 403 Forbidden with `{ "error": "EXAM_NOT_STARTED", "start_time": "..." }`. Exam portal displays countdown until start time. |
| 2 | Exam Engine | Candidate attempts to start exam after `start_time + late_entry_window_minutes`. | Endpoint returns 403 Forbidden with `{ "error": "LATE_ENTRY_WINDOW_EXPIRED" }`. Candidate is prevented from taking the exam and advised to contact instructor. |
| 3 | Exam Engine | Candidate submits exam after duration has expired. | Backend verifies expiration timestamp; automatically marks session status as `AUTO_SUBMITTED`, saves final answers, and rejects further answer mutations. |
| 4 | Exam Engine | Student attempts to access an exam they are not enrolled in. | Endpoint returns 403 Forbidden with `{ "error": "NOT_ENROLLED" }`. Exam does not appear on student's dashboard. |
| 5 | Exam Engine | Student opens exam session concurrently in two tabs or browsers. | Second session start generates a `CONCURRENT_SESSION_DETECTED` event, alerts proctor, and either terminates earlier session or flags session for review (never auto-blocks student from completing). |
| 6 | Auto-Save Engine | Network connection drops while student is typing an answer. | Client-side auto-save queue stores answer locally (IndexedDB / memory). UI shows "Offline - Changes saved locally". Answers synced to backend immediately upon reconnect. |
| 7 | Auto-Save Engine | Concurrent answer updates sent out of order due to network latency. | Backend applies last-write-wins based on client timestamp or monotonic version counter, preventing older drafts from overwriting newer text. |
| 8 | Browser Monitoring | Candidate triggers fullscreen exit by pressing ESC or Alt+Tab. | Event listener intercepts `fullscreenchange`, logs `FULLSCREEN_EXIT` event to backend, updates risk score, and presents prominent modal prompting student to re-enter fullscreen. |
| 9 | Browser Monitoring | Candidate attempts to copy question text or paste external text. | Clipboard events (`copy`, `cut`, `paste`) are cancelled via `preventDefault()`. Event `COPY_ATTEMPT` or `PASTE_ATTEMPT` is recorded with clipboard payload metadata (character count). |
| 10 | Browser Monitoring | Candidate resizes window or opens DevTools. | `window.onresize` detects sudden dimension changes. If DevTools is opened, window inner/outer dimension disparities log `DEVTOOLS_OPEN` and `WINDOW_RESIZE` to backend. |
| 11 | Webcam Monitoring | Candidate covers webcam or walks away from camera frame. | Computer vision detector finds 0 faces. If duration exceeds threshold (e.g. > 10s), `FACE_NOT_DETECTED` event is triggered, contributing +15 to session risk score. |
| 12 | Webcam Monitoring | Second person enters frame behind or next to candidate. | Computer vision detector finds >= 2 faces. Bounding boxes are drawn around both faces, snapshot is saved, and `MULTIPLE_FACES` event (+30 risk) is pushed to proctor dashboard. |
| 13 | Webcam Monitoring | Candidate holds a smartphone up to read questions or search. | YOLO detector detects `cell phone` object with confidence > 0.60. Snapshot is marked with phone bounding box, `PHONE_DETECTED` event (+40 risk) is emitted. |
| 14 | Webcam Monitoring | Candidate webcam stream fails or permissions revoked mid-exam. | Client logs `WEBCAM_DISCONNECTED` event. Risk score increases. Student receives warning modal to grant camera permissions. Exam is not terminated, but flagged for reviewer. |
| 15 | Risk Engine | Rapid succession of identical events (e.g., 50 blur events in 2 seconds). | Risk engine applies event debouncing / rate limiting to avoid artificial score inflation beyond maximum event category ceiling. |
| 16 | Risk Engine | Risk score calculation exceeds 100 points due to multiple infractions. | Score is strictly clamped to max 100 (`min(calculated_score, 100)`). Risk level remains `CRITICAL`. |
| 17 | Admin Dashboard | Admin's WebSocket connection drops due to local Wi-Fi blip. | Client frontend automatically attempts exponential backoff reconnection. While disconnected, polls REST endpoint `/api/admin/exams/{id}/live-summary` every 5s. |
| 18 | Review Center | Reviewer attempts to submit finding without entering justification text. | Validation returns 422 Unprocessable Entity. System enforces mandatory non-empty reviewer rationale before changing status to `DISMISSED` or `RECORD_FINDING`. |
| 19 | Review Center | AI detector flagged phone on an innocuous object (e.g. calculator or dark wallet). | Human reviewer inspects annotated snapshot, identifies false positive, selects `DISMISS`, logs note "Object identified as TI-84 calculator", clearing suspicion. |
| 20 | Reporting | Exam has 0 enrolled students or 0 submissions when generating report. | API returns 200 OK with zeroed statistics (mean: 0, median: 0, std_dev: 0) instead of dividing by zero (ZeroDivisionError). |
| 21 | Seed Data Script | Script `scripts/seed_demo_data.py` run multiple times in succession. | Script checks for existing records by unique keys (emails, exam codes), updating or skipping existing rows idempotently without unique constraint violations. |
| 22 | Docker Compose | Backend starts before PostgreSQL or Redis is ready to accept connections. | Docker Compose healthchecks or backend entrypoint wait-for-it script loops until DB port 5432 and Redis port 6379 are listening before launching Uvicorn. |

---

## 4. Documentation Specifications (`docs/`)

Per `ORIGINAL_REQUEST.md`, four authoritative documentation files must be created in the `docs/` directory. The exact content, structure, and constraints extracted are as follows:

### 4.1 `docs/readme.md` — Project Overview & Getting Started
- **Header & Tagline**:
  - Title: `# ExamSentinel`
  - Tagline: `AI-Powered Examination Integrity Platform — now extended with coding exams, interview exams, and adaptive digital exam capabilities.`
  - Core description: ExamSentinel lets institutions run secure online exams with intelligent, human-reviewed integrity monitoring. **No AI model ever issues a final verdict; every signal it surfaces is routed to a human reviewer.**
- **Capability Tracks Table**:
  1. *Core Exam Platform*: Student portal, exam builder, question bank, browser + webcam proctoring, risk engine, live admin dashboard, review workflow, reporting.
  2. *Coding Exams*: In-browser code editor (Monaco), sandboxed multi-language execution, autograding, plagiarism/similarity detection, paste- and typing-pattern integrity signals.
  3. *Interview Exams*: Live video interviews (WebRTC), async recorded interviews, panel rubric scoring, auto-transcription, reviewer highlight navigation.
  4. *Digital Exam Extensions*: Adaptive (IRT-based) difficulty, offline-resilient exam state, LMS/SSO integration, mobile exam mode, multi-modal question types (diagram, whiteboard, audio).
  5. *Compliance & Legal*: Versioned consent capture, per-institution data retention/deletion, student appeals process, accessibility (WCAG) audits, question-bank IP handling.
  6. *Reliability & Operations*: CI/CD gating, observability/alerting, exam-start load testing, backup & disaster recovery.
  7. *Anti-Cheat Hardening*: VPN/proxy detection, multi-device/multi-tab detection, interview screen-share detection, question-leak detection.
  8. *Cost & Product Polish*: Usage metering and budget alerts, notifications (email/SMS), calendar integration for interviews, pre-publish autograder validation.
- **Tech Stack**:
  - Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Monaco Editor.
  - Backend: Python, FastAPI, Pydantic, SQLAlchemy, WebSockets.
  - Database: PostgreSQL.
  - AI / Computer Vision: OpenCV, YOLO, MediaPipe, NumPy, scikit-learn.
  - Code Execution: Judge0 (or custom gVisor/Firecracker-isolated workers).
  - Video Interviews: LiveKit / Daily.
  - Transcription: Whisper-class model.
  - Infrastructure: Docker, Docker Compose, Redis.
- **Getting Started Guide**:
  ```bash
  git clone <repo-url>
  cd exam-sentinel
  cp .env.example .env
  docker compose up -d
  ```
  - Frontend: `http://localhost:3000`
  - Backend API: `http://localhost:8000`
  - API Docs (Swagger): `http://localhost:8000/docs`
  - Seed Demo Data: `docker compose exec backend python scripts/seed_demo_data.py`
- **5 Core Design Principles**:
  1. *No automated guilt*: The platform calculates risk scores and surfaces evidence; only a human reviewer decides on misconduct.
  2. *Signals, not verdicts*: Every detector feeds a review queue, never an auto-penalty.
  3. *No overclaiming*: The platform never implies monitoring coverage it doesn't actually have.
  4. *Privacy by design*: Data minimization, configurable retention, role-based access to evidence, and explicit consent before any capture.
  5. *Human review at every consequential step*.

### 4.2 `docs/plan.md` — Full 20-Phase Build Plan
- **Scope Matrix**: Covers all 7 expansion tracks (Coding, Interviews, Digital Exams, Compliance, Reliability, Cost Governance, Polish).
- **Target Repository Structure**:
  - `frontend/` (Next.js 14+ App Router, components, hooks, services).
  - `backend/` (FastAPI app, api routes, services, models, websockets).
  - `execution-workers/` (Sandboxed runner).
  - `ai/` (detectors, code-integrity, interview-analysis).
  - `connectors/` (LMS/LTI, SSO).
  - `compliance/` (retention policies, consent flows, accessibility audits).
  - `.github/workflows/` (CI/CD pipelines).
  - `observability/`, `load-testing/`, `infra/` (backup/DR), `database/migrations/`, `docs/`.
  - `docker-compose.yml`.
- **Database Tables Catalog**:
  - Coding: `code_submissions`, `test_cases`, `execution_results`, `language_configs`, `test_case_validation_runs`.
  - Interviews: `interview_sessions`, `interview_questions`, `interview_recordings`, `interview_scores`, `screen_share_flags`.
  - Adaptive: `question_irt_params`, `student_ability_est`.
  - LMS/SSO: `lms_sync_jobs`.
  - Compliance: `consent_records`, `data_retention_policies`, `retention_deletion_jobs`, `appeal_cases`, `appeal_actions`, `accessibility_audit_logs`.
  - Security & Device Integrity: `device_sessions`, `vpn_proxy_flags`, `multi_tab_events`.
  - Cost Governance: `usage_logs`, `budget_alerts`.
  - Product/UX: `notification_logs`, `calendar_syncs`, `question_leak_reports`.
- **Phase Breakdown**:
  - Detailed milestones for Phases 1 through 20 (Phase 1–10 Core Platform, Phase 11–16 Feature Tracks, Phase 17–20 Compliance & Hardening).
- **Working Method**:
  1. Contract first: API schemas and DB migration before UI or business logic.
  2. Backend before frontend: verified via `/docs`.
  3. Isolate the risky part: prove integrations standalone before embedding.
  4. Test failure paths: timeouts, dropped calls, offline sync conflicts.
  5. Update risk engine weight table in same PR as any new signal.
  6. Feature flag per exam/institution.
  7. Compliance and reliability are equal priority to features.
- **Definition of Done**: Clear acceptance criteria across all modules.

### 4.3 `docs/explain.md` — Subsystem Architecture & Design Rationale
Covers in-depth rationale for 16 subsystems:
1. *Code Execution Sandbox*: Isolation requirements (gVisor/Firecracker, no network, stateless workers).
2. *Code-Specific Integrity Signals*: Typing cadence and paste analysis treated strictly as signals, not proofs.
3. *Live Interview Mode*: Use WebRTC-as-a-service (LiveKit/Daily), multi-panelist independent scoring.
4. *Async Interview + Transcription*: Whisper time-aligned transcription, clickable navigational highlights.
5. *Adaptive Testing (IRT)*: 2-parameter logistic model ($a, b$), ability ($\theta$) estimation with confidence intervals.
6. *Offline Resilience*: IndexedDB client mirroring, queue-and-replay on reconnect, last-write-wins with audit log.
7. *LMS/SSO Integration*: Standards-based LTI 1.3 for rosters and grade passback; SAML2/OAuth2.
8. *Mobile Exam Mode*: Explicit disclosure of reduced monitoring capability on mobile devices.
9. *Multi-Modal Question Types*: Diagram labeling (hotspots), whiteboard (vector stroke replay), audio response.
10. *Consent & Retention*: Versioned consent text, scheduled per-institution retention and deletion.
11. *Appeals Process*: Contestability for students against automated or reviewer findings, separate review queue.
12. *Accessibility*: WCAG 2.1 AA compliance, screen-reader mode in Monaco, extended time accommodations.
13. *CI/CD, Observability, Load Testing & DR*: Zero merge without CI; metrics and alerting; restore drill.
14. *Anti-Cheat Hardening*: Low-weight contextual signals (VPN/proxy), multi-device detection without auto-blocking.
15. *Cost Governance*: Metering sandbox, video, and transcription minutes; never kill in-progress exams.
16. *Notifications, Calendar, Autograder Validation*: Trans-channel notifications, iCal, pre-publish validation.

### 4.4 `docs/prompt.md` — AI Agent Operating Instructions
- **Role**: Production-grade implementation on existing platform.
- **Ground Rules**:
  1. Work one phase at a time (Phase 1 -> 20).
  2. Never guess at security-sensitive design.
  3. Every new signal must reach the risk engine in the same change.
  4. Never let AI output become a verdict — always human-reviewer-facing evidence.
  5. Contract-first: schemas and migrations first.
  6. Backend before frontend, verified via `/docs`.
  7. Feature-flag per exam/institution.
  8. Test failure paths.
- **12 Non-Negotiable Constraints**:
  - No automated "cheating" verdicts.
  - No inference from demographics, appearance, disability, or emotion.
  - No plaintext secrets, no client-side-only auth checks.
  - No silent overclaiming of monitoring capability.
  - No student work lost on disconnect.
  - No untracked data collection.
  - No silent deletion or silent retention.
  - No decision without an appeal path.
  - No VPN/device/multi-tab signal may auto-block a student.
  - No budget enforcement may interrupt an exam in progress.
  - No production deploy without CI passing.
  - No claim of DR readiness without a tested restore.

---

## 5. Core Platform Technical Architecture (Phases 1–10)

### 5.1 Database Models & Entity-Relationship Schema

```
+------------------+         +--------------------+         +-------------------+
|      User        | 1     * |        Exam        | 1     * |   ExamEnrollment  |
|------------------+<--------|--------------------+<--------|-------------------|
| id (UUID)        |         | id (UUID)          |         | id (UUID)         |
| email (unique)   |         | title              |         | exam_id (FK)      |
| hashed_password  |         | description        |         | student_id (FK)   |
| role (enum)      |         | duration_minutes   |         | status (enum)     |
| institution_id   |         | start_time         |         | enrolled_at       |
| created_at       |         | end_time           |         +-------------------+
+------------------+         | late_entry_window  |                   | 1
         | 1                 | settings (JSONB)   |                   |
         |                   +--------------------+                   | *
         |                             | 1                  +-------------------+
         |                             | *                  |    ExamSession    |
         |                   +--------------------+         |-------------------|
         |                   |    ExamQuestion    |         | id (UUID)         |
         |                   |--------------------+         | enrollment_id(FK) |
         |                   | id (UUID)          |         | student_id (FK)   |
         |                   | exam_id (FK)       |         | exam_id (FK)      |
         |                   | question_id (FK)   |         | status (enum)     |
         |                   | order_index        |         | started_at        |
         |                   | points             |         | submitted_at      |
         |                   +--------------------+         | current_risk_score|
         |                             | *                  | risk_level (enum) |
         |                             | 1                  +-------------------+
         |                   +--------------------+           | 1           | 1
         |                   |      Question      |           |             |
         |                   |--------------------+           | *           | *
         |                   | id (UUID)          |    +------------+ +---------------+
         |                   | type (enum)        |    |StudentAns  | |MonitoringEvent|
         |                   | prompt (text)      |    |------------| |---------------|
         |                   | options (JSONB)    |    |id (UUID)   | |id (UUID)      |
         |                   | rubric (JSONB)     |    |session_id  | |session_id(FK) |
         |                   | points             |    |question_id | |event_type     |
         |                   | tags (array)       |    |answer_data | |severity       |
         |                   +--------------------+    |is_flagged  | |risk_points    |
         |                                             +------------+ |metadata(JSONB)|
         |                                                            |timestamp      |
         |                                                            +---------------+
         |                                                                    | 1
         |                                                                    | *
         |                   +--------------------+                   +---------------+
         |                   |    ReviewRecord    | 1               * |SessionSnapshot|
         |                   |--------------------+<------------------|---------------|
         |                   | id (UUID)          |                   | id (UUID)     |
         +------------------>| reviewer_id (FK)   |                   | session_id(FK)|
                             | session_id (FK)    |                   | image_path    |
                             | status (enum)      |                   | timestamp     |
                             | decision (enum)    |                   | face_count    |
                             | rationale (text)   |                   | phone_detected|
                             | findings (JSONB)   |                   | boxes (JSONB) |
                             +--------------------+                   +---------------+
```

#### Core Enumerations
1. `UserRole`: `ADMIN`, `INVIGILATOR`, `STUDENT`, `REVIEWER`.
2. `ExamStatus`: `DRAFT`, `SCHEDULED`, `ACTIVE`, `COMPLETED`, `ARCHIVED`.
3. `QuestionType`: `MCQ`, `SHORT_ANSWER`, `LONG_ANSWER`, `CODING`.
4. `EnrollmentStatus`: `ENROLLED`, `IN_PROGRESS`, `COMPLETED`, `EXPIRED`.
5. `SessionStatus`: `NOT_STARTED`, `IN_PROGRESS`, `SUBMITTED`, `AUTO_SUBMITTED`, `TERMINATED`.
6. `RiskLevel`: `LOW` (0-29), `MEDIUM` (30-59), `HIGH` (60-79), `CRITICAL` (80-100).
7. `EventType`: `TAB_BLUR`, `TAB_FOCUS`, `FULLSCREEN_EXIT`, `FULLSCREEN_ENTER`, `COPY_ATTEMPT`, `PASTE_ATTEMPT`, `RIGHT_CLICK_ATTEMPT`, `WINDOW_RESIZE`, `DEVTOOLS_OPEN`, `FACE_NOT_DETECTED`, `MULTIPLE_FACES`, `PHONE_DETECTED`, `WEBCAM_DISCONNECTED`.
8. `ReviewStatus`: `PENDING_REVIEW`, `IN_REVIEW`, `DISMISSED`, `ESCALATED`, `RESOLVED`.
9. `ReviewDecision`: `DISMISSED`, `ESCALATED`, `VERIFIED_MISCONDUCT`, `NO_ACTION`.

---

### 5.2 REST API Endpoints Specification

#### Authentication & User Management
- `POST /api/auth/register`
  - Body: `{ "email": "...", "password": "...", "full_name": "...", "role": "..." }`
  - Returns: `{ "id": "...", "email": "...", "role": "..." }` (201 Created)
- `POST /api/auth/login`
  - Body: `{ "email": "...", "password": "..." }`
  - Returns: `{ "access_token": "...", "refresh_token": "...", "token_type": "bearer", "user": { ... } }`
- `POST /api/auth/refresh`
  - Body: `{ "refresh_token": "..." }`
  - Returns: `{ "access_token": "...", "token_type": "bearer" }`
- `GET /api/auth/me`
  - Headers: `Authorization: Bearer <token>`
  - Returns: Current user profile and role permissions.

#### Exam Management (Admin & Invigilator)
- `GET /api/exams`
  - Query: `page`, `limit`, `status`, `institution_id`
  - Returns: Paginated list of exams.
- `POST /api/exams`
  - Body: `{ "title": "...", "description": "...", "duration_minutes": 60, "start_time": "...", "end_time": "...", "late_entry_window_minutes": 15, "settings": { ... } }`
  - Returns: Created exam object (201 Created).
- `GET /api/exams/{id}`
  - Returns: Full exam details with questions and settings.
- `PUT /api/exams/{id}`
  - Body: Partial or full exam update.
- `DELETE /api/exams/{id}`
  - Soft-deletes or archives the exam.
- `POST /api/exams/{id}/enroll`
  - Body: `{ "student_ids": ["uuid-1", "uuid-2"] }`
  - Returns: Enrollment confirmation list.

#### Question Bank Management
- `GET /api/questions`
  - Query: `type`, `category`, `tag`, `search`
- `POST /api/questions`
  - Body: `{ "title": "...", "type": "MCQ", "prompt": "...", "points": 5.0, "options": [...], "tags": ["math", "algebra"] }`
- `PUT /api/questions/{id}`
- `DELETE /api/questions/{id}`
- `POST /api/exams/{id}/questions`
  - Body: `{ "question_id": "...", "order_index": 1, "custom_points": null }`

#### Student Exam Execution Portal
- `GET /api/student/exams`
  - Returns: List of exams the authenticated student is enrolled in with schedule status.
- `POST /api/sessions/start`
  - Body: `{ "exam_id": "..." }`
  - Validation: Checks enrollment, schedule window, late entry threshold.
  - Returns: Active session object with token, started_at timestamp, and question list (without correct answers).
- `GET /api/sessions/{session_id}`
  - Returns: Session state, remaining time in seconds, answered question indices.
- `PUT /api/sessions/{session_id}/answers/{question_id}`
  - Body: `{ "answer_data": { "selected_option_id": "..." }, "is_flagged": false }`
  - Returns: `{ "status": "saved", "updated_at": "..." }`
- `POST /api/sessions/{session_id}/submit`
  - Body: `{ "confirm": true }`
  - Returns: `{ "session_id": "...", "status": "SUBMITTED", "submitted_at": "..." }`

#### Telemetry & Monitoring Ingestion
- `POST /api/sessions/{session_id}/events`
  - Body: `{ "event_type": "FULLSCREEN_EXIT", "timestamp": "...", "metadata": { "exit_count": 2 } }`
  - Returns: `{ "event_id": "...", "current_risk_score": 45, "risk_level": "MEDIUM" }`
- `POST /api/sessions/{session_id}/snapshots`
  - Body: Multipart image file (JPEG/PNG) + `{ "timestamp": "..." }`
  - Processes frame through OpenCV/YOLO face & phone detectors.
  - Returns: `{ "snapshot_id": "...", "faces_detected": 1, "phone_detected": false, "risk_score": 15 }`

#### Live Monitoring & Dashboards (Invigilator / Admin)
- `GET /api/admin/exams/{exam_id}/live-summary`
  - Returns: Enrolled count, active sessions, submitted count, risk score distribution.
- `GET /api/admin/exams/{exam_id}/sessions`
  - Query: `risk_level`, `search`, `page`, `limit`
  - Returns: Real-time list of candidate session cards with latest risk metrics.
- `GET /api/admin/sessions/{session_id}/timeline`
  - Returns: Complete chronological stream of events and snapshots for candidate.

#### Review Center
- `GET /api/reviews/queue`
  - Query: `exam_id`, `status`, `min_risk_score`
  - Returns: Flagged sessions awaiting review.
- `GET /api/reviews/{review_id}`
  - Returns: Evidence package: candidate answers, snapshots with bounding boxes, timeline.
- `POST /api/reviews/{review_id}/action`
  - Body: `{ "action": "DISMISS" | "ESCALATE" | "RECORD_FINDING", "rationale": "...", "findings": { ... } }`
  - Returns: Updated review record with immutable audit trail entry.

#### Reporting & Exports
- `GET /api/reports/exams/{exam_id}/summary`
  - Returns: Performance and integrity summary statistics.
- `GET /api/reports/exams/{exam_id}/export/csv`
  - Returns: Downloadable CSV file of results and proctoring outcomes.
- `GET /api/reports/sessions/{session_id}/export/pdf`
  - Returns: Rendered PDF integrity incident report.

---

### 5.3 WebSocket Protocols & Live Streams

#### 1. Admin Live Monitoring Stream
- **URL**: `ws://localhost:8000/api/ws/admin/exams/{exam_id}/live`
- **Authentication**: Connection query parameter `?token=<jwt>` validated on handshake.
- **Outbound Event Types (Server -> Admin Client)**:
  - `SESSION_STARTED`: Candidate initiated session.
  - `RISK_UPDATE`: Real-time score recalculation.
    ```json
    {
      "type": "RISK_UPDATE",
      "session_id": "e5b1...49f",
      "student_id": "u21...90a",
      "student_name": "Jane Doe",
      "score": 75,
      "risk_level": "HIGH",
      "trigger_event": "PHONE_DETECTED",
      "timestamp": "2026-09-16T10:55:00Z"
    }
    ```
  - `MONITORING_ALERT`: Instant high-severity flag (e.g., Phone Detected, Multiple Faces).
  - `SESSION_SUBMITTED`: Candidate submitted exam.

#### 2. Student Session Heartbeat Stream (Optional / Complementary to REST)
- **URL**: `ws://localhost:8000/api/ws/student/session/{session_id}`
- **Usage**: Bi-directional keepalive, countdown sync, proctor urgent broadcasts ("Please center yourself in camera").

---

### 5.4 Algorithmic Specifications

#### 1. Risk Engine Score Accumulation & Classification
The risk engine maps event occurrences to numerical increments. Let:
- $S_t$: Current risk score at event $t$ ($0 \le S_t \le 100$).
- $w_e$: Weight of incoming event $e$.
- $\alpha$: Decay factor per minute of clean behavior (e.g., $\alpha = 0.98$).
- $\Delta t$: Elapsed time in minutes since last event.

**Standard Weight Table**:
| Event Type | Weight ($w_e$) | Category |
|------------|----------------|----------|
| `PHONE_DETECTED` | +40 | Hardware / Device |
| `MULTIPLE_FACES` | +30 | Visual Anomaly |
| `DEVTOOLS_OPEN` | +25 | Technical / Browser |
| `FULLSCREEN_EXIT` | +20 | Browser Boundary |
| `FACE_NOT_DETECTED` (>10s) | +15 | Visual Anomaly |
| `TAB_BLUR` | +10 | Focus Loss |
| `PASTE_ATTEMPT` | +10 | Clipboard |
| `COPY_ATTEMPT` | +5 | Clipboard |
| `RIGHT_CLICK_ATTEMPT` | +5 | Browser Action |
| `WINDOW_RESIZE` | +5 | Browser Action |

**Score Update Equation**:
$$S_t = \min\left(100, \max\left(0, S_{t-1} \cdot \alpha^{\Delta t} + w_e\right)\right)$$

**Classification Mapping**:
$$\text{RiskLevel}(S_t) = \begin{cases}
\text{LOW}, & 0 \le S_t < 30 \\
\text{MEDIUM}, & 30 \le S_t < 60 \\
\text{HIGH}, & 60 \le S_t < 80 \\
\text{CRITICAL}, & 80 \le S_t \le 100
\end{cases}$$

#### 2. Computer Vision Detection Pipeline
When a frame snapshot is received:
1. **Decode & Preprocess**: Convert base64 / binary buffer to OpenCV BGR matrix; verify image dimensions ($\ge 640\times 480$).
2. **Face Detection**:
   - Run face detector (MediaPipe Face Mesh or OpenCV Haar / DNN face detector).
   - If face count == 0: increment absence counter; if prolonged, emit `FACE_NOT_DETECTED`.
   - If face count > 1: record bounding boxes of all faces, emit `MULTIPLE_FACES`.
3. **Object Detection**:
   - Run lightweight YOLO (e.g. YOLOv8n / YOLOv5s) on frame targeting classes: `cell phone`, `book`, `laptop`.
   - If class `cell phone` detected with confidence $\ge 0.50$: record bounding box coordinates $[x_1, y_1, x_2, y_2]$, annotate frame, emit `PHONE_DETECTED`.
4. **Storage**: Save annotated JPEG to storage path `uploads/snapshots/{session_id}/{uuid}.jpg` and store record in `SessionSnapshot`.

#### 3. Auto-Submit Engine
A background task (Celery / APScheduler / asyncio loop) checks for active sessions where:
$$\text{current\_time} > \text{started\_at} + \text{duration\_minutes} \times 60$$
If condition met:
- Transition `session.status = SessionStatus.AUTO_SUBMITTED`.
- Set `session.submitted_at = current_time`.
- Invalidate further answer update permissions.
- Emit WebSocket notification `SESSION_SUBMITTED` to admin dashboard.

---

### 5.5 Role-Based Access Control (RBAC) Matrix

| Resource / Capability | Admin | Invigilator / Proctor | Student / Candidate | Reviewer |
|-----------------------|:-----:|:---------------------:|:-------------------:|:--------:|
| User Management (CRUD) | ✅ | ❌ | ❌ | ❌ |
| Exam Authoring & CRUD | ✅ | ✅ | ❌ | ❌ |
| Question Bank Management | ✅ | ✅ | ❌ | ❌ |
| Student Enrollment | ✅ | ✅ | ❌ | ❌ |
| Take Exam & Submit Answers | ❌ | ❌ | ✅ (Enrolled only) | ❌ |
| Live Dashboard View | ✅ | ✅ | ❌ | ❌ |
| Live WebSocket Feed | ✅ | ✅ | ❌ | ❌ |
| Review Queue Access | ✅ | ❌ | ❌ | ✅ |
| Record Review Finding / Dismiss | ✅ | ❌ | ❌ | ✅ |
| Export CSV / PDF Reports | ✅ | ✅ | ❌ (Own summary only) | ✅ |
| Trigger Seed Demo Data | ✅ (CLI) | ❌ | ❌ | ❌ |

---

### 5.6 Deployment Architecture & Seed Script

#### Docker Compose Specification (`docker-compose.yml`)
1. **Frontend**:
   - Image/Build: `./frontend`
   - Ports: `3000:3000`
   - Environment: `NEXT_PUBLIC_API_URL=http://localhost:8000`
2. **Backend**:
   - Image/Build: `./backend`
   - Ports: `8000:8000`
   - Depends On: `db`, `redis`
   - Environment: `DATABASE_URL=postgresql://sentinel:sentinel_pass@db:5432/sentinel_db`, `REDIS_URL=redis://redis:6379/0`, `JWT_SECRET=...`
3. **Database (`db`)**:
   - Image: `postgres:15-alpine`
   - Ports: `5432:5432`
   - Volumes: `pgdata:/var/lib/postgresql/data`
4. **Cache & Queue (`redis`)**:
   - Image: `redis:7-alpine`
   - Ports: `6379:6379`

#### Seed Demo Data Script (`scripts/seed_demo_data.py`)
Executed via:
```bash
docker compose exec backend python scripts/seed_demo_data.py
```
**Seed Payload**:
- **Institution**: Sentinel University (`SU-101`).
- **Users**:
  - Admin: `admin@sentinel.edu` / `AdminPass123!`
  - Invigilator: `proctor@sentinel.edu` / `ProctorPass123!`
  - Reviewer: `reviewer@sentinel.edu` / `ReviewerPass123!`
  - Students (5): `alice@sentinel.edu`, `bob@sentinel.edu`, `charlie@sentinel.edu`, `david@sentinel.edu`, `eve@sentinel.edu` / `StudentPass123!`
- **Sample Exams**:
  - Exam 1: "CS101: Introduction to Computer Systems" (Scheduled, 60 mins, MCQs + Short Answers).
  - Exam 2: "DATA201: Data Structures & Algorithms" (Active session, with sample proctoring events).
- **Simulated Monitoring Data**:
  - 1 Clean session (Low risk, score: 5).
  - 1 Moderate session (Tab switches, fullscreen exits, score: 35, Medium risk).
  - 1 High risk session (Multiple faces, repeated blur, score: 65, High risk).
  - 1 Critical flagged session (Phone detected, DevTools opened, score: 85, Critical risk, awaiting review in Review Center).

---

## 6. Verification and Integration Test Suite Outline

The implementation of Phases 1–10 will be verified via a comprehensive Pytest test harness and Playwright / Jest frontend tests:

1. **Authentication Tests (`tests/api/test_auth.py`)**:
   - Registration, login, JWT token issuance and claims verification.
   - Password hashing and invalid password rejection.
   - RBAC enforcement (verifying 403 Forbidden for students accessing admin routes).
2. **Exam Engine Tests (`tests/api/test_exams.py`)**:
   - CRUD operations on exams and questions.
   - Enrollment validation.
   - Schedule enforcement: rejection before start time and after late entry window.
   - Session lifecycle: start -> answer auto-save -> manual submit -> auto-submit on duration expiry.
3. **Proctoring Telemetry Tests (`tests/api/test_monitoring.py`)**:
   - Ingestion of browser events (`TAB_BLUR`, `FULLSCREEN_EXIT`, `PASTE_ATTEMPT`).
   - Image snapshot upload and computer vision pipeline mock / run (face detection, phone detection).
4. **Risk Engine Tests (`tests/unit/test_risk_engine.py`)**:
   - Weight accumulation verification.
   - Clamping at 100, decaying over time.
   - Threshold transitions (Low -> Medium -> High -> Critical).
   - WebSocket broadcast verification.
5. **Review Center Tests (`tests/api/test_reviews.py`)**:
   - Flagged session appearance in review queue.
   - Evidence retrieval (timeline, snapshots).
   - Reviewer actions: `DISMISS`, `ESCALATE`, `RECORD_FINDING`.
   - Rejection of empty rationale.
   - Audit log generation.
6. **Reporting Tests (`tests/api/test_reports.py`)**:
   - Score distribution calculation.
   - CSV export formatting and content verification.
   - PDF generation output validity.
7. **End-to-End Integration Flow (`tests/e2e/test_exam_lifecycle.py`)**:
   - Complete multi-role simulation: Admin creates exam -> Student takes exam with events -> Risk engine flags session -> Invigilator views live card -> Reviewer inspects evidence and records finding.

---
*Report compiled and certified by `spec_miner_survey_1`.*
