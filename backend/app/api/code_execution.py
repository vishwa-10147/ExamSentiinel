"""Coding-exam execution endpoint."""

from statistics import mean, pstdev

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.code_submission import CodeSubmission
from app.models.code_test_case import CodeTestCase
from app.models.proctoring_event import EventCategory, EventSeverity, ProctoringEvent
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole
from app.schemas.code_execution import CodeExecutionRequest, CodeExecutionResponse, CodeGradeResponse, CodeIntegrityRequest, CodeTestCaseCreate
from app.services.sandbox_service import SandboxUnavailableError, sandbox_service
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/code", tags=["Code Execution"])


@router.post("/execute", response_model=CodeExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_code(
    payload: CodeExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (await db.execute(select(ExamSession).where(ExamSession.id == payload.session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coding is unavailable for this session state")

    submission = CodeSubmission(
        session_id=session.id,
        candidate_id=session.candidate_id,
        exam_id=session.exam_id,
        language=payload.language,
        source_code=payload.source_code,
        status="QUEUED",
    )
    db.add(submission)
    await db.flush()
    database_setup = ""
    if payload.language == "sql" and payload.question_id:
        from app.models.question import Question
        q = (await db.execute(select(Question).where(Question.id == payload.question_id))).scalar_one_or_none()
        if q and q.database_schema:
            database_setup = q.database_schema
            if q.database_seed:
                database_setup += "\n" + q.database_seed

    try:
        result = sandbox_service.execute(
            payload.language, 
            payload.source_code, 
            payload.stdin, 
            payload.time_limit_sec, 
            payload.memory_limit_mb,
            database_setup=database_setup
        )
    except SandboxUnavailableError as exc:
        submission.status = "UNAVAILABLE"
        submission.result = {"reason": str(exc)}
        await db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    submission.status = result.status
    submission.result = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "wall_time_ms": result.wall_time_ms,
    }
    await db.commit()
    return CodeExecutionResponse(
        submission_id=submission.id,
        status=result.status,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        wall_time_ms=result.wall_time_ms,
        result=submission.result,
    )


@router.post("/test-cases", status_code=status.HTTP_201_CREATED)
async def create_test_case(
    payload: CodeTestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    test_case = CodeTestCase(**payload.model_dump())
    db.add(test_case)
    await db.commit()
    await db.refresh(test_case)
    return {"id": test_case.id, **payload.model_dump()}


@router.post("/grade", response_model=CodeGradeResponse, status_code=status.HTTP_201_CREATED)
async def grade_code(
    payload: CodeExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (await db.execute(select(ExamSession).where(ExamSession.id == payload.session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    cases = (await db.execute(select(CodeTestCase).where(CodeTestCase.exam_id == session.exam_id).order_by(CodeTestCase.order_index))).scalars().all()
    if not cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No coding test cases are configured")

    submission = CodeSubmission(session_id=session.id, candidate_id=session.candidate_id, exam_id=session.exam_id, language=payload.language, source_code=payload.source_code, status="GRADING")
    db.add(submission)
    await db.flush()
    total_weight = sum(case.weight for case in cases)
    earned_weight = 0.0
    case_results = []
    for case in cases:
        try:
            result = sandbox_service.execute(payload.language, payload.source_code, case.input_data, payload.time_limit_sec, payload.memory_limit_mb)
        except SandboxUnavailableError as exc:
            submission.status = "UNAVAILABLE"
            submission.result = {"reason": str(exc)}
            await db.commit()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        passed = result.status == "SUCCESS" and result.stdout.strip() == case.expected_output.strip()
        if passed:
            earned_weight += case.weight
        case_results.append({"name": case.name, "passed": passed, "hidden": case.is_hidden, "status": result.status, "stdout": "" if case.is_hidden else result.stdout, "stderr": "" if case.is_hidden else result.stderr})
    score = round((earned_weight / total_weight) * 100, 2)
    submission.status = "GRADED"
    submission.score = score
    submission.result = {"score": score, "cases": case_results}
    await db.commit()
    return CodeGradeResponse(submission_id=submission.id, score=score, total_weight=total_weight, cases=case_results)


@router.post("/integrity")
async def code_integrity_signal(
    payload: CodeIntegrityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (await db.execute(select(ExamSession).where(ExamSession.id == payload.session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    signals = []
    added_lines = max(0, len(payload.current_code.splitlines()) - len(payload.previous_code.splitlines()))
    if added_lines > 10:
        signals.append(("LARGE_PASTE", {"added_lines": added_lines}))
    intervals = [value for value in payload.keystroke_intervals_ms if value > 0]
    if len(intervals) >= 5 and mean(intervals) > 0 and pstdev(intervals) / mean(intervals) < 0.15:
        signals.append(("TYPING_CADENCE_ANOMALY", {"interval_count": len(intervals), "coefficient_of_variation": pstdev(intervals) / mean(intervals)}))
    for event_type, details in signals:
        db.add(ProctoringEvent(session_id=session.id, candidate_id=session.candidate_id, exam_id=session.exam_id, event_type=event_type, category=EventCategory.CODE_INTEGRITY, severity=EventSeverity.HIGH if event_type == "LARGE_PASTE" else EventSeverity.LOW, details=details))
    score, risk_level = await risk_engine.recalculate_and_update(db, session.id)
    await db.commit()
    return {"signals": [{"event_type": event_type, "details": details} for event_type, details in signals], "risk_score": score, "risk_level": risk_level}
