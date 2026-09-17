import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.session import ExamSession
from app.models.exam import Exam

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/history")
async def get_my_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.exam))
        .where(ExamSession.candidate_id == current_user.id)
        .where(ExamSession.status == "SUBMITTED")
        .order_by(desc(ExamSession.submitted_at))
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "session_id": str(s.id),
            "exam_id": str(s.exam_id),
            "exam_name": s.exam.title if s.exam else "Unknown",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "total_score": s.total_score if s.results_published else None,
            "percentage": s.percentage if s.results_published else None,
            "results_published": s.results_published,
        }
        for s in sessions
    ]

@router.get("/exam/{exam_id}/leaderboard")
async def get_exam_leaderboard(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only published results are on the leaderboard
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.candidate))
        .where(ExamSession.exam_id == exam_id)
        .where(ExamSession.status == "SUBMITTED")
        .where(ExamSession.results_published == True)
        .order_by(desc(ExamSession.total_score))
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    leaderboard = []
    for idx, s in enumerate(sessions):
        leaderboard.append({
            "rank": idx + 1,
            "session_id": str(s.id),
            "candidate_name": s.candidate.full_name if s.candidate else "Unknown",
            "total_score": s.total_score,
            "percentage": s.percentage,
            "is_me": (s.candidate_id == current_user.id)
        })
    return leaderboard

@router.post("/publish/{exam_id}")
async def publish_results(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    query = select(ExamSession).where(ExamSession.exam_id == exam_id)
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for s in sessions:
        s.results_published = True
        
    await db.commit()
    return {"status": "success", "published_count": len(sessions)}
@router.get("/admin/exam/{exam_id}/sessions")
async def get_exam_sessions_admin(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER, UserRole.PROCTOR])),
):
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.candidate))
        .where(ExamSession.exam_id == exam_id)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "candidate_id": str(s.candidate_id),
            "candidate_name": s.candidate.full_name if s.candidate else "Unknown",
            "status": s.status,
            "score": s.total_score,
            "integrity_score": s.current_risk_score,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "results_published": s.results_published
        }
        for s in sessions
    ]

