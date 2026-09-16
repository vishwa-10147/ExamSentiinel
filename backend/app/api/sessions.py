from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, log_audit_event
from app.core.database import get_db
from app.models.exam import Exam, ExamEnrollment, ExamEnrollmentStatus, ExamStatus
from app.models.question import ExamQuestion, Question
from app.models.response import ExamResponse
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole
from app.schemas.question import QuestionCandidateResponse
from app.schemas.session import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    CandidateResponseItem,
    SessionStartRequest,
    SessionStateResponse,
    SessionSubmitRequest,
    SessionSubmitResponse,
)

router = APIRouter(tags=["Exam Sessions"])


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("/start", response_model=SessionStateResponse, status_code=status.HTTP_200_OK)
async def start_exam_session(
    payload: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    # 1. Load exam with questions
    exam_query = (
        select(Exam)
        .options(selectinload(Exam.exam_questions).selectinload(ExamQuestion.question))
        .where(Exam.id == payload.exam_id)
    )
    exam_res = await db.execute(exam_query)
    exam = exam_res.scalar_one_or_none()

    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # 2. Check enrollment for candidates
    if current_user.role == UserRole.CANDIDATE:
        enroll_res = await db.execute(
            select(ExamEnrollment).where(
                ExamEnrollment.exam_id == payload.exam_id,
                ExamEnrollment.candidate_id == current_user.id,
            )
        )
        enrollment = enroll_res.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidate is not enrolled in this exam",
            )

    # 3. Check exam status (must be published)
    if exam.status != ExamStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam is not published yet",
        )

    start_utc = ensure_utc(exam.start_window)
    end_utc = ensure_utc(exam.end_window)
    late_entry_deadline = start_utc + timedelta(minutes=exam.late_entry_minutes)

    # Pre-extract exam and questions before any DB commit occurs
    exam_id = exam.id
    exam_title = exam.title
    duration_delta = timedelta(minutes=exam.duration_minutes)

    eqs = sorted(exam.exam_questions, key=lambda x: x.order_index) if exam.exam_questions else []
    questions_candidate: List[QuestionCandidateResponse] = []
    for eq in eqs:
        q = eq.question
        if q:
            pts = eq.points_override if eq.points_override is not None else q.points
            questions_candidate.append(
                QuestionCandidateResponse(
                    id=q.id,
                    type=q.type,
                    title=q.title,
                    content_rich_text=q.content_rich_text,
                    options=q.options,
                    points=float(pts),
                    order_index=eq.order_index,
                )
            )

    # 4. Check existing session for candidate FIRST
    session_query = (
        select(ExamSession)
        .options(selectinload(ExamSession.responses))
        .where(
            ExamSession.exam_id == payload.exam_id,
            ExamSession.candidate_id == current_user.id,
        )
    )
    s_res = await db.execute(session_query)
    session = s_res.scalar_one_or_none()

    resp_map: Dict[str, Any] = {}
    flagged_count = 0

    if session:
        if session.status == SessionStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam session has already been submitted",
            )
        if session.status == SessionStatus.EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam session has expired",
            )

        server_end = ensure_utc(session.server_end_time)
        if now > server_end + timedelta(seconds=30):
            session.status = SessionStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam session has expired",
            )

        # Extract responses
        if session.responses:
            for r in session.responses:
                resp_map[str(r.question_id)] = {
                    "question_id": str(r.question_id),
                    "response_data": r.response_data,
                    "is_flagged": r.is_flagged,
                    "sequence_id": r.sequence_id,
                    "server_timestamp": r.server_timestamp.isoformat(),
                }
                if r.is_flagged:
                    flagged_count += 1

        session_id = session.id
        session_status = session.status
        session_started_at = session.started_at
        session_server_end_time = session.server_end_time

    else:
        # 5. Check scheduling window & late entry tolerance for new sessions
        if now < start_utc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam window has not opened yet",
            )
        if now > end_utc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam window has already ended",
            )
        if now > late_entry_deadline:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Late entry window has expired",
            )

        # Create new session
        server_end_time = min(now + duration_delta, end_utc)

        session = ExamSession(
            exam_id=exam_id,
            candidate_id=current_user.id,
            status=SessionStatus.IN_PROGRESS,
            started_at=now,
            server_end_time=server_end_time,
            client_state={},
        )
        db.add(session)
        await db.flush()

        # Update enrollment status
        enroll_res = await db.execute(
            select(ExamEnrollment).where(
                ExamEnrollment.exam_id == payload.exam_id,
                ExamEnrollment.candidate_id == current_user.id,
            )
        )
        enrollment = enroll_res.scalar_one_or_none()
        if enrollment and enrollment.status == ExamEnrollmentStatus.ENROLLED:
            enrollment.status = ExamEnrollmentStatus.IN_PROGRESS

        await log_audit_event(
            db=db,
            action="EXAM_SESSION_STARTED",
            resource_type="exam_session",
            resource_id=str(session.id),
            details={"exam_id": str(exam_id), "candidate_id": str(current_user.id)},
            user_id=current_user.id,
            institution_id=current_user.institution_id,
        )
        await db.commit()

        session_id = session.id
        session_status = session.status
        session_started_at = session.started_at
        session_server_end_time = session.server_end_time

    server_end = ensure_utc(session_server_end_time)
    remaining_secs = max(0, int((server_end - now).total_seconds()))

    return SessionStateResponse(
        session_id=session_id,
        exam_id=exam_id,
        exam_title=exam_title,
        status=session_status,
        started_at=session_started_at,
        server_end_time=session_server_end_time,
        remaining_seconds=remaining_secs,
        is_expired=(remaining_secs <= 0),
        questions=questions_candidate,
        responses=resp_map,
        total_questions=len(questions_candidate),
        answered_count=len(resp_map),
        flagged_count=flagged_count,
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session_state(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    query = (
        select(ExamSession)
        .options(
            selectinload(ExamSession.exam).selectinload(Exam.exam_questions).selectinload(ExamQuestion.question),
            selectinload(ExamSession.responses),
        )
        .where(ExamSession.id == session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Only session candidate or admin/proctor can access
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Extract all data before potential commit
    exam = session.exam
    exam_id = exam.id if exam else session.exam_id
    exam_title = exam.title if exam else "Exam"
    eqs = sorted(exam.exam_questions, key=lambda x: x.order_index) if (exam and exam.exam_questions) else []
    questions_candidate: List[QuestionCandidateResponse] = []
    for eq in eqs:
        q = eq.question
        if q:
            pts = eq.points_override if eq.points_override is not None else q.points
            questions_candidate.append(
                QuestionCandidateResponse(
                    id=q.id,
                    type=q.type,
                    title=q.title,
                    content_rich_text=q.content_rich_text,
                    options=q.options,
                    points=float(pts),
                    order_index=eq.order_index,
                )
            )

    resp_map: Dict[str, Any] = {}
    flagged_count = 0
    if session.responses:
        for r in session.responses:
            resp_map[str(r.question_id)] = {
                "question_id": str(r.question_id),
                "response_data": r.response_data,
                "is_flagged": r.is_flagged,
                "sequence_id": r.sequence_id,
                "server_timestamp": r.server_timestamp.isoformat(),
            }
            if r.is_flagged:
                flagged_count += 1

    session_id_val = session.id
    session_status = session.status
    session_started_at = session.started_at
    session_server_end_time = session.server_end_time

    # Expiration check
    server_end = ensure_utc(session_server_end_time)
    if session_status == SessionStatus.IN_PROGRESS and now > server_end + timedelta(seconds=30):
        session.status = SessionStatus.EXPIRED
        session_status = SessionStatus.EXPIRED
        await db.commit()

    remaining_secs = max(0, int((server_end - now).total_seconds()))

    return SessionStateResponse(
        session_id=session_id_val,
        exam_id=exam_id,
        exam_title=exam_title,
        status=session_status,
        started_at=session_started_at,
        server_end_time=session_server_end_time,
        remaining_seconds=remaining_secs,
        is_expired=(session_status == SessionStatus.EXPIRED or remaining_secs <= 0),
        questions=questions_candidate,
        responses=resp_map,
        total_questions=len(questions_candidate),
        answered_count=len(resp_map),
        flagged_count=flagged_count,
    )


@router.post("/{session_id}/answers", response_model=AnswerSaveResponse)
async def save_session_answer(
    session_id: uuid.UUID,
    payload: AnswerSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    query = select(ExamSession).where(ExamSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Freeze answers if submitted
    if session.status == SessionStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam session is already submitted. Answer updates not permitted.",
        )

    # Check expiration
    server_end = ensure_utc(session.server_end_time)
    if session.status == SessionStatus.EXPIRED or now > server_end + timedelta(seconds=30):
        session.status = SessionStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam session has expired. Answer updates not permitted.",
        )

    question_check = await db.execute(
        select(ExamQuestion.id).where(
            ExamQuestion.exam_id == session.exam_id,
            ExamQuestion.question_id == payload.question_id,
        )
    )
    if question_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is not part of this exam",
        )

    # Look up existing response for (session_id, question_id)
    resp_query = select(ExamResponse).where(
        ExamResponse.session_id == session_id,
        ExamResponse.question_id == payload.question_id,
    )
    resp_res = await db.execute(resp_query)
    existing_resp = resp_res.scalar_one_or_none()

    if existing_resp:
        # Last-write-wins based on sequence_id
        if payload.sequence_id < existing_resp.sequence_id:
            # Stale update ignored
            return AnswerSaveResponse(
                status="saved",
                question_id=payload.question_id,
                sequence_id=existing_resp.sequence_id,
                server_timestamp=existing_resp.server_timestamp,
            )

        existing_resp.response_data = payload.response_data
        existing_resp.sequence_id = payload.sequence_id
        if payload.is_flagged is not None:
            existing_resp.is_flagged = payload.is_flagged
        existing_resp.client_timestamp = ensure_utc(payload.client_timestamp)
        existing_resp.server_timestamp = now
        await db.commit()
        return AnswerSaveResponse(
            status="saved",
            question_id=payload.question_id,
            sequence_id=payload.sequence_id,
            server_timestamp=now,
        )
    else:
        new_resp = ExamResponse(
            session_id=session.id,
            question_id=payload.question_id,
            response_data=payload.response_data,
            sequence_id=payload.sequence_id,
            is_flagged=payload.is_flagged or False,
            client_timestamp=ensure_utc(payload.client_timestamp),
            server_timestamp=now,
        )
        db.add(new_resp)
        await db.commit()
        return AnswerSaveResponse(
            status="saved",
            question_id=payload.question_id,
            sequence_id=payload.sequence_id,
            server_timestamp=now,
        )


@router.post("/{session_id}/submit", response_model=SessionSubmitResponse)
async def submit_session(
    session_id: uuid.UUID,
    payload: SessionSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    query = select(ExamSession).where(ExamSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if session.status == SessionStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam session has already been submitted",
        )

    submission_time = now
    if session.status == SessionStatus.EXPIRED:
        # A timer-triggered submit may arrive after the server marks the
        # session expired. Finalize it idempotently as a timed submission.
        submission_time = ensure_utc(session.server_end_time) or now
    session.status = SessionStatus.SUBMITTED
    session.submitted_at = submission_time
    session.updated_at = now

    # Update candidate enrollment status if exists
    enroll_res = await db.execute(
        select(ExamEnrollment).where(
            ExamEnrollment.exam_id == session.exam_id,
            ExamEnrollment.candidate_id == session.candidate_id,
        )
    )
    enrollment = enroll_res.scalar_one_or_none()
    if enrollment:
        enrollment.status = ExamEnrollmentStatus.COMPLETED
        enrollment.updated_at = now

    await db.commit()
    await db.refresh(session)

    await log_audit_event(
        db=db,
        action="EXAM_SESSION_SUBMITTED",
        resource_type="exam_session",
        resource_id=str(session.id),
        details={"exam_id": str(session.exam_id), "submitted_at": now.isoformat()},
        user_id=current_user.id,
        institution_id=current_user.institution_id,
    )
    await db.commit()

    return SessionSubmitResponse(
        status="submitted",
        submitted_at=session.submitted_at,
        session_id=session.id,
    )
