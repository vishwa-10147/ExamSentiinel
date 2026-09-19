from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.session import ExamSession, SessionStatus
from app.models.exam import Exam
from app.models.batch import Batch

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Global metrics for Dean's Dashboard."""
    # Total Exams
    total_exams = (await db.execute(select(func.count(Exam.id)))).scalar_one_or_none() or 0
    
    # Total Completed Sessions
    completed_sessions = (await db.execute(
        select(func.count(ExamSession.id))
        .where(ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]))
    )).scalar_one_or_none() or 0
    
    # Average Risk Score
    avg_risk = (await db.execute(
        select(func.avg(ExamSession.current_risk_score))
        .where(ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]))
    )).scalar_one_or_none() or 0.0
    
    return {
        "total_exams": total_exams,
        "completed_sessions": completed_sessions,
        "average_risk_score": float(avg_risk)
    }

@router.get("/batch-performance")
async def get_batch_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Compare average risk and completion rates across Batches."""
    query = (
        select(
            Batch.name,
            func.count(ExamSession.id).label("total_students"),
            func.avg(ExamSession.current_risk_score).label("avg_risk")
        )
        .select_from(ExamSession)
        .join(User, ExamSession.candidate_id == User.id)
        .join(Batch, User.batch_id == Batch.id)
        .group_by(Batch.name)
    )
    
    result = await db.execute(query)
    
    data = []
    for row in result.all():
        data.append({
            "batch_name": row.name,
            "total_students": row.total_students,
            "avg_risk": float(row.avg_risk or 0.0)
        })
        
    return data
