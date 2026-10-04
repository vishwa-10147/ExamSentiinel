# ExamSentinel — Survey & Specification Report: Phases 15–20
**Author**: `explorer_survey_3`  
**Date**: 2026-09-16T10:50:00Z  
**Source Document**: `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`  
**Scope**: Digital Exam Extensions (Phases 15–16), Compliance & Legal (Phase 17), Reliability & Operations (Phase 18), Security Hardening (Phase 19), Cost Governance & Polish (Phase 20)

---

## 1. Executive Summary & Problem Boundary

This specification report establishes the definitive technical requirements, mathematical formulations, algorithms, database schemas, API contracts, failure modes, and edge cases for **Phases 15 through 20** of ExamSentinel.

These phases expand ExamSentinel from a core proctored examination and coding/interview platform into an enterprise-grade, resilient, legally compliant, observable, hardened, and cost-controlled assessment system:
1. **Phases 15–16 (Digital Exam Extensions)**: 2PL Item Response Theory (IRT) adaptive testing, multi-modal question types (diagram labeling, stroke-replay whiteboard, audio response), IndexedDB offline resilience, LTI 1.3 LMS connectors, SAML2/OAuth2 SSO, and mobile exam mode.
2. **Phase 17 (Compliance & Legal)**: Versioned multi-point consent capture, automated per-institution data retention & deletion, independent student appeals workflow, and WCAG 2.1 AA accessibility auditing.
3. **Phase 18 (Reliability & Operations)**: GitHub Actions CI/CD gating, structlog structured logging, Prometheus/Grafana alerting, k6/Locust thundering herd load testing, and verified backup/DR restore drills.
4. **Phase 19 (Security Hardening)**: VPN/proxy detection without auto-blocking, multi-device/multi-tab session collision detection, WebRTC interview screen-share detection, and question-leak batch comparison.
5. **Phase 20 (Cost Governance & Polish)**: Institutional usage metering (sandbox, video, transcription minutes) with non-interruptive throttling, transactional notifications (Email/SMS), calendar integrations (Google/Outlook/iCal), and autograder pre-publish validation gates.

---

## 2. Phase 15 — Adaptive & Multi-Modal Digital Exams

### 2.1 2PL Item Response Theory (IRT) Adaptive Testing System

#### 2.1.1 Mathematical Formulation
The adaptive testing engine models the probability that a student with latent ability $\theta$ correctly answers item $i$:

$$P_i(\theta) \equiv P(u_i = 1 \mid \theta, a_i, b_i) = \frac{1}{1 + \exp\left(-D \cdot a_i \cdot (\theta - b_i)\right)}$$

- $\theta \in (-\infty, \infty)$: Student latent ability parameter (standard scale: $\theta \sim \mathcal{N}(0, 1)$, typical range $[-3.0, +3.0]$).
- $b_i \in (-\infty, \infty)$: Item difficulty parameter. Represents ability level where probability of correct response is $0.50$.
- $a_i > 0$: Item discrimination parameter. Determines the steepness of the Item Characteristic Curve (ICC) at $\theta = b_i$. Typical operational values $0.5 \le a_i \le 2.5$.
- $D = 1.702$: Conventional scaling constant aligning the logistic metric to the normal ogive metric.
- $u_i \in \{0, 1\}$: Binary scored response ($1 = \text{correct}, 0 = \text{incorrect}$).

#### 2.1.2 Ability Estimation Update ($\hat{\theta}$)
Given a set of $k$ administered items with response vector $\mathbf{u} = [u_1, u_2, \dots, u_k]^T$:
1. **Likelihood Function**:
   $$L(\theta \mid \mathbf{u}) = \prod_{i=1}^k P_i(\theta)^{u_i} \left[1 - P_i(\theta)\right]^{1 - u_i}$$
2. **Log-Likelihood Function**:
   $$\ell(\theta) = \ln L(\theta \mid \mathbf{u}) = \sum_{i=1}^k \left[ u_i \ln P_i(\theta) + (1 - u_i) \ln (1 - P_i(\theta)) \right]$$
3. **First and Second Derivatives**:
   $$\ell'(\theta) = \frac{\partial \ell}{\partial \theta} = D \sum_{i=1}^k a_i \left(u_i - P_i(\theta)\right)$$
   $$\ell''(\theta) = \frac{\partial^2 \ell}{\partial \theta^2} = -D^2 \sum_{i=1}^k a_i^2 P_i(\theta) \left(1 - P_i(\theta)\right)$$

4. **Maximum A Posteriori (MAP) Estimation (Bayesian Guard against Cold Start)**:
   *Cold-Start Problem*: If a student answers all initial items correctly ($u_i=1 \ \forall i$) or incorrectly ($u_i=0 \ \forall i$), Maximum Likelihood Estimation (MLE) diverges to $\pm \infty$.
   *MAP Solution*: Place an informative prior $\theta \sim \mathcal{N}(\mu_0, \sigma_0^2)$, standard prior $\mu_0 = 0.0, \sigma_0^2 = 1.0$:
   $$\ell_{\text{MAP}}(\theta) = \ell(\theta) - \frac{(\theta - \mu_0)^2}{2 \sigma_0^2}$$
   $$\ell'_{\text{MAP}}(\theta) = D \sum_{i=1}^k a_i \left(u_i - P_i(\theta)\right) - \frac{\theta - \mu_0}{\sigma_0^2}$$
   $$\ell''_{\text{MAP}}(\theta) = -D^2 \sum_{i=1}^k a_i^2 P_i(\theta) \left(1 - P_i(\theta)\right) - \frac{1}{\sigma_0^2}$$

   Newton-Raphson Iteration:
   $$\theta^{(t+1)} = \theta^{(t)} - \frac{\ell'_{\text{MAP}}\left(\theta^{(t)}\right)}{\ell''_{\text{MAP}}\left(\theta^{(t)}\right)}$$
   Iterate until $|\theta^{(t+1)} - \theta^{(t)}| < 10^{-4}$ or max 25 iterations. Clamp $\theta \in [-4.0, 4.0]$.

#### 2.1.3 Fisher Information & Next-Item Selection
1. **Item Information Function (IIF)**:
   $$I_i(\theta) = D^2 \cdot a_i^2 \cdot P_i(\theta) \cdot (1 - P_i(\theta))$$
   Note: $I_i(\theta)$ attains its theoretical maximum when $\theta = b_i$, where $I_i(b_i) = \frac{D^2 a_i^2}{4}$.
2. **Next-Item Selection Algorithm (Maximum Fisher Information - MFI)**:
   Given current ability estimate $\hat{\theta}_k$ and unadministered item pool $\mathcal{Q}_{\text{avail}}$:
   $$i^* = \arg\max_{i \in \mathcal{Q}_{\text{avail}}} I_i(\hat{\theta}_k)$$
   *Content Balancing & Exposure Control*: To prevent item overexposure, candidate items within top $\epsilon = 5\%$ information can be randomly sampled (modified Sympson-Hetter rule) while satisfying topic category constraints.

#### 2.1.4 Standard Error & Confidence Intervals
1. **Standard Error of Measurement (SEM)**:
   $$\text{SE}(\hat{\theta}) = \frac{1}{\sqrt{-\ell''_{\text{MAP}}(\hat{\theta})}} = \frac{1}{\sqrt{D^2 \sum_{i=1}^k a_i^2 P_i(\hat{\theta})(1 - P_i(\hat{\theta})) + \frac{1}{\sigma_0^2}}}$$
2. **Confidence Interval (95% CI)**:
   $$\text{CI}_{95\%} = \left[ \hat{\theta} - z_{\alpha/2} \cdot \text{SE}(\hat{\theta}),\ \hat{\theta} + z_{\alpha/2} \cdot \text{SE}(\hat{\theta}) \right] = \left[ \hat{\theta} - 1.96 \cdot \text{SE}(\hat{\theta}),\ \hat{\theta} + 1.96 \cdot \text{SE}(\hat{\theta}) \right]$$
3. **Reporting Requirement**: Reporting must display $\hat{\theta}$, $\text{SE}(\hat{\theta})$, and the $95\%$ confidence bounds alongside standard scaled score (e.g. 200–800 or percentage equivalent).

#### 2.1.5 Termination Criteria
An adaptive exam terminates when ANY of the following conditions is met:
1. **Standard Error Threshold**: $\text{SE}(\hat{\theta}) \le \text{SE}_{\text{target}}$ (default $\text{SE}_{\text{target}} = 0.30$, corresponding to test reliability $\rho \approx 1 - \text{SE}^2 = 0.91$).
2. **Maximum Item Count**: $k \ge K_{\max}$ (default $K_{\max} = 30$).
3. **Minimum Item Count Guard**: Testing must NOT terminate before $k \ge K_{\min}$ (default $K_{\min} = 10$) regardless of SE.
4. **Time Window Limit**: Scheduled exam duration elapsed.
5. **Item Bank Exhaustion**: No remaining eligible items in the pool satisfying constraints.

---

### 2.2 Diagram Labeling Question Type

- **Concept**: Student labels specific parts of a schematic, biological diagram, or architectural layout.
- **Specification**:
  - `background_image_url`: URI to high-resolution base image.
  - `canvas_dimensions`: `{ "width": number, "height": number }`.
  - `target_zones`: Array of target zones:
    - `id`: UUID
    - `center_x`: Float (pixel coordinate relative to origin)
    - `center_y`: Float
    - `shape`: `"circle"` | `"rect"`
    - `radius`: Float (if circle) or `width`, `height` (if rect)
    - `tolerance_px`: Maximum acceptable Euclidean distance error (default 15px).
    - `correct_label_id`: UUID
  - `label_bank`: List of draggable/selectable text or image tokens.
- **Answer Submission Schema**:
  ```json
  {
    "question_id": "uuid",
    "placements": [
      {
        "target_zone_id": "zone-1",
        "label_id": "label-mitochondria",
        "drop_x": 245.5,
        "drop_y": 180.2,
        "timestamp_ms": 1420
      }
    ]
  }
  ```
- **Scoring Logic**:
  - For each target zone $j$, placement is valid if $\sqrt{(x_{\text{drop}} - x_j)^2 + (y_{\text{drop}} - y_j)^2} \le \text{tolerance\_px}$ AND `placed_label_id` matches `correct_label_id`.
  - Supports full credit and partial credit weighting.

---

### 2.3 Whiteboard Question Type with Stroke Recording & Playback

- **Concept**: Candidate illustrates freehand diagrams, mathematical derivations, or system architectures on an HTML5 canvas.
- **Stroke Data Vector Schema**:
  Strokes are recorded in vector format with millisecond timestamps to allow full replay:
  ```json
  {
    "canvas_version": 1,
    "canvas_dimensions": { "width": 1200, "height": 800 },
    "strokes": [
      {
        "stroke_id": "stk_001",
        "tool": "pen",
        "color": "#1e293b",
        "size": 3,
        "points": [
          { "x": 120, "y": 80, "t_ms": 0, "pressure": 0.5 },
          { "x": 125, "y": 84, "t_ms": 16, "pressure": 0.55 },
          { "x": 135, "y": 92, "t_ms": 32, "pressure": 0.6 }
        ]
      }
    ],
    "duration_total_ms": 45000,
    "thumbnail_png_url": "s3://exam-sentinel/whiteboards/session-1/thumb.png"
  }
  ```
- **Reviewer Playback Engine**:
  - Review Center UI provides video-like playback scrub bar: Play, Pause, Scrub timeline, Speed (0.5x, 1x, 2x, 5x).
  - Integrity Signal: Detects sudden unnatural paste/dump of vector strokes (e.g. 500 strokes appearing in <100ms) and flags as `SUSPICIOUS_WHITEBOARD_INJECTION`.

---

### 2.4 Audio Response Question Type

- **Concept**: Spoken oral exam responses (language oral test, conceptual explanation, behavioral prompt).
- **Client Pipeline**:
  - In-browser capture via Web MediaStream Recording API (`MediaRecorder`).
  - Audio codec: Opus in WebM container (`audio/webm;codecs=opus`) with 48kHz sample rate.
  - UI provides real-time AudioContext AnalyserNode visual waveform oscilloscope / amplitude meter.
  - Student controls: Record, Pause, Re-record (if permitted), Preview Playback, Submit.
- **Backend Pipeline**:
  - File upload via chunked multipart upload.
  - Normalization via FFmpeg to 16kHz mono WAV.
  - Automatic Speech-to-Text (STT) via Whisper-class model, outputting time-aligned transcript with word-level confidence scores.
  - Human review interface displays audio player synchronized with clickable transcript highlights.

---

## 3. Phase 16 — Platform Resilience & Integrations

### 3.1 Offline Resilience via IndexedDB Sync Queue-and-Replay

#### 3.1.1 Local IndexedDB Architecture
- Database Name: `ExamSentinelClientDB`
- Object Stores:
  1. `exam_metadata`: Cached exam structure, question list, media assets, timing configurations.
  2. `answers_draft`: Key-value store of latest local answer drafts per `question_id`.
  3. `sync_queue`: Ordered log of unsynced operations:
     ```typescript
     interface QueuedSyncItem {
       queue_id: number; // auto-increment
       action: "SAVE_ANSWER" | "FLAG_QUESTION" | "HEARTBEAT" | "PROCTOR_EVENT";
       payload: any;
       client_timestamp: string; // ISO 8601 UTC
       retry_count: number;
       status: "pending" | "syncing" | "failed";
     }
     ```
  4. `proctoring_buffer`: Local telemetry (tab blur, mouse leave, camera heartbeats) buffered during network loss.

#### 3.1.2 Sync Replay Protocol & Conflict Resolution
1. **Network Status Detection**: Monitored via `window.navigator.onLine`, WebSocket ping/pong timeouts (<5s), and failed HTTP POST retries.
2. **Offline Experience**:
   - Prominent non-intrusive alert: `"Network disconnected. Your answers are being safely saved locally on this device. Do not close this tab."`
   - Exam timer continues monotonically based on authenticated server start/end timestamps.
3. **Reconnect & Queue Replay**:
   - Reconnection triggers queue processing:
     `POST /api/exam/sessions/{session_id}/sync-replay`
   - Payload contains chronologically sorted array of `QueuedSyncItem`.
4. **Conflict Resolution Strategy**:
   - **Last-Write-Wins (LWW)** based on client timestamp within verified exam window.
   - If client timestamp exceeds exam submission deadline by more than configurable grace window (e.g. 60 seconds), answer is accepted into staging with `LATE_OFFLINE_SYNC` flag and routed to reviewer.
   - Non-negotiable constraint: **Never silently drop student work.**
5. **Risk Signal Emission**:
   - Total disconnect duration and count are calculated.
   - Disconnects lasting $> 30\text{s}$ emit `NETWORK_DISCONNECT` signal to risk engine with duration and time-of-occurrence metadata.

---

### 3.2 LMS Connector / LTI 1.3 Integration

#### 3.2.1 Standard & Architecture
ExamSentinel implements 1EdTech LTI 1.3 (LTI Advantage) Core:
1. **Security Framework**: OpenID Connect (OIDC) Third-Party Launch and OAuth 2.0 Client Credentials with asymmetric JWTs (RSA-SHA256 with public JWKS).
2. **Names and Role Provisioning Services (NRPS 2.0)**:
   - Endpoint: `POST /api/lti/sync-roster/{exam_id}`
   - Queries LMS course membership endpoint using scoped access token.
   - Automatically provisions student accounts and exam enrollments with mapped LMS user IDs.
3. **Assignment and Grade Services (AGS 2.0)**:
   - Endpoint: `POST /api/lti/push-grades/{exam_id}`
   - Once exam reviews are finalized, pushes normalized scores ($0.0 \dots 1.0$), max score, grading comments, and completion timestamp to LMS LineItem container.
4. **Supported LMS Platforms**: Moodle, Canvas, Blackboard Learn, D2L Brightspace.

---

### 3.3 Enterprise Single Sign-On (SSO)

#### 3.3.1 SAML 2.0 Integration
- **Service Provider (SP) Metadata**: `GET /api/auth/sso/saml/metadata.xml`
- **Assertion Consumer Service (ACS)**: `POST /api/auth/sso/saml/acs`
- Validations:
  - Verify IdP XML digital signature using institution's registered X.509 certificate.
  - Validate SAML conditions: `NotBefore`, `NotOnOrAfter`, `AudienceRestriction` matching SP EntityID.
  - Extract and map user attributes: `eduPersonPrincipalName`, email, firstName, lastName, institutional roles.
- Issuance: Generates native ExamSentinel JWT session token with mapped institutional role.

#### 3.3.2 OAuth 2.0 / OIDC Integration
- Standard Authorization Code Grant with PKCE.
- Compatible with Google Workspace, Microsoft Entra ID (Azure AD), Okta, PingFederate.
- Endpoints: `GET /api/auth/sso/oidc/authorize`, `GET /api/auth/sso/oidc/callback`.

---

### 3.4 Mobile Exam Mode with Honest Capability Disclosure

- **Responsive Viewport**: Optimized layout for touch screens, scaled canvas, and compact question navigation.
- **Non-Negotiable Constraint: No silent overclaiming of monitoring capability.**
- **Honest Capability Disclosure Modal**:
  Before starting on mobile, student must review and acknowledge:
  - Fullscreen lock: Limited by OS; app-switching is detected via Page Visibility API only.
  - Peripheral detection: Multi-monitor and secondary keyboard detection **NOT supported** on mobile browsers.
  - Camera: Front-facing single camera supported; peripheral room view not available.
  - Audio: Single microphone stream supported.
- **Session Metadata Tagging**:
  - Exam session tagged with `client_platform: "mobile"`, `device_model`, `browser_engine`.
  - Admin Dashboard and Reviewer Queue display prominent tag: `[MOBILE - REDUCED MONITORING]`.
  - Risk engine dynamically adjusts expected detector signals (suppresses absence of multi-monitor signals while weighting `PAGE_VISIBILITY_HIDDEN` events).

---

## 4. Phase 17 — Compliance & Legal

### 4.1 Versioned Consent Capture & Audit Logging

#### 4.1.1 Multi-Point Consent Architecture
Consent must be obtained explicitly at each distinct data collection point:
1. `WEBCAM_MONITORING`: Periodic video snapshots and face detection.
2. `AUDIO_RECORDING`: Ambient microphone monitoring and audio response capture.
3. `KEYSTROKE_LOGGING`: Cadence, typing dynamics, and paste telemetry.
4. `SCREEN_CAPTURE`: Fullscreen tracking and window snapshot capture.
5. `BIOMETRIC_ANALYSIS`: Face mesh and gaze vector calculation.

#### 4.1.2 Versioned Notice Text & Schema
- Each consent document is version-controlled (e.g. `consent_notice_v2.1`).
- Exact verbatim text displayed to student is cryptographically hashed (SHA-256).
- Schema (`consent_records`):
  ```sql
  CREATE TABLE consent_records (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      student_id UUID NOT NULL REFERENCES users(id),
      institution_id UUID NOT NULL REFERENCES institutions(id),
      exam_id UUID REFERENCES exams(id),
      collection_point VARCHAR(64) NOT NULL,
      consent_version VARCHAR(32) NOT NULL,
      notice_text_hash VARCHAR(64) NOT NULL,
      notice_text TEXT NOT NULL,
      status VARCHAR(16) NOT NULL CHECK (status IN ('granted', 'declined', 'withdrawn')),
      ip_address VARCHAR(45) NOT NULL,
      user_agent TEXT NOT NULL,
      granted_at TIMESTAMPTZ,
      withdrawn_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );
  ```
- **Constraint**: If consent is declined or withdrawn, monitoring cannot activate; student is blocked from entering monitored sections with clear explanatory prompt.

---

### 4.2 Per-Institution Data Retention Policies & Scheduled Deletion

#### 4.2.1 Configurable Retention Rules
Institutions configure retention windows per data category via `data_retention_policies`:
- `SNAPSHOTS`: Default 30 days.
- `AUDIO_VIDEO_RECORDINGS`: Default 60 days.
- `TYPING_TELEMETRY`: Default 90 days.
- `SUBMISSION_CODE_AND_ANSWERS`: Default 365 days.
- `AUDIT_LOGS_AND_DECISIONS`: Default 730 days (or permanent).

#### 4.2.2 Automated Deletion & Anonymization Engine (`retention_service.py`)
- Scheduled batch worker running daily at 02:00 UTC.
- Deletion actions:
  1. **Binary Artifact Deletion**: Deletes image snapshots, audio blobs, and video chunks from S3/MinIO.
  2. **Database Anonymization**: Replaces identifiable student data (names, IP addresses, email) with irreversible hashes (`anonymized_student_uuid`) while preserving statistical test psychometrics and grading distributions.
- **Right-to-Deletion (GDPR Art. 17 / CCPA)**:
  - If a student or DPO files a deletion request, system verifies whether an open dispute or appeal is pending.
  - If pending: request is marked `SUSPENDED_LEGAL_HOLD`.
  - If clear: records are purged within 72 hours, and a cryptographic deletion certificate is generated.
- **Non-Negotiable Constraint**: **No silent deletion or silent retention.** Every deletion is recorded in `retention_deletion_jobs`.

---

### 4.3 Student Appeals Flow with Independent Reviewer Queue

#### 4.3.1 Contestability Lifecycle
Every consequential decision (misconduct penalty, autograder test case failure, interview panel rubric score) can be appealed by the student within an institutional window (e.g. 14 days).

#### 4.3.2 Strict Role Separation Guard
- **Inviolable Policy**: An appeal **CANNOT** be reviewed or adjudicated by the instructor, invigilator, or reviewer who issued the original finding or score.
- Appeals are routed exclusively to the **Independent Appeal Reviewer Queue**.

#### 4.3.3 Appeal Schemas & Audit Trail
```sql
CREATE TABLE appeal_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES exam_sessions(id),
    student_id UUID NOT NULL REFERENCES users(id),
    exam_id UUID NOT NULL REFERENCES exams(id),
    appeal_type VARCHAR(32) NOT NULL CHECK (appeal_type IN ('misconduct_finding', 'autograder_score', 'interview_rubric')),
    original_decision JSONB NOT NULL,
    original_reviewer_id UUID REFERENCES users(id),
    assigned_reviewer_id UUID REFERENCES users(id),
    student_justification TEXT NOT NULL,
    supporting_document_urls TEXT[],
    status VARCHAR(32) NOT NULL CHECK (status IN ('submitted', 'under_review', 'resolved_upheld', 'resolved_overturned', 'resolved_modified')),
    final_verdict VARCHAR(32),
    resolution_rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT check_distinct_reviewer CHECK (original_reviewer_id IS NULL OR assigned_reviewer_id IS NULL OR original_reviewer_id != assigned_reviewer_id)
);

CREATE TABLE appeal_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appeal_case_id UUID NOT NULL REFERENCES appeal_cases(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 4.4 WCAG 2.1 AA Accessibility Compliance & Audits

- **Scope**: Monaco code editor, interview video room, exam portal, and appeals portal.
- **Monaco Editor Requirements**:
  - `accessibilitySupport: "on"` explicitly toggled.
  - Keyboard focus trapping release via `Ctrl+M` / `Cmd+M`.
  - Aria-live region announcements for autocompletion suggestions and linter errors.
- **Interview UI Requirements**:
  - Closed captioning display generated directly from real-time Whisper STT pipeline.
  - Minimum color contrast ratio $4.5:1$ for normal text, $3.0:1$ for large text and interactive components.
  - Full keyboard navigability (tab index ordering, visible focus outlines).
- **Accommodations Engine**:
  - Supports individualized student accommodations: extended time multipliers ($1.5\times, 2.0\times$), extra rest breaks, and disabled strict proctoring flags for medical reasons.
- **Automated Audit**: Automated `axe-core` test runs executed in CI, logging compliance status to `accessibility_audit_logs`.

---

## 5. Phase 18 — Reliability & Operations

### 5.1 CI/CD GitHub Actions Workflow

- Configuration path: `.github/workflows/ci.yml`
- Pipeline Stages:
  1. **Lint & Formatting**: Black, Flake8, Ruff for Python backend; ESLint and Prettier for TypeScript Next.js frontend.
  2. **Type Verification**: `mypy --strict` on Python backend; `tsc --noEmit` on frontend.
  3. **Unit Tests**: `pytest -v --cov=app --cov-report=xml` for backend (IRT math, sync queue, auth, models); Jest / Vitest for frontend.
  4. **Integration & Contract Tests**: Spin up PostgreSQL and Redis in Docker containers; run API integration tests against FastAPI app; verify OpenAPI schema stability.
  5. **Accessibility Suite**: Headless Playwright runs with `@axe-core/playwright` asserting 0 critical/serious WCAG 2.1 AA violations.
  6. **Deployment Gate**: Automated staging deployment upon green build on `main`. **No production deploy without passing CI.**

---

### 5.2 Structured Logging with `structlog` & Distributed Tracing

- Logger implementation: Python `structlog` emitting JSON formatted logs to stdout/stderr.
- Injected Contextual Keys on every log record:
  ```json
  {
    "timestamp": "2026-09-16T10:52:00.124Z",
    "level": "info",
    "logger": "exam_sentinel.adaptive",
    "event": "irt_ability_updated",
    "request_id": "req-98f2-4bc1",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "session_id": "sess-8a71-419b",
    "exam_id": "exam-df31-90aa",
    "student_id": "usr-3312-99ca",
    "theta_hat": 0.842,
    "standard_error": 0.285,
    "items_administered": 14
  }
  ```
- Tracing: OpenTelemetry W3C TraceContext (`traceparent`, `tracestate`) propagated across HTTP requests, WebSocket handshakes, and Redis task queue jobs.

---

### 5.3 System Metrics & Alerting

- **Instrumentation**: `prometheus_client` exposing `/metrics`.
- **Key Operational Metrics & Alert Thresholds**:
  1. `exam_sandbox_queue_depth`: Number of code execution jobs waiting in Redis. Alert if $> 20$ for $> 60\text{s}$.
  2. `websocket_disconnect_rate`: Disconnections per minute normalized by active exam connections. Alert if $> 5\%$ in 2 minutes.
  3. `video_room_join_failures`: Failed WebRTC room joins or ICE connection errors. Alert if $> 2$ failures in 5 minutes.
  4. `worker_execution_lag_seconds`: Delta between code job enqueue time and worker pickup time. Alert if $> 3.0\text{s}$.
  5. `db_connection_pool_utilization`: Database connections in use vs max pool size. Alert if $> 80\%$.
- Dashboards: Pre-configured Grafana dashboard JSON models in `observability/grafana/dashboards/`.

---

### 5.4 Load Testing: Thundering Herd Exam Starts (k6 / Locust)

- **Scenario**: Simulate the realistic university exam spike where **500 students simultaneously log in, start exam, download question payloads, and establish WebSocket/proctoring streams within a 60-second window**.
- **Script Implementations**:
  - `load-testing/k6/thundering_herd_start.js`:
    ```javascript
    export const options = {
      stages: [
        { duration: '60s', target: 500 }, // ramp up to 500 concurrent users in 60s
        { duration: '3m', target: 500 },  // sustain load
        { duration: '30s', target: 0 }    // ramp down
      ],
      thresholds: {
        http_req_duration: ['p(95)<500', 'p(99)<1200'],
        http_req_failed: ['rate<0.01'],
      },
    };
    ```
  - `load-testing/locust/locustfile.py`: Simulates answer typing, periodic heartbeats, and WebSocket message bursts.
- **Breaking Point Analysis**:
  - Identify breaking point (e.g. 850 concurrent starts causes Postgres pool starvation without PgBouncer).
  - Provide documented architecture mitigation and tuning guide.

---

### 5.5 Backup & Disaster Recovery (DR) Restore Drill

- **Continuous Archiving & PITR**:
  - PostgreSQL Write-Ahead Logging (WAL) archived to S3/MinIO.
  - Daily base backups via `pg_basebackup`.
- **DR Drill Script (`infra/disaster-recovery/dr_restore_drill.sh`)**:
  - Automates spinning up an isolated ephemeral PostgreSQL instance in Docker.
  - Downloads base backup and WAL archives.
  - Performs Point-in-Time Recovery to timestamp $T - 10\text{m}$.
  - Runs automated data parity verification queries (comparing row counts, cryptographic checksums of submissions, and student records).
  - Documents Recovery Time Objective (RTO < 15 minutes) and Recovery Point Objective (RPO < 5 minutes).
- **Non-Negotiable Constraint**: **No claim of DR readiness without a tested restore drill.**

---

## 6. Phase 19 — Security Hardening & Anti-Cheat

### 6.1 VPN / Proxy Detection (Risk Engine Feeding Without Auto-Blocking)

- **Mechanics**:
  - Upon session login and exam start, student client IP is checked against IP intelligence database / API.
  - Detects: Datacenter IP, commercial VPN endpoint, Tor exit node, or residential proxy network.
- **Inviolable Policy**: **No VPN/proxy signal may auto-block a student.**
  - Legitimate students often route through university campus VPNs or ISP CGNAT proxies.
- **Risk Engine Routing**:
  - Emits `VPN_OR_PROXY_DETECTED` as a low-weight contextual signal (default weight: +10 on a 0–100 scale).
  - Recorded in `vpn_proxy_flags`: IP address, ASN, ISP name, threat score, proxy type.
  - Surfaces in Review Center timeline for human reviewer correlation (e.g. IP geographic jump mid-exam from US to Germany).

---

### 6.2 Multi-Device / Multi-Tab Session Collision Detection

- **Client Fingerprinting (`useDeviceFingerprint.ts`)**:
  - Hashes client hardware traits: Canvas 2D rendering hash, WebGL renderer string, screen dimensions, system font list, audio context fingerprint.
- **Active Session Lock in Redis**:
  - Key: `active_exam_session:{exam_id}:{student_id}`
  - Value: `{ "session_token": "...", "device_fingerprint": "...", "ip": "...", "tab_id": "..." }` with 30-second TTL refreshed via heartbeat.
- **Collision Detection**:
  - When a second connection arrives for the same student on the same exam:
    1. **Multi-Tab Collision**: Same `device_fingerprint` and IP, but different `tab_id`.
    2. **Multi-Device Collision**: Different `device_fingerprint` or different IP.
  - Signal emitted to risk engine: `MULTI_TAB_SESSION_DETECTED` (medium weight) or `MULTI_DEVICE_COLLISION` (high weight: +35).
  - UX behavior: Second tab displays non-blocking modal: `"An active exam session is already open on another window/device. This action has been logged."` Student is NOT locked out, preserving test-taking continuity while logging immutable forensic timestamps for human review.

---

### 6.3 Interview Screen-Share Detection

- **Context**: In live/async interviews, candidate screen sharing should only occur when explicitly instructed by the panel.
- **Detection Service (`screen_share_detection_service.py`)**:
  - Subscribes to WebRTC server-side room events (LiveKit/Daily track published events).
  - Inspects published media track descriptors: `track.kind === 'video'` and `track.source === 'screen_share'` (or `displaySurface` constraint).
  - Unauthorized screen-share detection: If screen track is initiated without an active interviewer prompt flag:
    - Emits `UNAUTHORIZED_SCREEN_SHARE_DETECTED`.
    - Captures track metadata and duration.
    - Prompts interviewer dashboard with live alert badge.
    - Records entry in `screen_share_flags`.

---

### 6.4 Question-Leak Detection (Batch Web & Submission Comparison)

- **Engine (`question_leak_service.py`)**:
  - Maintains cryptographic hashes and embedding vectors (using sentence-transformers / TF-IDF) of all question stems, code prompts, and test cases in `question_bank`.
- **Batch Comparison Job**:
  - Scheduled worker scans public paste sites (Pastebin, GitHub Gists) and cross-compares text across concurrent student submissions and historical appeal statements.
  - Computes n-gram containment and cosine semantic similarity.
  - Threshold: If similarity $> 0.85$ between an unreleased question and an external snippet:
    - Creates record in `question_leak_reports`.
    - Flags question with status `SUSPECTED_LEAK`.
    - Alerts exam administrator to quarantine or swap the question.

---

## 7. Phase 20 — Cost Governance & Product Polish

### 7.1 Usage Metering & Non-Interruptive Throttling

#### 7.1.1 Tracked Resource Dimensions
1. `sandbox_minutes`: Container execution worker runtime (CPU-seconds / 60) consumed by coding submissions.
2. `video_minutes`: Total participant video session minutes in WebRTC rooms.
3. `transcription_minutes`: Audio duration transcribed by Whisper STT.

#### 7.1.2 Budget Thresholds & Alerting
- Per-institution monthly quota configuration.
- Alerts dispatched at:
  - **80% Consumption**: Warning email to institutional billing contact.
  - **100% Consumption**: Critical threshold notification.

#### 7.1.3 Inviolable Policy: Non-Interruptive Throttling
- **Constraint: No budget enforcement may interrupt an exam in progress.**
- If budget reaches 100%:
  - In-progress active exams **continue uninterrupted** with full compute allocation and proctoring.
  - Future exam starts for that institution are queued or held pending administrative approval.
  - Background asynchronous leak scanning and non-urgent transcription are temporarily de-prioritized.

---

### 7.2 Transactional Notification Service (Email / SMS)

- **Channels**: Email via AWS SES or SendGrid; SMS via Twilio.
- **Event Triggers**:
  - Exam enrollment and start reminder (24h and 1h prior).
  - Live interview calendar invite and joining instructions.
  - Submission confirmation receipt with cryptographic verification code.
  - Student appeal progress updates (acknowledged, under review, decision published).
  - Reviewer assignment alerts for invigilators.
- **Delivery Logging**: Every outbound message is logged in `notification_logs` with delivery status, message ID, and provider response.

---

### 7.3 Calendar Integration (Google / Outlook / iCal)

- **Supported Integrations**:
  - Google Calendar API: Automated event creation with room links for live interview exams.
  - Microsoft Graph API: Outlook calendar event creation.
  - Universal Fallback: **RFC 5545 iCalendar (`.ics`) file generation** attached to notification emails and downloadable via API.
- **Endpoints**:
  - `POST /api/calendar/sync-interview`: Syncs scheduled interview slot to attendee calendars.
  - `GET /api/calendar/interview/{session_id}.ics`: Returns standard `.ics` calendar payload.

---

### 7.4 Autograder Pre-Publish Validation Gate

- **Problem Statement**: Erroneous test cases or invalid reference solutions created by instructors lead to broken exams and widespread student grading errors.
- **Validation Engine (`test_case_validation_service.py`)**:
  - Before an exam containing coding questions can be published:
    1. System runs the instructor's **Reference Solution** against **100% of test cases** (both visible and hidden).
    2. Verifies that all test cases pass cleanly without syntax errors, runtime exceptions, or timeouts.
    3. Verifies that execution time is $\le 50\%$ of the maximum allocated student timeout (ensuring adequate headroom for non-optimal student code).
- **Hard Publish Gate**:
  - If any test case fails or reference solution fails to execute:
    `POST /api/exams/{id}/publish` **blocks with HTTP 422 Unprocessable Entity**.
  - Returns detailed diagnostic report identifying exact failing test cases, expected vs actual outputs, and stack traces.
  - Non-negotiable constraint: **No exam type can be published with unvalidated autograder test cases.**

---

## 8. Database Schema Inventory (Phases 15–20)

Below is the complete inventory of database tables for Phases 15 through 20 adhering to PostgreSQL conventions (UUID primary keys, foreign key constraints, indexes, timestamps):

| Table Name | Phase | Purpose | Key Columns |
|------------|-------|---------|-------------|
| `question_irt_params` | 15 | 2PL IRT item parameters | `id`, `question_id`, `discrimination_a`, `difficulty_b`, `scaling_d`, `calibration_n`, `status` |
| `student_ability_est` | 15 | Student ability estimates & CIs | `id`, `session_id`, `student_id`, `exam_id`, `theta_hat`, `standard_error`, `ci_lower`, `ci_upper`, `items_count`, `stopping_reason`, `trajectory` |
| `whiteboard_strokes` | 15 | Vector stroke history | `id`, `session_id`, `question_id`, `stroke_data` (JSONB), `total_duration_ms`, `thumbnail_url` |
| `diagram_placements` | 15 | Diagram question responses | `id`, `session_id`, `question_id`, `placements` (JSONB), `is_correct`, `score` |
| `audio_responses` | 15 | Audio responses & transcripts | `id`, `session_id`, `question_id`, `audio_url`, `duration_seconds`, `transcript_text`, `word_timestamps` (JSONB) |
| `lms_sync_jobs` | 16 | LTI roster and grade syncs | `id`, `institution_id`, `exam_id`, `lms_type`, `job_type`, `status`, `items_synced`, `error_log` |
| `sso_identities` | 16 | Federated SAML/OAuth bindings | `id`, `user_id`, `institution_id`, `provider_type`, `idp_entity_id`, `external_subject_id`, `attributes` |
| `consent_records` | 17 | Versioned consent log | `id`, `student_id`, `institution_id`, `exam_id`, `collection_point`, `consent_version`, `notice_text_hash`, `status`, `ip_address` |
| `data_retention_policies` | 17 | Institution retention rules | `id`, `institution_id`, `data_category`, `retention_days`, `action_type`, `is_active` |
| `retention_deletion_jobs`| 17 | Deletion/anonymization audit | `id`, `policy_id`, `records_scanned`, `records_deleted`, `storage_bytes_freed`, `status`, `executed_at` |
| `appeal_cases` | 17 | Student appeals workflow | `id`, `session_id`, `student_id`, `exam_id`, `appeal_type`, `original_reviewer_id`, `assigned_reviewer_id`, `status`, `final_verdict` |
| `appeal_actions` | 17 | Appeal audit log | `id`, `appeal_case_id`, `actor_id`, `action`, `notes`, `created_at` |
| `accessibility_audit_logs`| 17 | WCAG automated audit records | `id`, `target_component`, `criteria_checked`, `violations_count`, `compliance_status`, `details` |
| `device_sessions` | 19 | Hardware fingerprint sessions | `id`, `session_id`, `student_id`, `device_fingerprint`, `browser_info`, `platform`, `is_mobile` |
| `vpn_proxy_flags` | 19 | VPN/proxy detection flags | `id`, `session_id`, `ip_address`, `is_vpn`, `is_proxy`, `is_datacenter`, `threat_level`, `details` |
| `multi_tab_events` | 19 | Active session collisions | `id`, `session_id`, `student_id`, `collision_type`, `tab_id`, `device_fingerprint`, `detected_at` |
| `screen_share_flags` | 19 | Interview screen-share flags | `id`, `interview_session_id`, `track_id`, `event_type`, `authorized`, `detected_at` |
| `question_leak_reports` | 19 | Question leak comparisons | `id`, `question_id`, `exam_id`, `source_type`, `similarity_score`, `matched_snippet`, `status` |
| `usage_logs` | 20 | Resource usage metering | `id`, `institution_id`, `resource_type`, `quantity`, `session_id`, `recorded_at` |
| `budget_alerts` | 20 | Quota threshold alerts | `id`, `institution_id`, `resource_type`, `threshold_percentage`, `triggered_at`, `status` |
| `notification_logs` | 20 | Outbound email/SMS logs | `id`, `recipient_id`, `channel`, `template_name`, `delivery_status`, `provider_message_id` |
| `calendar_syncs` | 20 | Calendar event bindings | `id`, `interview_session_id`, `provider`, `external_event_id`, `sync_status` |
| `test_case_validation_runs`| 20 | Pre-publish autograder gates | `id`, `exam_id`, `question_id`, `passed`, `test_cases_evaluated`, `test_cases_passed`, `error_details` |

---

## 9. API Endpoint Inventory (Phases 15–20)

### Phase 15 — Adaptive & Multi-Modal
- `POST /api/adaptive/exams/{exam_id}/start`: Initialize adaptive exam session, calculate initial item.
- `POST /api/adaptive/sessions/{session_id}/answer`: Submit item response, update $\hat{\theta}$ via MAP, evaluate stopping criteria, return next item or finish payload.
- `GET /api/adaptive/sessions/{session_id}/ability`: Retrieve current $\hat{\theta}$, $\text{SE}$, $95\%$ CI, and response trajectory.
- `POST /api/questions/diagram/{question_id}/submit`: Submit coordinates and label placements for diagram question.
- `POST /api/questions/whiteboard/{question_id}/strokes`: Save vector stroke stream and thumbnail for whiteboard question.
- `GET /api/questions/whiteboard/{question_id}/replay`: Fetch full vector stroke stream for reviewer playback.
- `POST /api/questions/audio/{question_id}/upload`: Upload audio response blob, trigger transcription pipeline.

### Phase 16 — Resilience & Integrations
- `POST /api/exam/sessions/{session_id}/sync-replay`: Replay batched offline answer drafts and telemetry.
- `GET /api/lti/login_initiation`: Handle 1EdTech LTI 1.3 OIDC login initiation.
- `POST /api/lti/launch`: Handle LTI 1.3 authenticated resource launch.
- `POST /api/lti/sync-roster/{exam_id}`: Trigger LMS roster sync via NRPS 2.0.
- `POST /api/lti/push-grades/{exam_id}`: Push finalized exam grades back to LMS via AGS 2.0.
- `GET /api/auth/sso/saml/metadata.xml`: Return SP SAML metadata XML.
- `POST /api/auth/sso/saml/acs`: SAML Assertion Consumer Service.
- `GET /api/auth/sso/oidc/authorize`: OIDC redirect to identity provider.
- `GET /api/auth/sso/oidc/callback`: OIDC callback exchange code for JWT tokens.

### Phase 17 — Compliance & Legal
- `POST /api/compliance/consent`: Record granted or declined student consent with notice hash.
- `GET /api/compliance/consent/status`: Check student consent status across collection points.
- `GET /api/compliance/retention/policies`: List institution retention policies.
- `POST /api/compliance/retention/policies`: Create/update data retention policy.
- `POST /api/compliance/retention/run-deletion`: Trigger manual or scheduled retention deletion worker.
- `POST /api/compliance/right-to-deletion`: File student right-to-deletion request.
- `POST /api/appeals`: Submit student appeal against decision or autograder grade.
- `GET /api/appeals/queue`: Fetch appeal reviewer queue (enforcing distinct reviewer guard).
- `GET /api/appeals/{appeal_id}`: Fetch appeal case details and evidence.
- `POST /api/appeals/{appeal_id}/resolve`: Submit formal appeal decision with rationale.

### Phase 18 — Operations & Reliability
- `GET /metrics`: Prometheus operational metrics endpoint.
- `GET /health`: Comprehensive system health check (PostgreSQL, Redis, Sandbox workers).

### Phase 19 — Security Hardening
- `POST /api/security/device-fingerprint`: Register device fingerprint and active tab session.
- `POST /api/security/webrtc/screen-share-event`: WebRTC media track event notifier.
- `POST /api/security/question-leak/scan`: Trigger batch question leak detection scan.

### Phase 20 — Cost Governance & Polish
- `GET /api/governance/usage/{institution_id}`: Retrieve usage breakdown (sandbox, video, transcription minutes).
- `GET /api/governance/budgets/{institution_id}`: Retrieve budget limits and threshold alerts.
- `POST /api/calendar/sync-interview`: Sync interview session to Google/Outlook calendar.
- `GET /api/calendar/interview/{session_id}.ics`: Download standard iCal `.ics` invite.
- `POST /api/exams/{exam_id}/validate-autograder`: Run reference solution pre-validation against all test cases.
- `POST /api/exams/{exam_id}/publish`: Publish exam (gated by autograder pre-validation check).

---

## 10. Non-Negotiable Constraints & Architectural Invariants Matrix

| Constraint | Enforcement Point | Failure Consequence |
|------------|-------------------|---------------------|
| **No automated guilt verdicts** | Risk Engine & Review Center | All signals route to human review queue; zero automated penalties. |
| **No student work lost on disconnect** | IndexedDB mirror & Sync Replay | Client saves locally; reconnect replays with Last-Write-Wins and audit record. |
| **No silent overclaiming of monitoring** | Mobile Exam Mode | Explicit pre-exam capability disclosure modal; session tagged `[REDUCED MONITORING]`. |
| **No untracked data collection** | Versioned Consent Service | Access blocked if explicit consent is declined for any active collection point. |
| **No silent deletion or silent retention** | Scheduled Retention Worker | All deletions/anonymizations recorded in `retention_deletion_jobs`. |
| **No decision without an appeal path** | Appeals Subsystem | Every decision has contestable appeal button routing to distinct reviewer queue. |
| **Separation of appeal reviewers** | `check_distinct_reviewer` constraint | Database constraint and service logic block original reviewer from adjudicating appeal. |
| **No VPN/proxy auto-blocking** | Security Hardening / Auth | Emitted as low-weight risk signal (+10); student can always proceed with exam. |
| **No budget enforcement interrupts exams** | Cost Metering Service | In-progress exams always finish; throttling applies only to new exam launches. |
| **No production deploy without CI passing** | GitHub Actions Workflow | CI blocks merge on lint, type-check, unit tests, integration tests, or accessibility failure. |
| **No claim of DR readiness without tested drill** | DR Restore Drill Script | Script executes restore, validates checksums, and documents RTO/RPO. |
| **No exam publish with failing autograder** | Exam Publish Gate | Blocks publication with HTTP 422 if reference solution fails any test case. |

---

## 11. Downstream Implementation Plan & Worker Guidance

To implement Phases 15 through 20 cleanly, downstream sub-orchestrators and workers should sequence work across three modular implementation increments:

1. **Digital Extensions Milestone (Phases 15–16)**:
   - Module 1: `backend/app/services/irt_service.py`, `backend/app/models/question_irt_params.py`, `student_ability_est.py`, and `backend/app/api/adaptive.py`.
   - Module 2: Frontend multi-modal question components (`DiagramLabeling.tsx`, `WhiteboardCanvas.tsx`, `AudioRecorder.tsx`) and vector stroke replay engine.
   - Module 3: Frontend `useOfflineSync.ts` with IndexedDB queue and backend `POST /api/exam/sessions/{id}/sync-replay`.
   - Module 4: LTI 1.3 connector (`connectors/lti/`) and SAML2/OAuth2 SSO handlers.
2. **Compliance & Hardening Milestone (Phases 17 & 19)**:
   - Module 1: `backend/app/models/consent_record.py`, `retention_policy.py`, `appeal_case.py` and endpoints.
   - Module 2: Scheduled worker `retention_service.py` and GDPR right-to-deletion workflow.
   - Module 3: Accessibility audit hardening (Monaco editor keyboard focus, live captioning stream).
   - Module 4: Anti-cheat detectors: `device_integrity_service.py`, `vpn_proxy_flags`, `screen_share_detection_service.py`, and `question_leak_service.py`.
3. **Operations & Governance Milestone (Phases 18 & 20)**:
   - Module 1: `.github/workflows/ci.yml`, `structlog` setup, Prometheus metrics exporter.
   - Module 2: Load testing scenarios (`k6/thundering_herd_start.js`, Locustfile) and DR restore drill script.
   - Module 3: Usage metering service, budget alerting, and non-interruptive throttling middleware.
   - Module 4: Notification delivery (SES/SendGrid/Twilio), calendar sync (Google/Outlook/iCal), and `test_case_validation_service.py` pre-publish gate.
