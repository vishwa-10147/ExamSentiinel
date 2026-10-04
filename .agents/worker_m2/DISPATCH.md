# Dispatch: Milestone 2 Worker (Core Exam Engine & Candidate Portal)

## Identity
- Role: Core Exam Engine Implementer
- Agent Name: `worker_m2`
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`

## Mandatory Reference Documents
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (MUST read first)
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md` (Milestone 2 scope, Features 8–15, Interface Contracts)
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_1\survey_report.md` (Section 5: Data Models, REST Endpoints, and Algorithms for Exam Engine & Candidate Portal)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive File Ownership
You exclusively own:
- `backend/app/models/exam.py`, `backend/app/models/question.py`, `backend/app/models/session.py`, `backend/app/models/response.py`
- `backend/app/schemas/exam.py`, `backend/app/schemas/question.py`, `backend/app/schemas/session.py`
- `backend/app/api/exams.py`, `backend/app/api/questions.py`, `backend/app/api/sessions.py`
- `backend/alembic/versions/002_exam_engine_schema.py`
- `backend/tests/test_exam_engine.py`
- `frontend/app/exam/` (launch, readiness check, taking interface)
- `frontend/components/exam/` (QuestionPalette, TimerBanner, QuestionCard, AutoSaveIndicator)
- `frontend/services/examService.ts`

## Scope of Implementation (Features 8 to 15)
1. **Database Schema & Models**:
   - `Exam`: `id`, `institution_id`, `title`, `description`, `duration_minutes`, `start_window`, `end_window`, `late_entry_minutes`, `status` (`DRAFT`, `PUBLISHED`, `ARCHIVED`), `created_by`, timestamps.
   - `Question`: `id`, `institution_id`, `type` (`MCQ_SINGLE`, `MCQ_MULTI`, `SHORT_ANSWER`, `ESSAY`), `title`, `content_rich_text`, `options` (JSON for choices), `correct_answer` (JSON, hidden from candidate taking view), `points`, `difficulty`, `tags`, rubrics.
   - `ExamQuestion`: `id`, `exam_id`, `question_id`, `order_index`, `points_override`.
   - `ExamSession`: `id`, `exam_id`, `candidate_id`, `status` (`READY`, `IN_PROGRESS`, `SUBMITTED`, `EXPIRED`), `started_at`, `submitted_at`, `server_end_time`, `client_state` JSON.
   - `ExamResponse`: `id`, `session_id`, `question_id`, `response_data` JSON, `client_timestamp`, `server_timestamp`, `sequence_id`.
   - Migration in `backend/alembic/versions/002_exam_engine_schema.py`.
2. **REST API Endpoints**:
   - `POST /api/exams`, `GET /api/exams`, `GET /api/exams/{id}`, `PUT /api/exams/{id}`, `POST /api/exams/{id}/publish` (Protected by ADMIN/PROCTOR).
   - `POST /api/questions`, `GET /api/questions`, `GET /api/questions/{id}`, `PUT /api/questions/{id}` (Protected by ADMIN/PROCTOR).
   - `POST /api/exams/{id}/enroll`: Candidate enrollment.
   - `POST /api/exam/sessions/start`: Validates scheduling window, late entry limit, active status. Creates `ExamSession` and returns questions list with `correct_answer` stripped.
   - `GET /api/exam/sessions/{id}`: Returns session state, elapsed/remaining time.
   - `POST /api/exam/sessions/{id}/answers`: Auto-save endpoint with debounced answer persistence, updating `ExamResponse` (Last-Write-Wins based on sequence_id).
   - `POST /api/exam/sessions/{id}/submit`: Formal submission, sets `status = SUBMITTED`, freezes answers, prevents subsequent modifications (HTTP 400 if already submitted).
   - Automatic server-side expiration: If session exceeds duration + grace period, rejects further answer updates and marks `status = EXPIRED`.
3. **Frontend Candidate Experience**:
   - System readiness check page (webcam/mic check, fullscreen permission, terms & consent).
   - Exam Taking Interface:
     * Question navigation palette with status markers (Answered, Unanswered, Flagged for review).
     * Server-synchronized countdown timer with 5-minute warning banner.
     * Real-time auto-save indicator ("Saved", "Saving...", "Offline").
     * Fullscreen lock modal and warning on blur.
     * Review & Submit modal with answered/unanswered counts.
4. **Testing & Verification**:
   - Write comprehensive unit & integration tests in `backend/tests/test_exam_engine.py` covering:
     * Exam creation & question bank association
     * Publish guard (ensuring exam cannot start without questions)
     * Candidate session start within window and rejection outside window
     * Answer auto-save (Last-Write-Wins and sequence integrity)
     * Submission freeze (rejecting edits after submission)
     * Auto-submit on expiration
     * Role protection (candidate forbidden from creating exams or seeing correct answers)
   - Run pytest and verify all tests pass with exit code 0.

## Deliverables
- Working code across backend, migrations, tests, and frontend.
- Write handoff report to `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2\handoff.md`.
- Send completion message to parent orchestrator.

## 2026-09-16T11:28:51Z
Implement Milestone 2 (Core Exam Engine & Candidate Portal — Features 8–15):
1. Database models & migrations (Exam, Question, ExamQuestion, ExamSession, ExamResponse).
2. REST API endpoints (exams CRUD, questions CRUD, enrollment, session start, answers auto-save, submit, auto-expiration).
3. Frontend Candidate Portal (readiness check, taking interface, question palette, timer banner, auto-save status, submit modal).
4. Tests in backend/tests/test_exam_engine.py. Run pytest and verify 100% pass rate.
Write your handoff report to d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2\handoff.md. Update progress.md as you work. When finished, send a message to orchestrator.
