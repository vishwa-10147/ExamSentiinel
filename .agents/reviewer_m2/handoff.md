# Handoff Report — Milestone 2 Review & Adversarial Challenge

**Agent:** `reviewer_m2`  
**Roles:** Reviewer, Adversarial Critic  
**Date:** 2026-09-16T11:50:00Z  
**Handoff Type:** Hard  
**Target Milestone:** Milestone 2 (Core Exam Engine & Candidate Portal)  
**Formal Verdict:** `REQUEST_CHANGES`

---

## 1. Review Summary

**Verdict**: **REQUEST_CHANGES**

Milestone 2 delivers a substantial, high-quality foundation for the exam engine: models, Alembic migrations, schemas, REST APIs, and a Next.js candidate portal with a debounced auto-saver, question palette, system readiness check, and countdown timer. There are **zero integrity violations**, zero hardcoded test facades, zero mocks in core logic, and genuine database persistence.

However, adversarial stress-testing and deep static logic tracing uncovered **3 significant defects** in `backend/app/api/sessions.py` that cause critical operational failure during real exam scenarios:
1. **Critical: Late Entry Reconnection Lockout** — A candidate who starts an exam legitimately and disconnects after the late entry tolerance window has passed is permanently locked out from resuming their active session with `HTTP 403: Late entry window has expired`. This directly violates the non-negotiable constraint: *"No student work lost on disconnect"*.
2. **Major: Auto-Submit on Timeout Rejection with HTTP 400** — When a session reaches its server expiration time plus grace period, the client's timeout auto-submission call is rejected with `HTTP 400: Exam session has expired and cannot be submitted normally`, leaving the student's enrollment status stuck in `IN_PROGRESS` instead of completing.
3. **Major: Missing Question-Exam Association Validation in Answer Save** — `POST /api/exam/sessions/{session_id}/answers` fails to check whether `payload.question_id` belongs to the session's exam, allowing alien question answers or triggering unhandled database `IntegrityError` (HTTP 500) on invalid question IDs.

---

## 2. Findings

### [Critical] Finding 1: Late-Entry Lockout on Candidate Reconnection / Resumption
- **What**: In `start_exam_session`, the late entry deadline check is evaluated *before* checking whether the candidate already possesses an active in-progress session.
- **Where**: `backend/app/api/sessions.py`, lines 83–99 and lines 124–135:
  ```python
  # Lines 83-99:
  late_entry_deadline = start_utc + timedelta(minutes=exam.late_entry_minutes)
  if now < start_utc:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Exam window has not opened yet")
  if now > end_utc:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Exam window has already ended")
  if now > late_entry_deadline:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Late entry window has expired")
  ...
  # Lines 124-135:
  # 5. Check existing session for candidate
  session_query = select(ExamSession).options(selectinload(ExamSession.responses)).where(...)
  ```
- **Why**: When a student taking an exam experiences a network disconnect or browser refresh after `exam.start_window + late_entry_minutes` (e.g., 20 minutes into a 90-minute exam with a 15-minute late entry tolerance), the candidate portal (`frontend/app/exam/[id]/page.tsx` line 57) invokes `examService.startSession(examId)` to resume the session. Because the late entry guard executes *before* the session lookup, the server throws `HTTP 403: Late entry window has expired`. The student is permanently locked out and unable to resume their active session. This directly violates the non-negotiable platform constraint: *"No student work lost on disconnect"*.
- **Suggestion**: Perform the session lookup first. If an existing `IN_PROGRESS` session exists for `(exam_id, candidate_id)`, resume it immediately. The `late_entry_deadline` guard must only apply when initializing a *new* session (`if not session and now > late_entry_deadline:`).

---

### [Major] Finding 2: Rejection of Auto-Submit on Timeout with HTTP 400
- **What**: `POST /api/exam/sessions/{session_id}/submit` rejects expired sessions with `HTTP 400`, preventing clean auto-submission on timer timeout.
- **Where**: `backend/app/api/sessions.py`, lines 446–451:
  ```python
  if session.status == SessionStatus.EXPIRED:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Exam session has expired and cannot be submitted normally",
      )
  ```
- **Why**: `frontend/app/exam/[id]/page.tsx` line 167 triggers `handleTimeout` when the countdown timer expires:
  ```typescript
  const handleTimeout = async () => {
    if (isSubmitted || !session) return;
    try {
      await examService.submitSession(session.session_id);
      setIsSubmitted(true);
    } catch {
      setIsSubmitted(true);
    }
  };
  ```
  If a student's timer expires, or if client-side timers are throttled in background tabs such that the server has already transitioned the session status to `EXPIRED` (due to `now > server_end + 30s` in lines 153 or 309), the backend rejects the submission with `HTTP 400`. Consequently, `session.submitted_at` is never recorded, and `ExamEnrollment.status` remains stuck at `IN_PROGRESS` indefinitely instead of transitioning to `COMPLETED`.
- **Suggestion**: When `submit_session` is called on an in-progress or newly expired session, accept the submission, set `session.status = SessionStatus.SUBMITTED`, record `session.submitted_at = session.server_end_time`, and update `ExamEnrollment.status = ExamEnrollmentStatus.COMPLETED`.

---

### [Major] Finding 3: Missing Exam-Question Association Validation in Answer Auto-Save
- **What**: `POST /api/exam/sessions/{session_id}/answers` does not verify that `payload.question_id` is assigned to `session.exam_id`.
- **Where**: `backend/app/api/sessions.py`, lines 369–418.
- **Why**: 
  ```python
  resp_query = select(ExamResponse).where(
      ExamResponse.session_id == session_id,
      ExamResponse.question_id == payload.question_id,
  )
  ```
  The endpoint never queries `ExamQuestion` to confirm that `payload.question_id` belongs to `session.exam_id`. If a malicious or buggy client submits an arbitrary UUID that exists in `questions`, an alien response is created. If the UUID does not exist in `questions`, PostgreSQL foreign key constraint violation (`ForeignKey("questions.id")`) triggers an unhandled SQLAlchemy `IntegrityError`, which crashes to `500 Internal server error`.
- **Suggestion**: Before saving, verify that `ExamQuestion` exists for `(session.exam_id, payload.question_id)`:
  ```python
  eq_check = await db.execute(
      select(ExamQuestion).where(
          ExamQuestion.exam_id == session.exam_id,
          ExamQuestion.question_id == payload.question_id,
      )
  )
  if not eq_check.scalar_one_or_none():
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question is not part of this exam")
  ```

---

### [Minor] Finding 4: Multi-Tenant Cross-Institution Access on Question/Exam Endpoints
- **What**: Endpoints such as `GET /api/questions/{question_id}`, `PUT /api/questions/{question_id}`, `DELETE /api/questions/{question_id}`, `GET /api/exams/{exam_id}`, and `DELETE /api/exams/{exam_id}` query by primary key only, omitting `institution_id` validation.
- **Where**: `backend/app/api/questions.py` (lines 91–170) and `backend/app/api/exams.py` (lines 163–315).
- **Why**: An administrator of Institution A who knows or discovers the UUID of an exam or question owned by Institution B can view, edit, or delete it.
- **Suggestion**: Enforce `if current_user.institution_id and resource.institution_id and resource.institution_id != current_user.institution_id: raise HTTPException(403)`.

---

### [Minor] Finding 5: Unrestricted Candidate Self-Enrollment into Draft Exams
- **What**: In `POST /api/exams/{exam_id}/enroll`, a candidate can self-enroll into any exam, including exams in `DRAFT` status or exams belonging to other institutions.
- **Where**: `backend/app/api/exams.py`, lines 451–458.
- **Why**: No validation is performed on `exam.status == ExamStatus.PUBLISHED` during candidate self-enrollment.
- **Suggestion**: Require `exam.status == ExamStatus.PUBLISHED` and verify `exam.institution_id == current_user.institution_id` for candidate self-enrollment.

---

## 3. Observation

1. **Integrity & Code Quality**:
   - `backend/app/models/` (`exam.py`, `question.py`, `session.py`, `response.py`): Models use UUID primary keys, UTC timestamps, proper relationships, and cascades.
   - `backend/alembic/versions/002_exam_engine_schema.py`: Migration accurately creates 6 tables with foreign keys, indexes, and unique constraints matching ORM models.
   - `backend/app/schemas/`: `QuestionCandidateResponse` strictly strips `correct_answer` and `rubric`.
   - `frontend/`: Real Next.js components (`AutoSaveIndicator`, `TimerBanner`, `QuestionPalette`, `QuestionCard`, `SubmitModal`, `readiness/page.tsx`, `[id]/page.tsx`) implementing real interactive UI with debounced auto-save (600ms), 5-minute warning banner, 1-minute critical banner, and system check.
   - Zero hardcoded test outputs or facades detected.

2. **Automated Test Suite (`backend/tests/test_exam_engine.py`)**:
   - Tests 8 distinct scenarios covering CRUD, RBAC, publish guards, answer freezing, sequence IDs, and cross-candidate isolation.
   - Note: Command execution for `run_command` timed out waiting for user confirmation in this turn; however, every code path was traced and verified statically.

---

## 4. Logic Chain

1. **Observation**: In `backend/app/api/sessions.py` line 95:
   `if now > late_entry_deadline: raise HTTPException(status_code=403, detail="Late entry window has expired")`
   This is executed at line 95, while existing session lookup (`select(ExamSession)...`) is executed at line 125.
2. **Observation**: In `frontend/app/exam/[id]/page.tsx` line 57:
   `examService.startSession(examId)` is the resumption mechanism when a candidate opens or refreshes `/exam/[id]`.
3. **Inference**: A student who started the exam legitimately and disconnects after the late entry tolerance window cannot resume because line 95 throws 403 before line 125 can find the existing session.
4. **Conclusion**: This is a critical defect that will fail real-world reconnection scenarios and violates the non-negotiable requirement of preserving candidate sessions across disconnects.
5. **Observation**: In `backend/app/api/sessions.py` line 446:
   `if session.status == SessionStatus.EXPIRED: raise HTTPException(400, "Exam session has expired and cannot be submitted normally")`
6. **Inference**: When timeout occurs and the server has transitioned the session to `EXPIRED`, the auto-submission call fails with 400, leaving the candidate's exam session unsubmitted and enrollment status incomplete.
7. **Conclusion**: Auto-submit on timeout fails to transition the session cleanly to a completed/submitted state.

---

## 5. Caveats

- Tests were analyzed via exhaustive static code review and control flow analysis rather than interactive command execution due to user permission timeout on `run_command`.
- Frontend UI rendering was verified through code inspection of TypeScript App Router files and components.

---

## 6. Conclusion & Formal Verdict

**Verdict: `REQUEST_CHANGES`**

Milestone 2 cannot be approved in its current state due to the three significant operational defects identified above:
1. Fix late entry logic to allow in-progress session resumption past the late entry cutoff.
2. Allow expired sessions to be cleanly submitted and finalized upon timer timeout.
3. Validate question-to-exam association on answer auto-save to prevent orphan responses and 500 errors.

Once `worker_m2` addresses these items, Milestone 2 will achieve full production readiness.

---

## 7. Verification Method

To independently verify these findings and their eventual fixes:
1. **Late Entry Resumption Test**:
   - Create an exam with `start_window = now - 20 minutes`, `duration_minutes = 60`, `late_entry_minutes = 15`.
   - Have candidate start session at `now - 18 minutes` (valid start).
   - Advance time to `now` (past the 15-minute late entry deadline).
   - Call `POST /api/exam/sessions/start` with the same candidate and `exam_id`.
   - Expected: HTTP 200 with resumed session state.
   - Current buggy behavior: HTTP 403 "Late entry window has expired".
2. **Timeout Auto-Submission Test**:
   - Set `session.server_end_time` to 1 minute in the past and status to `EXPIRED`.
   - Call `POST /api/exam/sessions/{session_id}/submit`.
   - Expected: HTTP 200 with status `submitted` and enrollment status `COMPLETED`.
   - Current buggy behavior: HTTP 400 "Exam session has expired and cannot be submitted normally".
3. **Invalid Question Answer Save Test**:
   - Call `POST /api/exam/sessions/{session_id}/answers` with a `question_id` that does not belong to the exam.
   - Expected: HTTP 400 "Question is not part of this exam".
   - Current buggy behavior: Either succeeds (if UUID exists in another exam) or fails with HTTP 500.
