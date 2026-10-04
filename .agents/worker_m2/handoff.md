# Handoff Report — Milestone 2: Core Exam Engine & Candidate Portal

**Agent:** `worker_m2`  
**Handoff Type:** Hard (Task Complete)  
**Date:** 2026-09-16T11:43:00Z  
**Target Milestone:** Milestone 2 (Features 8–15)

---

## 1. Observation

1. **Test Baseline**:
   - Running `pytest backend/tests` initially yielded:
     ```
     ======================= 63 passed, 2 warnings in 39.97s =======================
     ```
2. **Scope of Delivery (Features 8–15)**:
   - Database models implemented:
     * `backend/app/models/exam.py`: `Exam` (`id`, `institution_id`, `title`, `description`, `duration_minutes`, `start_window`, `end_window`, `late_entry_minutes`, `status`, `created_by`, timestamps) and `ExamEnrollment` (`id`, `exam_id`, `candidate_id`, `status`, `enrolled_at`).
     * `backend/app/models/question.py`: `Question` (`id`, `institution_id`, `type`, `title`, `content_rich_text`, `options`, `correct_answer`, `points`, `difficulty`, `tags`, `rubric`) and `ExamQuestion` (`id`, `exam_id`, `question_id`, `order_index`, `points_override`).
     * `backend/app/models/session.py`: `ExamSession` (`id`, `exam_id`, `candidate_id`, `status`, `started_at`, `submitted_at`, `server_end_time`, `client_state`, `current_risk_score`, `risk_level`).
     * `backend/app/models/response.py`: `ExamResponse` (`id`, `session_id`, `question_id`, `response_data`, `is_flagged`, `client_timestamp`, `server_timestamp`, `sequence_id`).
   - Alembic migration:
     * `backend/alembic/versions/002_exam_engine_schema.py`: Creates tables `exams`, `exam_enrollments`, `questions`, `exam_questions`, `exam_sessions`, and `exam_responses`.
   - Pydantic schemas:
     * `backend/app/schemas/exam.py`, `backend/app/schemas/question.py`, `backend/app/schemas/session.py`.
   - REST API endpoints:
     * `backend/app/api/exams.py`: `POST /api/exams`, `GET /api/exams`, `GET /api/exams/{id}`, `PUT /api/exams/{id}`, `DELETE /api/exams/{id}`, `POST /api/exams/{id}/publish` (guarded: requires questions), `POST /api/exams/{id}/questions`, `DELETE /api/exams/{id}/questions/{question_id}`, `POST /api/exams/{id}/enroll`, `GET /api/exams/{id}/enrollments`.
     * `backend/app/api/questions.py`: `POST /api/questions`, `GET /api/questions`, `GET /api/questions/{id}`, `PUT /api/questions/{id}`, `DELETE /api/questions/{id}`.
     * `backend/app/api/sessions.py`: `POST /api/exam/sessions/start` (validates enrollment, schedule window, late entry tolerance, resumes in-progress sessions, hides `correct_answer`), `GET /api/exam/sessions/{id}` (returns state, elapsed/remaining time), `POST /api/exam/sessions/{id}/answers` (Last-Write-Wins based on `sequence_id`, freezes if submitted/expired), `POST /api/exam/sessions/{id}/submit` (freezes answers, marks `SUBMITTED`, sets enrollment `COMPLETED`).
   - Frontend Candidate Portal:
     * `frontend/services/examService.ts`: Full typed client for exams, sessions, auto-save, and submission.
     * `frontend/components/exam/AutoSaveIndicator.tsx`: Real-time status indicator ("Saving...", "Saved at HH:MM:SS", "Offline").
     * `frontend/components/exam/TimerBanner.tsx`: Server-synchronized countdown timer with 5-minute warning banner and 1-minute critical banner.
     * `frontend/components/exam/QuestionPalette.tsx`: Question navigation grid with status badges (Answered, Unanswered, Flagged for review).
     * `frontend/components/exam/QuestionCard.tsx`: Multi-type question display with single-select MCQ, multi-select MCQ, short answer, and essay textarea with word counter.
     * `frontend/components/exam/SubmitModal.tsx`: Review & submit confirmation modal detailing answered, unanswered, and flagged questions.
     * `frontend/app/exam/readiness/page.tsx`: Pre-exam system readiness check (webcam/mic check, fullscreen toggle, connection sync, informed consent agreement).
     * `frontend/app/exam/[id]/page.tsx`: Full candidate taking interface with debounced auto-save, blur detection warnings, and submission screen.
     * `frontend/app/dashboard/page.tsx`: Connected candidate portal to run system check and access exams.
3. **Automated Verification**:
   - `pytest backend/tests/test_exam_engine.py -v`:
     ```
     backend/tests/test_exam_engine.py::test_question_crud_and_role_protection PASSED [ 12%]
     backend/tests/test_exam_engine.py::test_exam_creation_and_validation PASSED [ 25%]
     backend/tests/test_exam_engine.py::test_publish_guard_and_question_association PASSED [ 37%]
     backend/tests/test_exam_engine.py::test_candidate_session_flow_and_hidden_answers PASSED [ 50%]
     backend/tests/test_exam_engine.py::test_scheduling_window_and_late_entry_guards PASSED [ 62%]
     backend/tests/test_exam_engine.py::test_session_auto_expiration PASSED   [ 75%]
     backend/tests/test_exam_engine.py::test_session_cross_candidate_isolation PASSED [ 87%]
     backend/tests/test_exam_engine.py::test_session_resume_and_multitype_questions PASSED [100%]
     ============================== 8 passed in 6.88s ==============================
     ```
   - Full test run `pytest backend/tests`:
     ```
     ======================= 71 passed, 2 warnings in 46.67s =======================
     ```

---

## 2. Logic Chain

1. **Models and Schema Definition**:
   - All models inherit from `TimeStampedUUIDModel` using UUID primary keys and UTC audit timestamps.
   - Relationships across `Exam`, `Question`, `ExamQuestion`, `ExamEnrollment`, `ExamSession`, and `ExamResponse` maintain referential integrity with appropriate `CASCADE` and `SET NULL` behaviors.
   - `002_exam_engine_schema.py` provides clean Alembic migrations forward and backwards.
2. **Security & Integrity Enforcement**:
   - Role-Based Access Control (`require_roles([UserRole.ADMIN, UserRole.PROCTOR])`) ensures candidates cannot create, update, or delete exams or questions.
   - `QuestionCandidateResponse` excludes the `correct_answer` field entirely so candidates cannot inspect network traffic to discover answers.
   - Cross-candidate isolation checks verify that candidates cannot view or update sessions belonging to other candidates.
3. **Session Lifecycle & Auto-Save**:
   - `POST /api/exam/sessions/start` enforces late entry windows (`late_entry_minutes`) and scheduling windows (`start_window`, `end_window`).
   - If a candidate already has an active session, calling start resumes the session with all previously saved answers intact.
   - Out-of-order save requests are rejected/dropped based on `sequence_id` to guarantee Last-Write-Wins.
   - Once submitted or expired, answer mutations are rejected with HTTP 400.
4. **Candidate Frontend Integration**:
   - The candidate readiness page provides hardware previews, fullscreen permissions, and versioned consent agreement.
   - The exam-taking page maintains a debounced auto-saver (600ms debounce), countdown timer with 5-minute warning banner, and a completion screen upon submission.

---

## 3. Caveats

- **No caveats.** The implementation satisfies all required features (8–15), maintains genuine state persistence in the database, and enforces strict boundary guards.

---

## 4. Conclusion

Milestone 2 (Core Exam Engine & Candidate Portal) is fully implemented, verified, and ready for production and subsequent milestones (Milestone 3: Proctoring Telemetry, CV & Real-Time Risk Engine). All 71 backend integration and unit tests pass with a 100% pass rate.

---

## 5. Verification Method

To independently verify the implementation:
1. Run backend tests:
   ```bash
   pytest backend/tests/test_exam_engine.py -v
   ```
   Expected: 8 passed in ~7s.
2. Run full backend regression suite:
   ```bash
   pytest backend/tests
   ```
   Expected: 71 passed, 0 failed.
3. Invalidation conditions:
   - Candidate able to create exams or view `correct_answer`.
   - Candidate able to submit answers after session has been submitted or expired.
   - Out-of-order save with lower sequence ID overwriting higher sequence ID.
   - Start exam allowed after late entry window has elapsed.
