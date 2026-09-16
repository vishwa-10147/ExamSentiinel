"""
REST API endpoints for the admin monitoring dashboard.

All endpoints require ADMIN or PROCTOR role.  Data returned is always
reviewer-facing signals — no auto-verdicts are ever produced.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.exam import Exam, ExamStatus
from app.models.session import ExamSession, SessionStatus
from app.models.risk_score_history import RiskScoreHistory
from app.models.user import User, UserRole

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Roles permitted to access the monitoring dashboard
_DASHBOARD_ROLES = [UserRole.ADMIN, UserRole.PROCTOR]

# Risk level thresholds (aligned with risk scoring pipeline)
_HIGH_RISK_THRESHOLD = 0.7
_MEDIUM_RISK_THRESHOLD = 0.4


# --------------------------------------------------------------------------
# Response schemas
# --------------------------------------------------------------------------

class SessionSummary(BaseModel):
    """Summary view of an active exam session for the dashboard."""
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    status: str
    current_risk_score: float
    risk_level: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    server_end_time: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Aggregate statistics for the admin dashboard overview."""
    active_exams: int
    total_active_sessions: int
    in_progress_sessions: int
    submitted_sessions: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    average_risk_score: float

    model_config = ConfigDict(from_attributes=True)


class RiskTimelineEntry(BaseModel):
    """A single point on the risk score timeline."""
    risk_score: float
    risk_level: str
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionTimeline(BaseModel):
    """Risk score timeline for a single session."""
    session_id: uuid.UUID
    exam_id: uuid.UUID
    candidate_name: str
    current_risk_score: float
    current_risk_level: str
    timeline: List[RiskTimelineEntry]

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Helper: build session summary from ORM objects
# --------------------------------------------------------------------------

def _build_session_summary(session: ExamSession) -> Dict[str, Any]:
    """Convert an ExamSession with eagerly-loaded relationships to a dict."""
    return {
        "session_id": session.id,
        "exam_id": session.exam_id,
        "exam_title": session.exam.title if session.exam else "Unknown",
        "candidate_id": session.candidate_id,
        "candidate_name": session.candidate.full_name if session.candidate else "Unknown",
        "candidate_email": session.candidate.email if session.candidate else "Unknown",
        "status": session.status.value if isinstance(session.status, SessionStatus) else session.status,
        "current_risk_score": session.current_risk_score,
        "risk_level": session.risk_level,
        "started_at": session.started_at,
        "submitted_at": session.submitted_at,
        "server_end_time": session.server_end_time,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/active-sessions",
    response_model=List[SessionSummary],
    summary="List all active exam sessions with risk scores",
)
async def list_active_sessions(
    risk_level: Optional[str] = Query(
        None,
        description="Filter by risk level: LOW, MEDIUM, HIGH",
        pattern="^(LOW|MEDIUM|HIGH)$",
    ),
    sort_by: str = Query(
        "risk_score",
        description="Sort field: risk_score, started_at, candidate_name",
        pattern="^(risk_score|started_at|candidate_name)$",
    ),
    sort_order: str = Query(
        "desc",
        description="Sort order: asc, desc",
        pattern="^(asc|desc)$",
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(_DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all active (IN_PROGRESS or READY) exam sessions with risk scores.

    Results can be filtered by risk level and sorted by risk score,
    start time, or candidate name.
    """
    stmt = (
        select(ExamSession)
        .options(joinedload(ExamSession.exam), joinedload(ExamSession.candidate))
        .where(ExamSession.status.in_([SessionStatus.IN_PROGRESS, SessionStatus.READY]))
    )

    # Optional risk-level filter
    if risk_level:
        stmt = stmt.where(ExamSession.risk_level == risk_level)

    # Sorting
    sort_column_map = {
        "risk_score": ExamSession.current_risk_score,
        "started_at": ExamSession.started_at,
        "candidate_name": ExamSession.candidate_id,  # fallback; ideally join sort
    }
    sort_col = sort_column_map.get(sort_by, ExamSession.current_risk_score)
    stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    sessions = result.unique().scalars().all()

    return [_build_session_summary(s) for s in sessions]


@router.get(
    "/active-sessions/{exam_id}",
    response_model=List[SessionSummary],
    summary="List active sessions for a specific exam",
)
async def list_active_sessions_for_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(_DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all active sessions for a specific exam, ordered by risk score descending."""
    # Verify exam exists
    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam {exam_id} not found",
        )

    stmt = (
        select(ExamSession)
        .options(joinedload(ExamSession.exam), joinedload(ExamSession.candidate))
        .where(
            ExamSession.exam_id == exam_id,
            ExamSession.status.in_([SessionStatus.IN_PROGRESS, SessionStatus.READY]),
        )
        .order_by(ExamSession.current_risk_score.desc())
    )

    result = await db.execute(stmt)
    sessions = result.unique().scalars().all()

    return [_build_session_summary(s) for s in sessions]


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Overall monitoring statistics",
)
async def dashboard_stats(
    current_user: User = Depends(require_roles(_DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return aggregate statistics for the admin dashboard overview.

    Includes counts of active exams, sessions by status, risk-level
    distribution, and the average risk score.
    """
    now = datetime.now(timezone.utc)

    # Count active exams (PUBLISHED and within their time window)
    active_exams_result = await db.execute(
        select(func.count(Exam.id)).where(
            Exam.status == ExamStatus.PUBLISHED,
            Exam.start_window <= now,
            Exam.end_window >= now,
        )
    )
    active_exams: int = active_exams_result.scalar() or 0

    # Session counts by status (only non-terminal)
    active_statuses = [SessionStatus.IN_PROGRESS, SessionStatus.READY]

    total_active_result = await db.execute(
        select(func.count(ExamSession.id)).where(
            ExamSession.status.in_(active_statuses),
        )
    )
    total_active: int = total_active_result.scalar() or 0

    in_progress_result = await db.execute(
        select(func.count(ExamSession.id)).where(
            ExamSession.status == SessionStatus.IN_PROGRESS,
        )
    )
    in_progress: int = in_progress_result.scalar() or 0

    submitted_result = await db.execute(
        select(func.count(ExamSession.id)).where(
            ExamSession.status == SessionStatus.SUBMITTED,
        )
    )
    submitted: int = submitted_result.scalar() or 0

    # Risk-level distribution among active sessions
    high_risk_result = await db.execute(
        select(func.count(ExamSession.id)).where(
            ExamSession.status.in_(active_statuses),
            ExamSession.current_risk_score >= _HIGH_RISK_THRESHOLD,
        )
    )
    high_risk: int = high_risk_result.scalar() or 0

    medium_risk_result = await db.execute(
        select(func.count(ExamSession.id)).where(
            ExamSession.status.in_(active_statuses),
            ExamSession.current_risk_score >= _MEDIUM_RISK_THRESHOLD,
            ExamSession.current_risk_score < _HIGH_RISK_THRESHOLD,
        )
    )
    medium_risk: int = medium_risk_result.scalar() or 0

    low_risk: int = total_active - high_risk - medium_risk

    # Average risk score among active sessions
    avg_result = await db.execute(
        select(func.avg(ExamSession.current_risk_score)).where(
            ExamSession.status.in_(active_statuses),
        )
    )
    avg_risk: float = round(float(avg_result.scalar() or 0.0), 4)

    return {
        "active_exams": active_exams,
        "total_active_sessions": total_active,
        "in_progress_sessions": in_progress,
        "submitted_sessions": submitted,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "average_risk_score": avg_risk,
    }


@router.get(
    "/session/{session_id}/timeline",
    response_model=SessionTimeline,
    summary="Risk score timeline for a session",
)
async def session_risk_timeline(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(_DASHBOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the risk score timeline for a specific exam session.

    Currently returns the session's current risk snapshot. When the
    ``risk_score_history`` table is introduced, this endpoint will
    return the full chronological series of risk updates.
    """
    stmt = (
        select(ExamSession)
        .options(joinedload(ExamSession.candidate))
        .where(ExamSession.id == session_id)
    )
    result = await db.execute(stmt)
    session = result.unique().scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    history_result = await db.execute(
        select(RiskScoreHistory)
        .where(RiskScoreHistory.session_id == session_id)
        .order_by(RiskScoreHistory.recorded_at.asc())
    )
    history = history_result.scalars().all()
    timeline = [
        {
            "risk_score": entry.risk_score,
            "risk_level": entry.risk_level,
            "recorded_at": entry.recorded_at,
        }
        for entry in history
    ]
    if not timeline:
        timeline = [{
            "risk_score": session.current_risk_score,
            "risk_level": session.risk_level,
            "recorded_at": session.updated_at,
        }]

    return {
        "session_id": session.id,
        "exam_id": session.exam_id,
        "candidate_name": session.candidate.full_name if session.candidate else "Unknown",
        "current_risk_score": session.current_risk_score,
        "current_risk_level": session.risk_level,
        "timeline": timeline,
    }
