# ExamSentinel — E2E Test Infrastructure & Specification (Tiers 1–4)

## 1. Test Philosophy

ExamSentinel's testing strategy relies on **authentic, opaque-box, requirement-driven verification**. The test harness exercises the platform exclusively through its external boundaries—REST API endpoints, WebSocket streams, WebRTC signal boundaries, and worker protocols—without importing backend internals or coupling to private database models.

### Key Principles:
1. **Opaque-Box Boundary Testing**: All assertions validate HTTP response codes, response payloads, WebSocket message schemas, and observable external artifacts. No direct queries against database internals bypassing the API.
2. **Zero Facade Testing**: No vacuous assertions (`assert True`, empty try/except). Every test asserts strict invariant properties, schema adherence, and stateful side-effects.
3. **Progressive Testability**: The test suite can run against live milestone deployments or simulated local environments. When an endpoint is unmounted or in-development, tests surface clear skip/pending statuses without masking defects.
4. **Adversarial & Fault Injection**: Tests actively supply malformed tokens, boundary inputs, SQL/XSS payloads, concurrent conflicting payloads, and timing race conditions.
5. **Authoritative Specification Tracing**: Every test maps directly to numbered requirements in `ORIGINAL_REQUEST.md` and feature entries in `PROJECT.md`.

---

## 2. Feature Inventory & Test Tier Mapping (Features 1 to 69)

| Feature # | Feature Name | Milestone | Tier 1 (Feature Coverage) | Tier 2 (Boundary & Corner Cases) | Tier 3 (Pairwise Interactions) | Tier 4 (Real-World Application Scenarios) |
|---|---|---|---|---|---|---|
| 1 | Documentation Suite | M1 | Verifies file presence, non-empty content, verbatim headers in docs/ | Corrupted markdown, UTF-8 BOM, missing sections | Docs links vs actual endpoints | New engineer onboarding flow |
| 2 | Docker Compose Environment | M1 | Verifies compose YAML syntax, service definitions (backend, frontend, postgres, redis, worker) | Missing port bindings, invalid env vars, resource limits | Container restart under load | Full-stack automated spin-up & healthcheck |
| 3 | Core Database Schema & Migrations | M1 | Health check schema status, table creation via Alembic migrations | Duplicate migration versions, downgrade rollback | Concurrent migrations, connection pool starvation | Cold-start migration & seeding drill |
| 4 | Authentication & JWT Service | M1 | Register, login, token issuance, refresh token exchange, revocation | Expired JWT, tampered signature, empty bearer, malformed header | Login storm during token expiration | Multi-device user credential lifecycle |
| 5 | Role-Based Access Control (RBAC) | M1 | Admin/Proctor/Reviewer/Candidate route access permissions | Role spoofing in token claims, case sensitivity of role strings | Cross-role privilege escalation attempts | End-to-end multi-role permission segregation |
| 6 | Base API Infrastructure | M1 | CORS headers, request ID propagation, global error handler, /health | Giant request headers, non-JSON body on JSON route, null payloads | CORS preflight with invalid origin + auth token | Global gateway fault & recovery |
| 7 | Base Frontend Shell | M1 | Health probe on UI route, auth route rendering, metadata tags | 404 page navigation, invalid deep-links | Auth state persistence across browser reload | Candidate initial launch & login |
| 8 | Exam CRUD & Management | M2 | Create, read, update, delete exam configurations; duration & timing | Negative duration, end time before start time, 0 late tolerance | Overlapping exam windows for same batch | Institution admin semester exam setup |
| 9 | Question Bank Management | M2 | Question creation, category tags, difficulty rating, options schema | 100k character question text, zero options, duplicate tags | Batch question upload with mixed types | Multi-course question bank authoring |
| 10 | Standard Question Types | M2 | MCQ single/multi, Short Answer, Long Essay with rubrics | All wrong MCQ options, empty essay text, HTML tags in short answer | Question re-ordering mid-exam | Comprehensive general knowledge exam |
| 11 | Candidate Enrollment & Scheduling | M2 | Enroll student by ID/email, generate access codes, enforce time windows | Access code reuse, pre-start launch attempt, post-window launch | Bulk enrollment (500 candidates) + instant launch | University entrance exam cohort scheduling |
| 12 | Candidate Exam Portal | M2 | Launch check, system readiness verification, camera/mic checks | Missing permissions payload, unsupported browser user-agent | Readiness check failure followed by retry pass | First-time candidate check-in experience |
| 13 | Exam Taking Interface | M2 | Navigation palette, flag question for review, progress counters | Rapid next/prev skipping, jumping to out-of-bound question index | Flagging all questions + bulk unflagging | 3-hour certification exam taking flow |
| 14 | Client-Side Auto-Save | M2 | Periodic/debounced answer save endpoint, sequence numbering | Save replay with stale sequence number, concurrent answer saves | Auto-save during network jitter | Intermittent connectivity exam session |
| 15 | Exam Timer & Auto-Submit | M2 | Server-side time enforcement, countdown sync, auto-submit on timeout | Clock skew in client timestamp, submit at t=0.001s past cutoff | Late auto-save arriving after auto-submit | Timed speed test with hard cutoff |
| 16 | Browser Telemetry Interception | M3 | Window blur/focus, fullscreen exit, paste, devtools detection events | Rapid 50x blur events/sec, negative timestamp deltas | Telemetry flood combined with answer save | Student attempting dual-screen lookup |
| 17 | Webcam Media Capture | M3 | Frame snapshot upload endpoint, rate configuration validation | Truncated JPEG data, 0-byte upload, 50MB oversized frame | Media capture upload failure + retry queue | Full video proctoring session capture |
| 18 | Computer Vision Detection Service | M3 | Face presence, multiple faces, cell phone detection event triggers | Pitch black frame, extreme glare, side profile angles | Multiple faces + phone detected simultaneously | Real-world proctored room anomalies |
| 19 | Real-Time Risk Engine | M3 | Event weight accumulation, Low/Med/High/Critical tier calculation | Weight overflow, negative event weight injection | Rapid succession of low-weight vs single high-weight | Escalating cheating behavior session |
| 20 | WebSocket Telemetry Stream | M3 | Real-time event push to proctor room, connection handshake, auth | Dropped WS frame, unauthenticated socket connection, ping timeout | 100 simultaneous proctor WS client connections | Live proctor center monitoring 200 candidates |
| 21 | Proctor Live Dashboard | M3 | Active sessions grid, real-time risk badge updates via WS | 0 active sessions, 500 active sessions pagination | Filter by risk level while candidates transition tiers | Multi-room proctor supervisory watch |
| 22 | Review Center & Evidence Viewer | M3 | Flagged session queue, timeline scrubber data, bounding box metadata | Corrupted snapshot URI, empty evidence list | Concurrent reviewer access to same flagged session | Post-exam forensic evidence investigation |
| 23 | Human Reviewer Workflow | M3 | Dismiss flag, escalate to disciplinary, record formal finding | Empty finding justification text, double-submission of verdict | Reviewer verdict conflict resolution | Disciplinary committee audit review |
| 24 | Exam Reporting & CSV Export | M3 | Score card generation, integrity summary, CSV & PDF export formats | Special characters (CSV injection `=cmd|'`) in candidate names | Exporting empty exam vs 10,000 candidate exam | Academic dean semester integrity audit |
| 25 | Demo Data Seeding Script | M3 | Execution of seed_demo_data.py, verifications of seeded entities | Re-running seed script on existing database (idempotency) | Seeding during active database connections | Local developer environment bootstrap |
| 26 | Monaco Code Editor Integration | M4 | Language config retrieval (Python, JS, etc.), editor theme options | Unsupported language request, 1MB source code payload | Switching language selector mid-question | Software engineer technical assessment |
| 27 | Sandboxed Code Execution Worker | M4 | Zero-network enforcement (`--net=none`), CPU/memory/time limit kills | Fork bomb (`os.fork()`), memory exhaustion, infinite loop | Worker restart during job queue processing | Malicious code sandbox containment |
| 28 | Visible & Hidden Test Case Runner | M4 | Visible test feedback during exam, hidden test results suppressed | Missing stdin, infinite output stream, partial output match | Visible tests pass, all hidden tests fail | Data structures & algorithms problem |
| 29 | Autograding Engine | M4 | Weighted test scoring, runtime error parsing, wall-clock telemetry | Float division by zero, non-zero exit codes, syntax errors | Partial credit scoring with custom weights | CS101 midterm programming autograde |
| 30 | Large Paste Detection | M4 | >10 line paste detection, editor diffing, risk signal emission | 9-line paste (below threshold) vs 11-line paste, paste of spaces | Large paste followed immediately by editor clear | Candidate pasting ChatGPT solution |
| 31 | Typing Cadence Analysis | M4 | Keystroke interval delta tracking, burstiness & uniformity scoring | Constant 1ms keystrokes (bot macro), 60s idle then burst | Typing cadence signal + large paste correlation | Keystroke biometric anomaly detection |
| 32 | MOSS-Style Token Similarity | M4 | Tokenized k-gram winnowing algorithm, cross-submission matrix | Variable renaming, re-ordered independent functions | 100% identical submissions vs slight boilerplate overlap | Batch plagiarism check across cohort |
| 33 | Pre-Publish Test Case Validation | M4 | Blocking validation: test cases must pass against reference solution | Reference solution timeout, incorrect expected output | Complex edge case test suite validation | Instructor publishing flawed exam question |
| 34 | Live WebRTC Video Room | M4 | Room creation, JWT token generation, participant connection state | Expired room token, candidate joins wrong room ID | Reconnection after network interface switch | Live 1-on-1 technical interview |
| 35 | Interview Question Script UI | M4 | Synchronized question script view, interviewer note-taking | Empty script, out-of-order question advance | Multiple interviewers viewing same script | Panel interview structured questioning |
| 36 | Rubric-Based Panel Scoring | M4 | Criterion-based scoring sliders, rubric weight calculations | Score outside rubric min/max bounds, non-numeric scores | Partial rubric completion submission | Standardized competency rubric scoring |
| 37 | Multi-Panelist Independent Scoring | M4 | Panelist isolation (blind scoring), score aggregation (mean/median) | 1 panelist gives 0, 1 gives 100; missing panelist score | Panelist modifying score after consensus reveal | High-stakes executive hiring panel |
| 38 | Async Interview Mode | M4 | Timed video/audio response recording, preset question countdown | Upload interruption mid-video, response exceeding time limit | Re-recording attempts within allowed limit | Asynchronous graduate admissions interview |
| 39 | Whisper Transcription Pipeline | M4 | Audio file ingestion, time-aligned speech-to-text transcription | Silent audio file, extreme background noise, overlapping speech | Long 30-minute interview transcription chunking | Automated transcript indexing for review |
| 40 | Clickable Transcript Highlights | M4 | Word-level timestamp linkage, pause/filler density markers | Zero words detected, transcript offset past media duration | Seeking video player to transcript highlight | Quick navigation to candidate answer pause |
| 41 | Interview Screen-Share Detection | M4 | WebRTC track inspection, unauthorized screen-share alert | Screen-share toggled rapidly on/off, audio-only share | Screen-share alert + multi-face detection | Unauthorized presentation sharing in interview |
| 42 | 2PL IRT Adaptive Engine | M5 | 2-parameter logistic model ($\hat{\theta}$ update based on $a, b$) | Extreme discrimination ($a=5.0$), extreme difficulty ($b=\pm 4.0$) | Candidate with all correct vs all incorrect streak | Computerized Adaptive Testing (CAT) exam |
| 43 | Fisher Information Item Selection | M5 | Selection of next question maximizing $I(\theta)$ at current $\hat{\theta}$ | Empty remaining item pool, identical information items | Shift in ability estimate after surprising mistake | Optimal item selection during GRE-style test |
| 44 | Ability Confidence Intervals | M5 | Standard error calculation ($\hat{\theta} \pm z \cdot \text{SE}$), stopping rule | SE divergence on inconsistent response pattern | Target SE reached in 15 items vs max 40 items | High-precision medical certification exam |
| 45 | Diagram Labeling Question Type | M5 | Coordinate hotspot validation, click target placement with tolerance | Click at exact boundary edge, negative coordinate click | Multiple targets with overlapping tolerance circles | Anatomy diagram labeling test |
| 46 | Whiteboard Question Type | M5 | Vector canvas stroke serialization, coordinate stream validation | 100,000 vector points, 0 strokes, out-of-canvas points | Clear canvas followed by rapid drawing | System architecture design whiteboard exam |
| 47 | Audio Response Question Type | M5 | Audio blob upload, duration bounds check, waveform playback metadata | Exceeding max duration, corrupted audio header, 0-byte audio | Audio response alongside text notes | Oral language proficiency assessment |
| 48 | Offline Resilience via IndexedDB | M5 | Offline state sync endpoint, conflict resolution (last-write-wins) | Replay of 100 offline actions in batch, conflicting timestamps | Prolonged 15-minute outage then burst reconnection | Remote candidate with unstable rural Wi-Fi |
| 49 | LMS Connector / LTI 1.3 | M5 | LTI 1.3 OIDC launch handshake, NRPS roster sync, AGS grade push | Expired state parameter, tampered LTI launch signature | Bulk grade push with 500 grades | Canvas / Blackboard integrated exam launch |
| 50 | Enterprise SSO Integration | M5 | SAML2 / OAuth2 / OIDC auth flow, JIT user provisioning | Expired SAML assertion, missing required claims (email/name) | SSO user logging in via local password form | Corporate Okta/AzureAD SSO login |
| 51 | Mobile Exam Mode | Honest capability disclosure, responsive profile tag, signal restrictions | User-agent spoofing, orientation change event handling | Mobile session telemetry vs desktop session telemetry | Candidate taking exam on iPad or Android tablet |
| 52 | Versioned Consent Capture | M6 | Multi-point consent (webcam, mic, screen, retention), version audit | Declining mandatory consent point, tampered consent version ID | Consent revocation post-exam | GDPR/FERPA compliant pre-exam onboarding |
| 53 | Data Retention & Deletion Engine | M6 | Scheduled deletion job, retention policy rules, anonymization | Retention period 0 days, retention period 10 years | Deletion job running while session is actively being reviewed | Automated privacy compliance purge |
| 54 | Student Appeals Flow | M6 | Appeal contestation submission, reviewer role separation enforcement | Submitting appeal after deadline, assigning same reviewer | Appeal approval overturning review finding & score | Contested autograder decision appeal |
| 55 | WCAG 2.1 AA Accessibility | M6 | ARIA attributes, keyboard tab order, high contrast support verification | Keyboard trap in editor/modal, missing alt attributes | Screen reader navigation during timed test | Visually impaired candidate exam taking |
| 56 | CI/CD GitHub Actions Pipeline | M6 | Workflow definition validation, linting/test/build job triggers | Broken test blocking PR merge, secret leakage detection | Multi-job matrix build (Ubuntu, Node, Python) | Automated regression prevention gate |
| 57 | Structured Logging & Tracing | M6 | Structlog JSON format, correlation ID (X-Request-ID) propagation | Missing request ID in header, nested exception stack trace | Correlation ID traced from HTTP to WS to worker | Distributed debugging of anomalous session |
| 58 | Prometheus Metrics & Alerting | M6 | `/metrics` endpoint, queue depth counter, WS active connections | Metric counter reset, metric scrape timeout | High queue depth triggering alert threshold | Datadog/Prometheus production monitoring |
| 59 | k6 / Locust Load Testing Scripts | M6 | Execution of load script, simulated exam-start thundering herd | Ramp up 10 to 500 VUs in 60s, breaking point detection | Concurrent logins + concurrent answer saves | 1,000 student simultaneous university final |
| 60 | Backup & DR Restore Drill Script | M6 | Database dump execution, restore drill verification, recovery time | Corrupted backup file restore, restore to existing DB | Point-in-time recovery during active load | Disaster recovery failover drill |
| 61 | VPN & Proxy Detection | M6 | IP intelligence classification, low-weight risk signal emission | Datacenter IP, residential proxy, IPv6 address | VPN flag emitted WITHOUT auto-blocking student | Candidate taking exam over NordVPN |
| 62 | Multi-Device & Multi-Tab Detection | M6 | Active session collision detection, alert emission, no auto-block | Rapid tab switching, simultaneous logins on 2 IPs | Multi-tab alert + copy-paste risk escalation | Candidate attempting collaboration across devices |
| 63 | Question-Leak Detection | M6 | Text fingerprinting, batch comparison vs leak database | 100% exact text match, paraphrased question text | Question bank leak check across past 5 years | Post-exam integrity scan for public leaks |
| 64 | Cost & Usage Metering | M6 | Tracking sandbox-seconds, video-minutes, transcription-minutes | Negative usage delta, zero duration usage event | Multi-tenant usage aggregation under concurrent load | Monthly cloud resource billing audit |
| 65 | Budget Alerts & Non-Interruptive Throttling | M6 | Warning at 80%, throttle at 100%, in-progress exam immunity | Budget limit set to $0, negative budget | New launch blocked while existing exam completes | Institution exceeding monthly compute allocation |
| 66 | Notification Service | M6 | Email/SMS dispatch endpoint, template rendering, delivery logs | Invalid email/phone syntax, SMTP timeout | 500 exam reminders queued at once | Exam schedule reminder & appeal notification |
| 67 | Calendar Integration | M6 | `.ics` file generation, Google Calendar / Outlook payload schema | Timezone boundary conditions, leap year dates, DST shift | Interview rescheduled across timezones | Candidate importing interview into Google Calendar |
| 68 | Opaque-Box E2E Test Suite (Tiers 1-4) | M7 | Full test suite execution across all domains, report generation | Network drop during test run, slow endpoint latency | Full matrix execution across all 4 tiers | Final platform acceptance gate |
| 69 | Adversarial Coverage Hardening (Tier 5) | M7 | White-box stress tests, race conditions, forensic tampering audit | Signature forgery, timestamp manipulation, replay attack | End-to-end multi-vector attack simulation | High-security government certification audit |

---

## 3. Test Architecture & Runner Design

### 3.1 Directory Layout
```
e2e-tests/
├── runner.py                        # Unified CLI test runner
├── client.py                        # Opaque-box HTTP & WebSocket client
├── config.py                        # Centralized test configuration
├── requirements.txt                 # Dependencies
├── tier1_feature_coverage/          # Tier 1: Feature Coverage (>=5 tests/feature)
│   ├── __init__.py
│   ├── test_m1_auth_foundation.py   # Features 1–7
│   ├── test_m2_exam_engine.py       # Features 8–15
│   ├── test_m3_telemetry_risk.py    # Features 16–25
│   ├── test_m4_coding_interview.py  # Features 26–41
│   ├── test_m5_adaptive_digital.py  # Features 42–51
│   └── test_m6_compliance_ops.py    # Features 52–67
├── tier2_boundary_corner/           # Tier 2: Boundary & Corner Cases (>=5 tests/feature)
│   ├── __init__.py
│   ├── test_b1_auth_security.py     # Auth boundaries & malicious inputs
│   ├── test_b2_exam_timer_limits.py # Time limits, oversized payloads, negative bounds
│   ├── test_b3_telemetry_floods.py  # Telemetry storms, invalid coordinates, corrupted media
│   ├── test_b4_sandbox_attacks.py   # Fork bombs, resource exhaustion, zero network
│   ├── test_b5_adaptive_extremes.py # Extreme IRT discrimination/difficulty, cold starts
│   └── test_b6_compliance_edge.py   # Strict role separation, retention boundaries, quota edges
├── tier3_pairwise_interactions/     # Tier 3: Multi-feature pairwise combinatorics
│   └── __init__.py
└── tier4_real_world_workloads/      # Tier 4: Realistic end-to-end application scenarios
    └── __init__.py
```

### 3.2 Runner CLI Specification
```bash
python e2e-tests/runner.py [OPTIONS]

Options:
  --tier {1,2,3,4,all}     Test tier to execute (default: all)
  --domain {auth,exam,telemetry,coding,interview,adaptive,compliance,ops,all} Filter by domain
  --base-url URL           Base URL of backend API (default: http://localhost:8000)
  --ws-url URL             Base WebSocket URL (default: ws://localhost:8000)
  --verbose, -v            Detailed per-test output
  --json-report FILE       Export test execution results to JSON artifact
  --dry-run                Verify discovery, test counts, and contract schemas without executing network calls
  --help                   Display help and usage details
```

### 3.3 Exit Codes
- `0`: All executed tests passed cleanly.
- `1`: One or more test assertions failed (implementation defect detected).
- `2`: Configuration, environment, or connection error.

---

## 4. Coverage Thresholds & Integrity Guardrails

### 4.1 Strict Minimum Thresholds
- **Tier 1 (Feature Coverage)**: $\ge 5$ explicit behavioral tests per feature.
- **Tier 2 (Boundary & Corner Cases)**: $\ge 5$ boundary/stress cases for every feature exposing external parameters.
- **Tier 3 (Pairwise Interactions)**: Minimum 10 cross-feature combinatorial matrices.
- **Tier 4 (Real-World Application Scenarios)**: Minimum 5 complete end-to-end lifecycles.

### 4.2 Non-Negotiable Integrity Invariants
1. **No Automated Guilt**: Telemetry events, VPN flags, paste signals, and AI detections MUST never transition session status to "TERMINATED" or "FAILED" automatically. They MUST calculate risk and populate reviewer queues.
2. **Reviewer Role Separation**: In any student appeal, the resolving reviewer ID MUST strictly differ from the reviewer who recorded the initial finding.
3. **No Student Work Lost**: Auto-save and offline sync mechanisms must guarantee that disconnected sessions preserve submitted answers up to the last network or local save point.
4. **Sandboxed Isolation**: Sandboxed code execution must strictly enforce zero outbound network access and respect CPU/memory/time bounds.
5. **No Vacuous Assertions**: Every test must evaluate a real contract response or state transformation.

---

## 5. Real-World Application Scenarios (Tier 4 Catalog)

1. **Scenario 1: High-Stakes University Final (Core Exam Lifecycle)**
   - Admin creates 50-question mixed exam (MCQ, Short, Essay) with 60-minute limit.
   - 50 Candidates authenticate, agree to versioned consent, and launch simultaneously.
   - Candidate A triggers window blur, devtools open, and periodic webcam snapshots.
   - Risk engine accumulates score to "HIGH"; proctor live dashboard updates badge to red.
   - Exam timer expires; auto-submit triggers; session transitions to "SUBMITTED".
   - Reviewer opens evidence gallery, inspects snapshots with bounding boxes, dismisses or confirms finding.

2. **Scenario 2: Technical Software Engineering Assessment (Coding Track)**
   - Candidate launches coding challenge (Python & JavaScript).
   - Candidate writes solution in Monaco editor; runs visible test cases with live pass/fail output.
   - Candidate attempts large paste (>10 lines); paste detection fires and emits signal to risk engine.
   - Final submission runs against hidden test cases in zero-network sandbox.
   - Weighted autograder calculates score; post-exam MOSS token similarity runs cross-cohort check.

3. **Scenario 3: Multi-Panelist Synchronized Interview (Live & Async)**
   - Candidate and 2 Interviewers join WebRTC video room.
   - Interviewers follow synchronized question script and score on rubric sliders independently.
   - Candidate records async response; Whisper transcription produces time-aligned transcript.
   - Reviewer navigates to pauses via clickable transcript highlights; consensus score is aggregated.

4. **Scenario 4: Adaptive Graduate Certification (2PL IRT CAT)**
   - Candidate begins adaptive exam at baseline ability estimate $\hat{\theta} = 0.0$.
   - First question presented; candidate answers correctly; IRT engine recalculates $\hat{\theta} = +0.65$.
   - Next item chosen by maximizing Fisher Information $I(\theta)$; confidence interval tightens.
   - Network disconnects mid-exam; client IndexedDB buffers answers; reconnect replays without data loss.
   - Final ability score reported with 95% confidence interval ($\hat{\theta} \pm 1.96 \cdot \text{SE}$).

5. **Scenario 5: Contested Finding & Institutional Governance (Compliance & Appeals)**
   - Reviewer records misconduct finding on candidate session based on phone detection flag.
   - Candidate receives notification and submits formal appeal with explanatory statement.
   - System assigns distinct appeal reviewer; original reviewer is prevented from adjudication.
   - Appeal reviewer evaluates frozen evidence snapshot and grants appeal; grade restored.
   - Scheduled retention job executes; past-retention telemetry purged; audit log retained.
