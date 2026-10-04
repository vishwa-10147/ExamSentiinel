# ExamSentinel Specification Mining Survey Report: Phases 11–14
**Document ID:** `survey_report.md`  
**Agent:** `spec_miner_survey_2`  
**Date:** 2026-09-16T10:48:00Z  
**Primary Source:** `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (inclusive of `docs/readme.md`, `docs/plan.md`, `docs/explain.md`, `docs/prompt.md`, Requirements R2–R3, and Acceptance Criteria)  
**Target Tracks:** 
- **Phases 11–12: Coding Exam Track** (Monaco Editor, Sandboxed Execution, Resource Limits, Visible/Hidden Tests, Autograding, Paste Detection, Typing Cadence Analysis, MOSS Cross-Submission Similarity, Pre-Publish Validation)
- **Phases 13–14: Interview Exam Track** (Live WebRTC Video Rooms, Question Script, Rubric Scoring, Multi-Panelist Aggregation, Async Recorded Interviews, Whisper Transcription, Clickable Timestamped Highlights, Screen-Share Detection)

---

## 1. Executive Summary & Architectural Scope

The ExamSentinel platform extends digital exam integrity beyond conventional multiple-choice testing into rigorous technical assessments (in-browser coding) and verbal evaluations (live and asynchronous structured interviews). 

A foundational architectural invariant across all mined subsystems is:
> **Signals, Not Verdicts / No Automated Guilt.**  
> Neither automated code sandboxes, plagiarism algorithms, cadence detectors, nor transcription highlight models can ever render an automated misconduct finding or penalize a student. Every detector feeds the central Risk Engine weight table and Review Center, where qualified human evaluators examine the contextual evidence.

### Subsystem Interconnections
```
[Student Frontend] ──> Monaco Editor / WebRTC Live / Async Video
        │
        ├──> [Code Execution Service] ──> Redis Queue ──> [gVisor/Firecracker Sandbox Workers]
        │            │                                          │
        │            ├──> WebSocket Stream ────────────────────┘
        │            └──> [Autograder & Pre-Publish Validator]
        │
        ├──> [Integrity Detectors]
        │            ├──> Paste Detector (>10 lines diff)
        │            ├──> Typing Cadence Analyzer (IKI burstiness)
        │            └──> MOSS Winnowing Similarity (Post-Exam Batch)
        │
        ├──> [Interview Service] ──> LiveKit/Daily WebRTC SFU ──> Multi-Panelist Rubrics
        │            │
        │            ├──> Screen-Share Detector (Track Metadata)
        │            └──> Async Video Storage (S3) ──> Whisper STT ──> Transcript Navigator
        │
        └──> [Risk Engine & Admin Review Center] <── (All signals route here with configurable weights)
```

---

## 2. Phase 11: Code Execution Foundation

### 2.1 Monaco Editor Integration
- **Frontend Location:** `frontend/components/code-editor/`, `frontend/app/exam/coding/`
- **Supported Languages:**
  - Mandatory primary: **Python 3.10+** (`python`) and **JavaScript (Node.js 18+)** (`javascript`).
  - Extended support in spec: **Java 17+** (`java`) and **C++ (GCC/Clang)** (`cpp`).
- **Core Editor Capabilities:**
  - Multi-language syntax highlighting, bracket matching, indentation auto-format.
  - Contextual autocompletion (IntelliSense disabled or restricted based on exam integrity flags).
  - Split-pane layout: Problem statement and test results on side panel; code editor on main canvas.
  - Reset to boilerplate starter code.
  - Local auto-save to browser storage (resilient against page refresh).
  - **Accessibility Compliance (Phase 17 linkage):** WCAG 2.1 AA compliance requiring Monaco accessibility mode (`accessibilitySupport: 'on'`), screen reader DOM nodes, and keyboard focus trap escape commands (`Ctrl+M`).

### 2.2 Sandboxed Execution Engine & Security Hardening
- **Execution Engine:** Custom gVisor (`runsc`) / Firecracker microVMs or Judge0 container-isolated execution workers (`execution-workers/`).
- **Isolation Guarantees (Non-Negotiable):**
  1. **Strictly Zero Network Access:** Workers instantiated with `--net=none` or empty network namespace. Zero loopback access to internal microservices, Redis, or database.
  2. **Filesystem Jail:** Read-only root filesystem. Ephemeral memory-backed `tmpfs` mounts for compilation and execution (capped at 16MB). Drop all Linux capabilities (`CAP_SYS_ADMIN`, `CAP_NET_RAW`, etc.).
  3. **Process & Fork-Bomb Protection:** `pids.max` set strictly (e.g., 32 processes max) to prevent recursive fork attacks.
  4. **Syscall Filtering:** Seccomp profiles blocking risky syscalls (`ptrace`, `sys_chroot`, `socket`, `mount`).

### 2.3 Resource Limits & Test Runner Protocol
- **Default Constraints:**
  - **CPU Limit:** 1.0 virtual CPU core per execution.
  - **Memory Limit:** 128MB to 256MB hard cap.
  - **Execution Wall-Clock Timeout:** Configurable per test case (default: 2000ms; hard maximum 5000ms).
- **Test Case Classification:**
  - **Visible Test Cases:** Inputs and expected outputs are displayed to candidate. Used during active exam for real-time iterative debugging via "Run Code".
  - **Hidden Test Cases:** Inputs and expected outputs are completely shielded from student client and API payloads. Executed only upon final submission or background evaluation to prevent hardcoded solutions.
- **Output Matching & Normalization:**
  - Normalization rules: Trim trailing whitespace, normalize line endings (`\r\n` -> `\n`), ignore single trailing blank lines.

### 2.4 Asynchronous Queue & WebSocket Streaming
- **Queue Pipeline:** Redis + Celery / RQ.
- **Worker Behavior:** Workers are strictly stateless and idempotent. Submissions are enqueued as JSON jobs.
- **Streaming Life-Cycle:**
  1. Client calls `POST /api/code/submit` (or `/run`).
  2. Backend places job on Redis queue `code:execution:queue` and returns `job_id`.
  3. Client opens WebSocket connection to `/api/code/ws/{job_id}`.
  4. Worker publishes execution events: `QUEUED` ➔ `COMPILING` ➔ `RUNNING_TEST_N` ➔ `OUTPUT_STREAM` ➔ `COMPLETED` / `ERROR`.
  5. Status codes emitted: `PASSED`, `FAILED`, `TIMEOUT`, `MEMORY_LIMIT_EXCEEDED`, `COMPILATION_ERROR`, `RUNTIME_ERROR`.

---

## 3. Phase 12: Coding Exam Integrity & Autograding

### 3.1 Large Paste Detection
- **Trigger Rule:** Any paste event inserting **greater than 10 lines** (`line_count > 10`) or diff size greater than 200 characters in a single input tick.
- **Algorithm:**
  - Client-side hook (`useCodeExecution.ts` / Monaco `onDidChangeModelContent`) tracks delta between sequential editor buffers.
  - When insertion delta spans $>10$ line breaks (`\n`), payload captures: `pasted_line_count`, `char_length`, `timestamp_ms`, `content_hash`.
  - Emits `LARGE_PASTE_DETECTED` event to the backend and Risk Engine.
- **Integrity Rule:** Flagged for reviewer inspection in Review Center with diff viewer. Never auto-terminates or auto-grades as zero.

### 3.2 Typing Cadence Analysis
- **Theoretical Basis:** Human manual typing exhibits natural log-normal inter-keystroke interval (IKI) distributions. Automated paste injectors, macro scripts, or external automation emit uniform, near-zero, or unnatural intervals.
- **Client Telemetry:**
  - Records rolling buffer of keydown timestamps: $T = [t_0, t_1, t_2, \dots, t_n]$.
  - Calculates inter-keystroke intervals: $\Delta t_i = t_i - t_{i-1}$ (in milliseconds).
- **Server Analysis (`ai/code-integrity/`):**
  - Calculates mean $\mu = \frac{1}{N}\sum \Delta t_i$, standard deviation $\sigma = \sqrt{\frac{1}{N}\sum (\Delta t_i - \mu)^2}$.
  - **Burstiness Metric:**
    $$B = \frac{\sigma - \mu}{\sigma + \mu}$$
  - Evaluates coefficient of variation $CV = \frac{\sigma}{\mu}$.
  - Anomaly scoring flags:
    1. Unnatural Uniformity: $\sigma < 5\text{ms}$ over 50+ characters (indicating macro replay).
    2. Zero-delay injections without clipboard paste trigger.
  - Risk Signal: `TYPING_CADENCE_ANOMALY`. Documented as low-weight risk signal, human-reviewed only.

### 3.3 Cross-Submission Plagiarism / Similarity (MOSS-Style)
- **Execution Paradigm:** Post-exam asynchronous batch job running across all submissions for a given exam question.
- **Algorithm: Tokenized Winnowing (Schleimer et al.):**
  1. **Lexical Normalization:** Parse code into tokens, stripping comments, variable names, and whitespace. Identifiers map to `ID`, string literals to `STR`, numbers to `NUM`.
  2. **K-Gram Generation:** Generate sliding token k-grams of length $k$ (default $k = 15$).
  3. **Rolling Hash:** Compute hash for each k-gram using Rabin-Karp polynomial rolling hash:
     $$H(c_1 \dots c_k) = \sum_{i=1}^k c_i \cdot b^{k-i} \pmod M$$
  4. **Winnowing Algorithm:** In each sliding window of size $w$ (default $w = 10$) of consecutive hashes, select the minimum hash value. (If tie, choose rightmost minimum). This forms the document fingerprint.
  5. **Pairwise Comparison / Inverted Index:**
     $$\text{Similarity}(S_1, S_2) = \frac{|\text{Fingerprint}(S_1) \cap \text{Fingerprint}(S_2)|}{\min(|\text{Fingerprint}(S_1)|, |\text{Fingerprint}(S_2)|)}$$
  6. **Threshold & Review UI:** Pairs exceeding similarity threshold (e.g., $\ge 75\%$) are flagged in Review Center with side-by-side synchronized token diffs.

### 3.4 Autograding System
- **Weighted Scoring Formulation:**
  $$\text{Final Question Score} = \sum_{i=1}^M (\text{weight}_i \cdot \mathbb{I}(\text{test}_i == \text{PASSED}))$$
- Supports partial credit based on passed test cases.
- Execution metrics recorded: cumulative execution runtime, peak memory footprint.

### 3.5 Pre-Publish Test Case Validation (Phase 20 linkage)
- **Enforcement Service:** `test_case_validation_service.py`
- **Validation Rule:** An exam creator **cannot publish** a coding exam unless every question includes a verified Reference Solution that:
  1. Executes successfully within the exact sandbox environment.
  2. Passes 100% of all visible and hidden test cases.
  3. Does not trigger `TIMEOUT` or `MEMORY_LIMIT_EXCEEDED`.
  4. Has at least 1 visible test case and at least 1 hidden test case defined.
- **Publish Block:** Backend returns `422 Unprocessable Entity` with details of failing test cases if validation fails.

---

## 4. Phase 13: Live Interview Mode

### 4.1 WebRTC Video Infrastructure
- **Integration Framework:** LiveKit or Daily.co WebRTC SDKs (WebRTC SFU architecture).
- **Session Lifecycle:**
  1. Interview scheduled with candidate and assigned panelist(s).
  2. Backend generates cryptographic join tokens with explicit room scopes and role claims (`candidate`, `interviewer`, `panelist`, `observer`).
  3. Candidate and panelists connect to WebRTC room.
  4. Bi-directional audio/video publishing with server-side media recording enabled.
  5. Automatic ICE renegotiation and reconnection handling for dropped network packets.

### 4.2 Interviewer Question Script UI
- **Interface Location:** `frontend/components/interview/`, `frontend/app/exam/interview/`
- **Capabilities:**
  - Live side-by-side console: Video feed on primary panel, structured question script on secondary panel.
  - Hierarchical question breakdown: Section, Question Title, Detailed Prompt, Time Target, Behavioral Anchors.
  - Active question synchronization: Lead interviewer can advance active question, synchronizing focus across all panelists via WebSocket.
  - Real-time scratchpad / panelist notes per question.

### 4.3 Rubric-Based Scoring & Multi-Panelist Consensus Aggregation
- **Independent Scoring Architecture:**
  - Panelists record scores independently across predefined rubric criteria (e.g., Technical Mastery, Problem Decomposition, Communication, System Architecture).
  - Scoring scale: Configurable 1–5 numerical scale or categorical rubric bands with descriptive rubrics.
  - **Anti-Anchoring Isolation:** Panelists cannot view co-panelists' scores or notes during the active interview.
- **Consensus & Aggregation Formulas:**
  - **Mean Score:**
    $$\bar{S}_c = \frac{1}{P}\sum_{p=1}^P S_{p,c}$$
  - **Inter-Rater Variance / Discrepancy Flag:**
    $$\sigma_c = \sqrt{\frac{1}{P}\sum_{p=1}^P (S_{p,c} - \bar{S}_c)^2}$$
    If $\max(S_{p,c}) - \min(S_{p,c}) \ge 2.0$, session is marked for panel deliberation / reconciliation.
  - Aggregated view displays individual panelist breakdowns, calculated average, and consolidated reviewer notes.

### 4.4 Screen-Share Detection & Proctoring Integration (Phase 19 linkage)
- **Service:** `screen_share_detection_service.py`
- **Detection Mechanism:**
  - LiveKit/Daily track subscription events inspect WebRTC track metadata.
  - When candidate publishes a track with source `screen` or `screen_share`:
    - Checks exam policy `allow_screen_share`.
    - If unauthorized: Emits `UNAUTHORIZED_SCREEN_SHARE` signal to the Risk Engine.
    - Displays non-disruptive alert to interview panel; records timestamped violation in session audit trail.

---

## 5. Phase 14: Async Interview Mode & Transcription

### 5.1 Asynchronous Timed Response Workflow
- **Candidate Experience:**
  1. System check & device test (camera, microphone, speaker test).
  2. **Consent Capture:** Explicit versioned consent prompt for video/audio recording and transcription storage.
  3. Structured question progression:
     - **Preparation Timer:** Configurable countdown (e.g., 30–60 seconds) where prompt is visible, but recording has not started.
     - **Response Recording Timer:** Countdown (e.g., 90–180 seconds) during which candidate's response is actively captured via browser `MediaRecorder` API.
     - Automatic stop and upload when countdown expires.
     - Candidate can confirm upload and proceed to next question. Retakes are strictly disabled unless configured by institution.

### 5.2 Storage & Audio Processing Pipeline
- **Storage:** Chunked upload to S3 / MinIO object storage with presigned URLs.
- **Audio Extraction:** Server worker invokes `ffmpeg` to extract clean 16kHz mono 16-bit PCM WAV audio from uploaded WebM/MP4 video files.

### 5.3 Whisper-Class Transcription Pipeline
- **Service:** `transcription_service.py` (`ai/interview-analysis/`)
- **Transcription Model:** OpenAI Whisper (self-hosted `faster-whisper` / `whisper-timestamped` or enterprise STT API).
- **Output Schema:** Time-aligned JSON with word-level and phrase-level millisecond timestamps:
  ```json
  {
    "segments": [
      {
        "id": 0,
        "start": 1.12,
        "end": 4.85,
        "text": "The time complexity of this approach is O of N log N.",
        "words": [
          {"word": "The", "start": 1.12, "end": 1.30, "confidence": 0.99},
          {"word": "time", "start": 1.32, "end": 1.65, "confidence": 0.98},
          {"word": "complexity", "start": 1.68, "end": 2.20, "confidence": 0.99}
        ]
      }
    ]
  }
  ```

### 5.4 Interactive Transcript Viewer & Reviewer Highlights
- **Bidirectional Video-Transcript Sync:**
  - Clicking any word or timestamp in the transcript seeks the video player to that exact millisecond.
  - Video playback highlights corresponding transcript text in real time.
- **Clickable Timestamped Highlights (Navigation Aids Only):**
  1. **Extended Pauses:** Silence gaps $> 3.0$ seconds highlighted on transcript timeline.
  2. **Filler Word Density:** Instances of lexical fillers ("um", "uh", "like", "you know") tagged and aggregated as fillers/minute.
  3. **Proctoring Timeline Correlation:** Overlays events from the proctoring stream (e.g., `FACE_NOT_DETECTED`, `MULTIPLE_FACES`, `PHONE_DETECTED`, `TAB_BLUR`) directly onto the transcript timeline.
  - **Critical Design Directive:** Highlights are **reviewer navigation aids only**, NEVER automated penalties or guilt scores.

---

## 6. Database Models & Schema Specifications

### 6.1 Coding Track Tables
```sql
-- 1. Language Configurations
CREATE TABLE language_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    language VARCHAR(32) UNIQUE NOT NULL, -- python, javascript, java, cpp
    version VARCHAR(32) NOT NULL,
    runner_image VARCHAR(128) NOT NULL,
    compile_cmd TEXT,
    run_cmd TEXT NOT NULL,
    file_extension VARCHAR(16) NOT NULL,
    default_timeout_ms INT NOT NULL DEFAULT 2000,
    default_memory_mb INT NOT NULL DEFAULT 128,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Test Cases (Visible & Hidden)
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    time_limit_ms INT,
    memory_limit_mb INT,
    order_index INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Code Submissions
CREATE TABLE code_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_session_id UUID NOT NULL REFERENCES exam_sessions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    language VARCHAR(32) NOT NULL,
    source_code TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT
    score NUMERIC(5,2) DEFAULT 0.00,
    total_weight NUMERIC(5,2) DEFAULT 0.00,
    passed_count INT DEFAULT 0,
    total_count INT DEFAULT 0,
    execution_time_ms INT,
    memory_bytes BIGINT,
    paste_events_count INT DEFAULT 0,
    max_paste_lines INT DEFAULT 0,
    cadence_burstiness NUMERIC(5,4),
    cadence_anomaly_score NUMERIC(5,4),
    is_final BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Execution Results (Per Test Case)
CREATE TABLE execution_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES code_submissions(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL, -- PASSED, FAILED, TIMEOUT, RUNTIME_ERROR, MEMORY_EXCEEDED
    actual_output TEXT,
    error_output TEXT,
    execution_time_ms INT NOT NULL,
    memory_bytes BIGINT,
    passed BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Test Case Validation Runs (Pre-Publish)
CREATE TABLE test_case_validation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    reference_solution_code TEXT NOT NULL,
    language VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL, -- PASSED, FAILED, ERROR
    total_tests INT NOT NULL,
    passed_tests INT NOT NULL,
    failure_details JSONB,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.2 Interview Track Tables
```sql
-- 6. Interview Sessions
CREATE TABLE interview_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    interview_type VARCHAR(16) NOT NULL, -- 'LIVE' or 'ASYNC'
    room_id VARCHAR(128) UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED', -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    scheduled_start_at TIMESTAMPTZ NOT NULL,
    scheduled_end_at TIMESTAMPTZ NOT NULL,
    actual_start_at TIMESTAMPTZ,
    actual_end_at TIMESTAMPTZ,
    consent_record_id UUID REFERENCES consent_records(id),
    final_score NUMERIC(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Interview Questions & Rubrics
CREATE TABLE interview_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    order_index INT NOT NULL DEFAULT 0,
    title VARCHAR(255) NOT NULL,
    prompt_text TEXT NOT NULL,
    category VARCHAR(64) NOT NULL, -- technical, behavioral, system_design
    prep_time_seconds INT DEFAULT 30,
    response_time_seconds INT DEFAULT 120,
    rubric_criteria JSONB NOT NULL, -- [{criterion: string, max_points: int, description: string, weight: float}]
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Interview Recordings & Transcription
CREATE TABLE interview_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_id UUID REFERENCES interview_questions(id) ON DELETE SET NULL,
    storage_path TEXT NOT NULL,
    duration_seconds NUMERIC(7,2) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    transcription_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    transcript_json JSONB,
    filler_words_count INT DEFAULT 0,
    long_pauses_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. Interview Scores (Multi-Panelist)
CREATE TABLE interview_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    panelist_id UUID NOT NULL REFERENCES users(id),
    question_id UUID REFERENCES interview_questions(id) ON DELETE CASCADE,
    criterion_name VARCHAR(128) NOT NULL,
    score NUMERIC(5,2) NOT NULL,
    max_score NUMERIC(5,2) NOT NULL,
    weight NUMERIC(5,2) NOT NULL DEFAULT 1.00,
    notes TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_panelist_criterion UNIQUE (interview_session_id, panelist_id, question_id, criterion_name)
);

-- 10. Screen Share Flags
CREATE TABLE screen_share_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_session_id UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES users(id),
    track_id VARCHAR(128) NOT NULL,
    is_authorized BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    risk_score_delta NUMERIC(5,2) NOT NULL DEFAULT 15.00,
    reviewed_by UUID REFERENCES users(id),
    finding VARCHAR(64)
);
```

---

## 7. API Endpoints & Interfaces

### 7.1 Coding Exam API
| Method | Route | Description | Request Body | Response Body |
|---|---|---|---|---|
| `POST` | `/api/code/run` | Execute code against visible test cases for real-time testing | `{"question_id": UUID, "language": str, "source_code": str}` | `{"job_id": UUID, "status": "QUEUED"}` |
| `POST` | `/api/code/submit` | Final submission evaluated against hidden and visible test cases | `{"question_id": UUID, "session_id": UUID, "language": str, "source_code": str, "paste_events": list, "cadence_metrics": dict}` | `{"submission_id": UUID, "job_id": UUID, "status": "QUEUED"}` |
| `GET` | `/api/code/submissions/{submission_id}` | Retrieve submission result and autograder breakdown | None | `{"submission_id": UUID, "status": str, "score": float, "passed": int, "total": int, "results": [...]}` |
| `WS` | `/api/code/ws/{job_id}` | WebSocket stream for live execution logs and test outcomes | WebSocket handshake with auth token | Streamed JSON frames: `{"event": "TEST_CASE", "index": 0, "status": "PASSED", "duration_ms": 42}` |
| `POST` | `/api/code/validate-reference` | Validate reference solution against question test cases (pre-publish check) | `{"question_id": UUID, "language": str, "reference_code": str}` | `{"valid": bool, "passed_tests": int, "total_tests": int, "errors": [...]}` |
| `POST` | `/api/code/plagiarism-batch` | Trigger MOSS-style tokenized cross-submission analysis | `{"exam_id": UUID, "question_id": UUID, "threshold": 0.75}` | `{"job_id": UUID, "total_submissions": int}` |
| `GET` | `/api/code/plagiarism-results/{exam_id}` | Retrieve flagged high-similarity pairs | None | `{"flagged_pairs": [{"sub_a": UUID, "sub_b": UUID, "similarity": 0.89, "matching_ranges": [...]}]}` |

### 7.2 Interview Exam API
| Method | Route | Description | Request Body | Response Body |
|---|---|---|---|---|
| `POST` | `/api/interviews/rooms/create` | Initialize LiveKit/Daily video room | `{"interview_session_id": UUID}` | `{"room_id": str, "livekit_url": str}` |
| `POST` | `/api/interviews/rooms/{room_id}/token` | Issue signed WebRTC participant JWT | `{"interview_session_id": UUID, "role": "candidate" \| "panelist"}` | `{"token": str, "expires_in": int}` |
| `GET` | `/api/interviews/{interview_id}/script` | Fetch question script & rubric definition | None | `{"questions": [{"id": UUID, "title": str, "rubrics": [...]}]}` |
| `POST` | `/api/interviews/{interview_id}/scores` | Submit independent panelist score | `{"scores": [{"question_id": UUID, "criterion": str, "score": float, "notes": str}]}` | `{"status": "SAVED", "count": int}` |
| `GET` | `/api/interviews/{interview_id}/scores/aggregated` | Retrieve aggregated consensus scores | None | `{"criteria": [...], "panelist_breakdown": [...], "consensus_score": float, "discrepancies": [...]}` |
| `POST` | `/api/interviews/async/{session_id}/recordings` | Upload recorded response video | Multipart form: `question_id`, `video_blob` | `{"recording_id": UUID, "storage_path": str}` |
| `POST` | `/api/interviews/recordings/{recording_id}/transcribe` | Trigger Whisper transcription job | None | `{"job_id": UUID, "status": "PROCESSING"}` |
| `GET` | `/api/interviews/recordings/{recording_id}/transcript` | Get time-aligned transcript & highlights | None | `{"transcript": [...], "pauses": [...], "fillers": [...], "proctoring_correlations": [...]}` |
| `POST` | `/api/interviews/{interview_id}/screen-share-event` | Report WebRTC screen share start/stop | `{"participant_id": UUID, "track_id": str, "action": "START" \| "STOP"}` | `{"flag_id": UUID, "is_authorized": bool}` |

---

## 8. Cross-Cutting Constraints & Edge Cases

### 8.1 Critical Project Invariants
1. **Never Automated Guilt:** No student is disqualified, zeroed, or marked cheater automatically by the paste detector, typing cadence analyzer, similarity runner, or screen-share detector. All route to the Risk Engine and Review Center.
2. **Pre-Publish Blocking:** If reference code fails any test case or times out, the exam cannot transition to `PUBLISHED`.
3. **No Budget-Induced Exam Interruption (Phase 20 linkage):** If an institution exhausts its sandbox execution minutes or video minutes mid-exam, the in-progress exam is NEVER aborted or degraded. Alerts trigger, and graduation throttling applies only to new exam launches.
4. **Resilient Async Audio Recording:** If candidate browser crashes mid-recording, partial video chunks saved locally are preserved and upload resumes via chunked multipart.
5. **Multi-Panelist Blind Scoring:** Panelists must remain blind to each other's live inputs until deliberation or final aggregation.

---

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Coding Track | Monaco In-Browser Code Editor | Code editor supporting Python, JS, C++, Java with syntax highlighting, indentation, accessibility support | User keystrokes, language selection, starter code | Formatted code buffer, cursor telemetry | Graceful fallback on unsupported syntax or browser incompatibility | `ORIGINAL_REQUEST.md` line 38, 300, 413, 539 |
| 2 | Coding Track | Sandboxed Execution Engine | gVisor/Firecracker or Judge0 isolated worker running code without network or filesystem write rights | Source code string, language id, standard input | Standard output, standard error, execution time ms, memory bytes | Emits `TIMEOUT` (>2s) or `MEMORY_EXCEEDED` (>256MB) or `RUNTIME_ERROR` | `ORIGINAL_REQUEST.md` line 42, 177, 303–308, 413 |
| 3 | Coding Track | Visible vs Hidden Test Evaluation | Evaluates visible tests during active drafting and hidden tests during final autograding | Code submission, test case suite (`is_hidden` flag) | Detailed diff for visible; pass/fail boolean count for hidden | Returns test-specific failure messages; masks hidden inputs/outputs from student API | `ORIGINAL_REQUEST.md` line 306, 413, 505, 541 |
| 4 | Coding Track | Autograding Weighted Scoring | Calculates final technical question score based on test case weights and outcomes | Test case execution status array, weights | Final score float, passed test count, total test count | Unhandled exceptions or syntax errors yield 0 points with compilation error logs | `ORIGINAL_REQUEST.md` line 314, 505, 542 |
| 5 | Coding Track | Pre-Publish Test Case Validation | Blocks publishing of coding exam if reference solution fails any test case | Reference solution code, test cases | Validation report (Pass/Fail) | Blocks exam publish action (`422 Unprocessable Entity`) | `ORIGINAL_REQUEST.md` line 383, 461, 505, 545, 587 |
| 6 | Coding Integrity | Large Paste Detection | Detects clipboard insertions exceeding 10 lines, calculating diff against previous buffer | Monaco buffer change event, delta line count | `LARGE_PASTE_DETECTED` signal to Risk Engine with line count and hash | Recorded as evidence in Review Center; does NOT block submission | `ORIGINAL_REQUEST.md` line 311, 416, 505, 543 |
| 7 | Coding Integrity | Typing Cadence Analysis | Statistical analysis of inter-keystroke intervals (IKIs) to compute burstiness and detect macro scripts | Keydown timestamps array $(\Delta t)$ | Cadence burstiness score $B$, `TYPING_CADENCE_ANOMALY` signal | Low-weight risk signal routed to reviewer; never auto-penalizes | `ORIGINAL_REQUEST.md` line 312, 417, 505 |
| 8 | Coding Integrity | Cross-Submission Similarity (MOSS) | Winnowing algorithm with k-gram tokenization to detect structural plagiarism across submissions | Batch submissions for question, k-gram length $k$, window $w$ | Pairwise similarity score matrix, highlighted matching token ranges | Flags pairs $\ge 75\%$ for reviewer inspection; handles trivial code gracefully | `ORIGINAL_REQUEST.md` line 182, 313, 418, 505, 544 |
| 9 | Interview Track | Live WebRTC Video Room | Multi-party video conferencing for live candidate-interviewer sessions via LiveKit/Daily SDK | Room ID, participant role token, audio/video media tracks | Live media feeds, peer connection status, audio levels | Handles network drops with ICE renegotiation and reconnection states | `ORIGINAL_REQUEST.md` line 43, 179, 320, 422, 508, 548 |
| 10 | Interview Track | Interviewer Question Script UI | Synchronized structured question script console for interviewers | Exam question bank, category tags, time targets | Interactive question list, active question indicator, notes scratchpad | Gracefully permits free-form question reordering or skip | `ORIGINAL_REQUEST.md` line 321, 422, 508, 549 |
| 11 | Interview Track | Rubric-Based Scoring Panel | Structured criteria evaluation with score inputs and behavioral anchors | Criterion IDs, ratings (1–5), panelist qualitative notes | Saved rubric scores per criterion | Rejects invalid score ranges; requires mandatory notes on outlier scores | `ORIGINAL_REQUEST.md` line 322, 508, 549 |
| 12 | Interview Track | Multi-Panelist Independent Scoring | Isolated scoring interface preventing anchoring bias; aggregates post-interview | Independent panelist score sets | Consensus score (mean), inter-rater variance, deliberation flags | Flags score variance $\ge 2.0$ between panelists for consensus review | `ORIGINAL_REQUEST.md` line 323–324, 508, 550 |
| 13 | Interview Track | Async Recorded Interview Mode | Candidate records timed responses to preset prompts with prep and response countdowns | Question prompt, prep timer seconds, response timer seconds | Video/audio recording blob, upload receipt | MediaRecorder failure triggers local retry; records timer expirations | `ORIGINAL_REQUEST.md` line 329–330, 424, 508, 551 |
| 14 | Interview Track | Whisper-Class Audio Transcription | Speech-to-text pipeline generating time-aligned transcript with word-level timestamps | Extracted 16kHz WAV audio stream from recording | JSON transcript with word/phrase millisecond timestamps | Low audio levels or background noise flagged; retains raw audio | `ORIGINAL_REQUEST.md` line 44, 180, 331, 424, 508, 552 |
| 15 | Interview Track | Interactive Transcript Highlights | Clickable highlights for pauses (>3s), filler words, and proctoring event overlaps | Time-aligned transcript, proctoring event timeline | Interactive video seek navigation, highlighted transcript tokens | Highlights function exclusively as navigation aids, never verdicts | `ORIGINAL_REQUEST.md` line 332–333, 424, 508, 553 |
| 16 | Interview Integrity | Screen-Share Detection | Detects WebRTC screen-sharing tracks published by candidate | WebRTC track metadata (`source: "screen"`) | `UNAUTHORIZED_SCREEN_SHARE` signal to Risk Engine | Triggers interviewer notification; never auto-terminates session | `ORIGINAL_REQUEST.md` line 189, 373, 455, 520, 579 |
| 17 | Platform Governance | Usage Metering & Guardrails | Tracks sandbox-minutes, video-minutes, and transcription-minutes per institution | Execution duration, WebRTC room duration, audio STT duration | Monthly usage logs, budget alerts at 80% & 100% | Graduated throttling on new exams; NEVER interrupts in-progress exams | `ORIGINAL_REQUEST.md` line 378–380, 458, 523, 583–584 |
| 18 | Compliance | Versioned Consent Capture | Explicit consent captured prior to webcam, audio recording, and keystroke logging | User consent affirmation, notice version ID, collection scope | Auditable `consent_record` linked to session | Access blocked until consent explicitly granted | `ORIGINAL_REQUEST.md` line 352, 442, 514, 554, 565 |
| 19 | Compliance | Contested Evaluation Appeals | Student appeals workflow against autograder results or interview panel scores | Appeal submission, student justification, submission ID | Distinct reviewer queue, appeal audit record, score adjustment | Requires review by distinct reviewer from original evaluator | `ORIGINAL_REQUEST.md` line 356–358, 446, 514, 567 |
| 20 | Compliance | Accessibility (WCAG 2.1 AA) | Screen reader and keyboard navigation compliance across Monaco and interview UI | Assistive tech inputs, keyboard navigation | Accessible DOM tree, aria-labels, high contrast | Audit log generated; accessibility mode switchable in Monaco | `ORIGINAL_REQUEST.md` line 359, 448, 514, 568 |

---

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | Sandboxed Code Execution | Infinite loop or `while True: pass` in student code | Sandbox wall-clock watchdog kills process at exactly configured timeout (e.g., 2000ms), status marked `TIMEOUT`, zero points, no CPU hang on worker |
| 2 | Sandboxed Code Execution | Memory exhaustion attack (e.g., `a = [0] * 10**9`) | Sandbox cgroups memory limit terminates process immediately (`SIGKILL`), status marked `MEMORY_LIMIT_EXCEEDED`, stdout truncated, system worker stays healthy |
| 3 | Sandboxed Code Execution | Socket creation or network call (e.g., `requests.get("https://evil.com")`) | Network namespace `--net=none` blocks socket creation instantly (`OSError: [Errno 101] Network is unreachable`), prevents exfiltration |
| 4 | Sandboxed Code Execution | Recursive fork bomb (e.g., `while(1) fork();`) | Cgroup process ceiling (`pids.max = 32`) denies child process creation; worker terminates parent process cleanly |
| 5 | Sandboxed Code Execution | Massive output flood (e.g., `while True: print("A")`) | Output stream buffer truncated at 100KB with marker `[Output truncated]`, status marked `FAILED` or `TIMEOUT` |
| 6 | Sandboxed Code Execution | Whitespace mismatch in output (e.g., trailing spaces or `\r\n` vs `\n`) | Output normalizer strips trailing whitespace and standardizes newlines, resulting in `PASSED` if logical content matches |
| 7 | Large Paste Detection | Candidate pastes code template containing exactly 11 lines | Detects line delta $= 11 > 10$, logs paste event with timestamp and character length, emits `LARGE_PASTE_DETECTED` risk signal to reviewer |
| 8 | Large Paste Detection | Candidate pastes 1-line snippet of 2000 characters | Token/character threshold triggers paste event even if line count is 1, preventing single-line minified code paste bypass |
| 9 | Typing Cadence Analysis | Automated macro software inserts keystrokes with uniform 20ms delay | Inter-keystroke standard deviation $\sigma \approx 0 < 5\text{ms}$, burstiness anomaly detected, emits `TYPING_CADENCE_ANOMALY` signal |
| 10 | Typing Cadence Analysis | Candidate naturally pauses for 2 minutes to think, then types fast | Inter-keystroke interval exhibits natural human log-normal variance; burstiness score remains within normal human variance threshold |
| 11 | MOSS Plagiarism Detection | Candidate renames all variables and changes `while` loop to `for` loop | Lexical tokenization normalizes identifiers to uniform `ID` tokens; winnowing fingerprints match source submission, yielding high similarity score |
| 12 | MOSS Plagiarism Detection | Short 5-line standard solution (e.g., recursive factorial or binary search) | Fingerprint overlap is high due to problem simplicity; similarity engine flags as common pattern, reviewer inspects and dismisses as non-misconduct |
| 13 | Pre-Publish Validation | Admin provides incorrect reference solution that fails 1 hidden test case | Exam publish action blocked with `422 Unprocessable Entity`; error report details exact input and expected vs actual output of failing test |
| 14 | Pre-Publish Validation | Admin creates coding question with zero hidden test cases | Validation service rejects question publish; policy requires at least one visible test and at least one hidden test case |
| 15 | Live WebRTC Interview | Panelist drops internet connection mid-interview | LiveKit SFU detects ICE disconnect, UI displays "Panelist reconnecting" indicator; other participants remain connected, recording continues uninterrupted |
| 16 | Live WebRTC Interview | Panelist A scores 1/5 and Panelist B scores 5/5 on same rubric criterion | Discrepancy metric $|S_A - S_B| = 4 \ge 2.0$ flags criterion for panel reconciliation post-interview; consensus view displays both scores |
| 17 | Async Video Interview | Candidate's browser tab closes during response recording | Local MediaRecorder buffer flushes to IndexedDB; upon tab reload, student is prompted to resume upload of saved segment |
| 18 | Async Video Interview | Candidate attempts to retake question after finishing recording | System strictly enforces single-take policy; API returns `403 Forbidden` for re-recording attempts unless explicit administrator accommodation granted |
| 19 | Whisper Transcription | Candidate has heavy accent or audio has low signal-to-noise ratio | Whisper generates transcript with lower token confidence scores; reviewer clicks low-confidence segment to listen directly to raw audio |
| 20 | Transcript Highlights | Candidate pauses for 4.5 seconds to read technical problem prompt | Transcription pipeline identifies silence gap $> 3.0$s and highlights duration on timeline; reviewer sees question start context and disregards |
| 21 | Screen-Share Detection | Candidate enables secondary monitor or screen share to view notes | WebRTC track event `screen` detected; emits `UNAUTHORIZED_SCREEN_SHARE` signal to admin dashboard; reviewer evaluates without terminating call |
| 22 | Usage Metering | Institution hits 100% video/sandbox budget while 10 exams are active | Active exams continue to completion without interruption; new exam launches are gated with a notification to institution administrator |
| 23 | Student Appeals Flow | Candidate appeals autograder 0/100 due to compiler flag difference | Appeal routes to secondary reviewer queue; reviewer runs code with custom flags, inspects diff, and can override grade with full audit log |
| 24 | Accessibility Audit | Candidate with motor impairment utilizes screen reader and keyboard navigation | Monaco accessibility mode provides focus trap release via `Ctrl+M`; ARIA labels enable question navigation and rubric score entry |
