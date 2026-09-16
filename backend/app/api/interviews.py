"""Interview workflow contracts with consent and human scoring."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.interview import InterviewScore, InterviewSession
from app.models.session import ExamSession
from app.models.user import User, UserRole
from app.schemas.interview import InterviewConsentRequest, InterviewCreate, InterviewScoreCreate, InterviewTranscriptUpdate

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_interview(
    payload: InterviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (await db.execute(select(ExamSession).where(ExamSession.id == payload.exam_session_id))).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found")
    if current_user.role == UserRole.CANDIDATE and session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    existing = (await db.execute(select(InterviewSession).where(InterviewSession.exam_session_id == session.id))).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "status": existing.status, "room_name": existing.room_name, "recording_consent": existing.recording_consent}
    room_name = f"exam-{session.id}" if payload.mode == "LIVE" else None
    interview = InterviewSession(exam_session_id=session.id, mode=payload.mode, status="SCHEDULED", room_name=room_name)
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return {"id": interview.id, "mode": interview.mode, "status": interview.status, "room_name": interview.room_name, "provider_configured": bool(os.getenv("LIVEKIT_URL"))}


@router.post("/{interview_id}/consent")
async def record_interview_consent(
    interview_id: uuid.UUID,
    payload: InterviewConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = (await db.execute(select(InterviewSession).where(InterviewSession.id == interview_id))).scalar_one_or_none()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Recording consent is required before interview capture")
    interview.recording_consent = True
    interview.status = "READY"
    await db.commit()
    return {"interview_id": interview.id, "recording_consent": True, "notice_version": payload.notice_version, "status": interview.status}


@router.post("/{interview_id}/scores", status_code=status.HTTP_201_CREATED)
async def submit_interview_score(
    interview_id: uuid.UUID,
    payload: InterviewScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER])),
):
    interview = (await db.execute(select(InterviewSession).where(InterviewSession.id == interview_id))).scalar_one_or_none()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    score = InterviewScore(interview_session_id=interview.id, reviewer_id=current_user.id, criterion_scores=payload.criterion_scores, notes=payload.notes)
    db.add(score)
    await db.commit()
    await db.refresh(score)
    return {"id": score.id, "reviewer_id": score.reviewer_id, "criterion_scores": score.criterion_scores, "notes": score.notes}


@router.put("/{interview_id}/transcript")
async def update_transcript(
    interview_id: uuid.UUID,
    payload: InterviewTranscriptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER])),
):
    interview = (await db.execute(select(InterviewSession).where(InterviewSession.id == interview_id))).scalar_one_or_none()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    interview.transcript = payload.model_dump()
    await db.commit()
    return {"interview_id": interview.id, "transcript": interview.transcript, "transcription_provider_configured": bool(os.getenv("WHISPER_MODEL_SIZE"))}