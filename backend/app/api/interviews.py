"""Live technical interviews: consent, WebRTC rooms, transcription and human scoring.

Video/audio flows browser-to-browser (WebRTC); this API only relays the
signalling (see ``interview_ws.py``), transcribes the candidate's audio clips
and stores the transcript and the interviewer's scores. Nothing is captured
before the candidate gives recording consent.
"""

import asyncio
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.exam import Exam
from app.models.interview import InterviewScore, InterviewSession
from app.models.session import ExamSession
from app.models.user import User, UserRole
from app.schemas.interview import (
    InterviewConsentRequest,
    InterviewCreate,
    InterviewScoreCreate,
    InterviewStatusUpdate,
    InterviewTopicsUpdate,
    InterviewTranscriptUpdate,
)
from app.services.transcription_service import TranscriptionUnavailable, topic_coverage, transcription_service

router = APIRouter(prefix="/interviews", tags=["Interviews"])
_STAFF = [UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER]
MAX_AUDIO_BYTES = 5 * 1024 * 1024


async def _load(db: AsyncSession, interview_id: uuid.UUID, user: User) -> tuple[InterviewSession, ExamSession]:
    """The interview and its exam session, if *user* is the candidate or staff."""
    interview = await db.get(InterviewSession, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    session = await db.get(ExamSession, interview.exam_session_id)
    if user.role == UserRole.CANDIDATE and (session is None or session.candidate_id != user.id):
        raise HTTPException(status_code=404, detail="Interview session not found")
    return interview, session


def _transcript(interview: InterviewSession) -> dict:
    data = dict(interview.transcript or {})
    data.setdefault("segments", [])
    data.setdefault("topics", [])
    return data


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
        return {"id": existing.id, "mode": existing.mode, "status": existing.status, "room_name": existing.room_name,
                "recording_consent": existing.recording_consent}
    room_name = f"exam-{session.id}" if payload.mode == "LIVE" else None
    interview = InterviewSession(exam_session_id=session.id, mode=payload.mode, status="SCHEDULED", room_name=room_name,
                                 transcript={"segments": [], "topics": []})
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return {"id": interview.id, "mode": interview.mode, "status": interview.status, "room_name": interview.room_name,
            "recording_consent": False}


@router.get("")
async def list_interviews(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_STAFF)),
):
    """Interviews for the interviewer console, newest first."""
    query = (
        select(InterviewSession, ExamSession, User, Exam)
        .join(ExamSession, ExamSession.id == InterviewSession.exam_session_id)
        .join(User, User.id == ExamSession.candidate_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .order_by(InterviewSession.created_at.desc())
        .limit(200)
    )
    if status_filter:
        query = query.where(InterviewSession.status == status_filter.upper())
    rows = (await db.execute(query)).all()
    return [
        {
            "id": str(i.id), "status": i.status, "mode": i.mode, "recording_consent": i.recording_consent,
            "candidate_name": u.full_name, "candidate_email": u.email, "exam_title": e.title,
            "segments": len((i.transcript or {}).get("segments", [])), "created_at": i.created_at.isoformat(),
        }
        for i, s, u, e in rows
    ]


@router.get("/{interview_id}")
async def get_interview(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview, session = await _load(db, interview_id, current_user)
    candidate = await db.get(User, session.candidate_id) if session else None
    exam = await db.get(Exam, session.exam_id) if session else None
    data = _transcript(interview)
    is_staff = current_user.role in _STAFF
    response = {
        "id": str(interview.id),
        "status": interview.status,
        "mode": interview.mode,
        "recording_consent": interview.recording_consent,
        "role": "interviewer" if is_staff else "candidate",
        "candidate_name": candidate.full_name if candidate else None,
        "exam_title": exam.title if exam else None,
        "segments": data["segments"],
        "transcription_available": transcription_service.available,
    }
    if is_staff:  # topics and scores are the interviewer's working notes
        response["topics"] = data["topics"]
        response["coverage"] = topic_coverage(data["topics"], data["segments"])
        scores = (await db.execute(
            select(InterviewScore).where(InterviewScore.interview_session_id == interview.id).order_by(InterviewScore.created_at)
        )).scalars().all()
        response["scores"] = [
            {"id": str(s.id), "criterion_scores": s.criterion_scores, "notes": s.notes, "created_at": s.created_at.isoformat()}
            for s in scores
        ]
    return response


@router.post("/{interview_id}/consent")
async def record_interview_consent(
    interview_id: uuid.UUID,
    payload: InterviewConsentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview, session = await _load(db, interview_id, current_user)
    # Only the candidate can consent to being recorded.
    if session is None or session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the candidate can give recording consent")
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Recording consent is required before interview capture")
    interview.recording_consent = True
    if interview.status == "SCHEDULED":
        interview.status = "READY"
    await log_audit_event(db=db, action="INTERVIEW_CONSENT_GIVEN", resource_type="interview", resource_id=str(interview.id),
                          details={"notice_version": payload.notice_version}, user_id=current_user.id,
                          institution_id=current_user.institution_id)
    await db.commit()
    return {"interview_id": interview.id, "recording_consent": True, "notice_version": payload.notice_version, "status": interview.status}


@router.post("/{interview_id}/status")
async def update_interview_status(
    interview_id: uuid.UUID,
    payload: InterviewStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_STAFF)),
):
    interview, _ = await _load(db, interview_id, current_user)
    interview.status = payload.status
    await db.commit()
    return {"id": str(interview.id), "status": interview.status}


@router.put("/{interview_id}/topics")
async def update_topics(
    interview_id: uuid.UUID,
    payload: InterviewTopicsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_STAFF)),
):
    interview, _ = await _load(db, interview_id, current_user)
    data = _transcript(interview)
    data["topics"] = payload.topics
    interview.transcript = data
    await db.commit()
    return {"topics": data["topics"], "coverage": topic_coverage(data["topics"], data["segments"])}


@router.post("/{interview_id}/audio")
async def upload_audio_clip(
    interview_id: uuid.UUID,
    clip: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The candidate's browser sends short standalone clips; each is transcribed and appended."""
    interview, session = await _load(db, interview_id, current_user)
    if session is None or session.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the candidate's own audio is transcribed")
    if not interview.recording_consent:
        raise HTTPException(status_code=409, detail="Recording consent has not been given")
    if interview.status not in ("READY", "LIVE"):
        raise HTTPException(status_code=409, detail="This interview is not in progress")
    audio = await clip.read()
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio clip exceeds 5 MB")
    if len(audio) < 1000:
        return {"segments": []}  # silence / empty clip
    try:
        result = await asyncio.to_thread(transcription_service.transcribe, audio)
    except TranscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = datetime.now(timezone.utc).isoformat()
    new_segments = [{"speaker": "candidate", "at": now, **seg} for seg in result["segments"]]
    # Re-read inside this request's transaction so concurrent clips don't overwrite each other.
    await db.refresh(interview)
    data = _transcript(interview)
    data["segments"] = data["segments"] + new_segments
    data["language"] = result["language"]
    interview.transcript = data
    await db.commit()
    return {"segments": new_segments, "language": result["language"]}


@router.post("/{interview_id}/scores", status_code=status.HTTP_201_CREATED)
async def submit_interview_score(
    interview_id: uuid.UUID,
    payload: InterviewScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_STAFF)),
):
    interview, _ = await _load(db, interview_id, current_user)
    score = InterviewScore(interview_session_id=interview.id, reviewer_id=current_user.id,
                           criterion_scores=payload.criterion_scores, notes=payload.notes)
    db.add(score)
    await db.commit()
    await db.refresh(score)
    return {"id": score.id, "reviewer_id": score.reviewer_id, "criterion_scores": score.criterion_scores, "notes": score.notes}


@router.put("/{interview_id}/transcript")
async def update_transcript(
    interview_id: uuid.UUID,
    payload: InterviewTranscriptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_STAFF)),
):
    """Staff correction of the transcript (topics are preserved)."""
    interview, _ = await _load(db, interview_id, current_user)
    data = _transcript(interview)
    data["segments"] = payload.segments
    if payload.language:
        data["language"] = payload.language
    interview.transcript = data
    await db.commit()
    return {"interview_id": interview.id, "transcript": interview.transcript,
            "transcription_provider_configured": transcription_service.available}
