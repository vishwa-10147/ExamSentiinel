# Dispatch: Milestone 2 Remediation Worker

## Identity
- Role: Core Exam Engine Remediation Implementer
- Agent Name: `worker_m2_remediation`
- Working Directory: `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2_remediation\`
- Project Root: `d:\vishwa47\v47Studio\ExamSentinel\`

## Mandatory References
1. `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`
2. `d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md`
3. `d:\vishwa47\v47Studio\ExamSentinel\.agents\reviewer_m2\handoff.md` (Contains exact line numbers and defect details)

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks & Defect Fix Specifications
1. **Fix Defect 1 — Late Entry Reconnect Lockout (`backend/app/api/sessions.py:83-118`)**:
   In `start_exam_session`:
   - Check for an existing `ExamSession` with `status == SessionStatus.IN_PROGRESS` *FIRST* before checking the late entry window (`late_entry_deadline`).
   - If an existing active session exists, resume and return it immediately, regardless of whether the late entry window has elapsed.
   - Only apply the `late_entry_deadline` check when creating a *new* session.
2. **Fix Defect 2 — Auto-Submit on Timeout Rejection (`backend/app/api/sessions.py:446-455`)**:
   In `submit_exam_session`:
   - If `session.status == SessionStatus.EXPIRED`, allow the submission to proceed: update `session.status = SessionStatus.SUBMITTED`, set `session.submitted_at = datetime.now(timezone.utc)`, update candidate enrollment `status = EnrollmentStatus.COMPLETED`, commit, and return success. Only reject if `session.status == SessionStatus.SUBMITTED`.
3. **Fix Defect 3 — Alien Question Validation in Answer Auto-Save (`backend/app/api/sessions.py:369-418`)**:
   In `submit_answer`:
   - Verify that `payload.question_id` belongs to `session.exam_id` by checking `ExamQuestion` table (`select(ExamQuestion).where(ExamQuestion.exam_id == session.exam_id, ExamQuestion.question_id == payload.question_id)`).
   - If not found, raise `HTTPException(status_code=400, detail="Question is not part of this exam")`.
4. **Add Regression Tests in `backend/tests/test_exam_engine.py`**:
   - Add `test_late_entry_reconnect_allowed_after_window_expires`
   - Add `test_expired_session_submit_succeeds`
   - Add `test_alien_question_answer_rejected`
5. **Run All Tests**:
   - Run `pytest backend/tests/` and verify 100% pass rate across all test suites.

## Deliverables
- Working code and passing tests.
- Handoff report to `d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2_remediation\handoff.md`.
- Send completion message to parent orchestrator.

## 2026-09-16T11:47:18Z
You are worker_m2_remediation, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2_remediation\
Read:
- d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md
- d:\vishwa47\v47Studio\ExamSentinel\PROJECT.md
- d:\vishwa47\v47Studio\ExamSentinel\.agents\reviewer_m2\handoff.md
- d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2_remediation\DISPATCH.md
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Fix the 3 defects in backend/app/api/sessions.py:
1. Allow resume of active session even after late entry window expires (check active session before late entry check).
2. Allow submitting an EXPIRED session so it cleanly marks SUBMITTED and enrollment COMPLETED.
3. Validate question_id belongs to exam_id in submit_answer, reject alien questions with HTTP 400.
Add tests in test_exam_engine.py. Run pytest and verify 100% pass rate.
Write handoff report to d:\vishwa47\v47Studio\ExamSentinel\.agents\worker_m2_remediation\handoff.md. Update progress.md. When finished, send a message to orchestrator.

