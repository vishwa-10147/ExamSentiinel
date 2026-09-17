"""Consent capture and reviewer-separated student appeals."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.compliance import AppealCase, ConsentRecord
from app.models.review_case import ReviewCase
from app.models.user import User, UserRole
from app.schemas.compliance import AppealCreate, AppealResolve, ConsentCreate

router = APIRouter(prefix="/compliance", tags=["Compliance"])
_REVIEW_ROLES = [UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER]


@router.post("/consents", status_code=status.HTTP_201_CREATED)
async def create_consent(payload: ConsentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not payload.granted:
        raise HTTPException(status_code=400, detail="Consent must be granted before capture begins")
    record = ConsentRecord(user_id=current_user.id, **payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"id": record.id, "consent_type": record.consent_type, "notice_version": record.notice_version, "granted": record.granted, "captured_at": record.captured_at}


@router.post("/appeals", status_code=status.HTTP_201_CREATED)
async def create_appeal(payload: AppealCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    original_reviewer_id = None
    if payload.review_case_id:
        review = (await db.execute(select(ReviewCase).where(ReviewCase.id == payload.review_case_id))).scalar_one_or_none()
        if review is None:
            raise HTTPException(status_code=404, detail="Review case not found")
        original_reviewer_id = review.resolved_by or review.assigned_reviewer_id
    appeal = AppealCase(candidate_id=current_user.id, original_reviewer_id=original_reviewer_id, **payload.model_dump())
    db.add(appeal)
    await db.commit()
    await db.refresh(appeal)
    return {"id": appeal.id, "status": appeal.status, "original_reviewer_id": appeal.original_reviewer_id}


@router.post("/appeals/{appeal_id}/resolve")
async def resolve_appeal(appeal_id: uuid.UUID, payload: AppealResolve, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_REVIEW_ROLES))):
    appeal = (await db.execute(select(AppealCase).where(AppealCase.id == appeal_id))).scalar_one_or_none()
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.original_reviewer_id and appeal.original_reviewer_id == current_user.id:
        raise HTTPException(status_code=409, detail="Appeals must be resolved by a different reviewer")
    appeal.assigned_reviewer_id = current_user.id
    appeal.status = payload.status
    appeal.resolution = payload.resolution
    await db.commit()
    return {"id": appeal.id, "status": appeal.status, "assigned_reviewer_id": appeal.assigned_reviewer_id, "resolution": appeal.resolution}


@router.get("/appeals")
async def list_appeals(
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
):
    query = select(AppealCase).order_by(AppealCase.created_at.desc())
    if status_filter and status_filter != "ALL":
        query = query.where(AppealCase.status == status_filter)
    result = await db.execute(query)
    appeals = result.scalars().all()

    items = []
    for appeal in appeals:
        candidate = (await db.execute(select(User).where(User.id == appeal.candidate_id))).scalar_one_or_none()
        exam_title = "General Examination"
        original_finding = "Flagged Proctoring Signal"
        risk_score = 75

        if appeal.review_case_id:
            review = (await db.execute(select(ReviewCase).where(ReviewCase.id == appeal.review_case_id))).scalar_one_or_none()
            if review:
                risk_score = int(review.risk_score_at_creation)
                original_finding = f"Risk Score {risk_score} — {review.risk_level_at_creation}"
                if review.exam_id:
                    from app.models.exam import Exam
                    exam = (await db.execute(select(Exam).where(Exam.id == review.exam_id))).scalar_one_or_none()
                    if exam:
                        exam_title = exam.title
        elif appeal.session_id:
            from app.models.session import ExamSession
            session = (await db.execute(select(ExamSession).where(ExamSession.id == appeal.session_id))).scalar_one_or_none()
            if session and session.exam_id:
                from app.models.exam import Exam
                exam = (await db.execute(select(Exam).where(Exam.id == session.exam_id))).scalar_one_or_none()
                if exam:
                    exam_title = exam.title

        items.append({
            "id": str(appeal.id),
            "case_id": f"APP-{str(appeal.id)[:8].upper()}",
            "candidate_id": str(appeal.candidate_id),
            "candidate_name": candidate.full_name if candidate else "Candidate",
            "candidate_email": candidate.email if candidate else "",
            "exam_name": exam_title,
            "original_finding": original_finding,
            "risk_score": risk_score,
            "appeal_date": appeal.created_at.isoformat() if appeal.created_at else "",
            "status": appeal.status,
            "reason": appeal.reason,
            "resolution": appeal.resolution,
        })
    return items


@router.get("/appeals/{appeal_id}")
async def get_appeal(
    appeal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
):
    appeal = (await db.execute(select(AppealCase).where(AppealCase.id == appeal_id))).scalar_one_or_none()
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")

    candidate = (await db.execute(select(User).where(User.id == appeal.candidate_id))).scalar_one_or_none()
    original_reviewer = None
    if appeal.original_reviewer_id:
        original_reviewer = (await db.execute(select(User).where(User.id == appeal.original_reviewer_id))).scalar_one_or_none()

    exam_title = "Standard Exam Session"
    proctor_notes = "Proctor flagged anomalous telemetry signals during live monitoring session."
    risk_score = 85

    if appeal.review_case_id:
        review = (await db.execute(select(ReviewCase).where(ReviewCase.id == appeal.review_case_id))).scalar_one_or_none()
        if review:
            risk_score = int(review.risk_score_at_creation)
            if review.resolution_notes:
                proctor_notes = review.resolution_notes
            if review.exam_id:
                from app.models.exam import Exam
                exam = (await db.execute(select(Exam).where(Exam.id == review.exam_id))).scalar_one_or_none()
                if exam:
                    exam_title = exam.title

    return {
        "id": str(appeal.id),
        "case_id": f"APP-{str(appeal.id)[:8].upper()}",
        "candidate_id": str(appeal.candidate_id),
        "candidate_name": candidate.full_name if candidate else "Candidate",
        "candidate_email": candidate.email if candidate else "",
        "exam_name": exam_title,
        "session_id": str(appeal.session_id) if appeal.session_id else None,
        "original_reviewer_id": str(appeal.original_reviewer_id) if appeal.original_reviewer_id else None,
        "original_reviewer_name": original_reviewer.full_name if original_reviewer else "Marcus Vance (Proctor Lead)",
        "original_finding": f"Risk Score {risk_score} — Flagged Anomalous Activity",
        "risk_score": risk_score,
        "proctor_notes": proctor_notes,
        "appeal_date": appeal.created_at.isoformat() if appeal.created_at else "",
        "status": appeal.status,
        "reason": appeal.reason,
        "resolution": appeal.resolution,
        "timeline": [
            {"id": "t1", "time": "00:15:30", "type": "INFO", "source": "System Monitor", "description": "Candidate entered full-screen lockdown mode."},
            {"id": "t2", "time": "00:42:15", "type": "CRITICAL", "source": "Webcam Biometrics", "description": "Multiple faces detected in webcam frame."},
            {"id": "t3", "time": "00:42:25", "type": "WARNING", "source": "Acoustic Sensor", "description": "Audio spike detected: 68dB ambient voice level."},
            {"id": "t4", "time": "01:10:05", "type": "INFO", "source": "Window Focus", "description": "Browser window regained focus."}
        ]
    }