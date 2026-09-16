"""Human review queue and evidence endpoints."""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.proctoring_event import ProctoringEvent
from app.models.review_case import ReviewAction, ReviewCase, ReviewStatus
from app.models.session import ExamSession
from app.models.user import User, UserRole
from app.schemas.review import ReviewActionCreate, ReviewCaseList, ReviewCaseResponse

router = APIRouter(prefix="/reviews", tags=["Human Review"])
_REVIEW_ROLES = [UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER]
_ACTION_STATUS = {
    "START_REVIEW": ReviewStatus.IN_REVIEW,
    "DISMISS": ReviewStatus.DISMISSED,
    "ESCALATE": ReviewStatus.ESCALATED,
    "CONFIRM": ReviewStatus.CONFIRMED,
}


@router.get("", response_model=ReviewCaseList)
async def list_review_cases(
    status_filter: ReviewStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    filters = [ReviewCase.candidate_id.is_not(None)]
    if status_filter is not None:
        filters.append(ReviewCase.status == status_filter)

    total = (await db.execute(select(func.count(ReviewCase.id)).where(*filters))).scalar_one()
    result = await db.execute(
        select(ReviewCase)
        .options(selectinload(ReviewCase.actions))
        .where(*filters)
        .order_by(ReviewCase.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ReviewCaseList(
        items=[ReviewCaseResponse.model_validate(case) for case in result.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=ReviewCaseResponse)
async def get_review_case(
    case_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReviewCase)
        .options(selectinload(ReviewCase.actions))
        .where(ReviewCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review case not found")
    return ReviewCaseResponse.model_validate(case)


@router.get("/{case_id}/evidence")
async def get_review_evidence(
    case_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    case_result = await db.execute(select(ReviewCase).where(ReviewCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review case not found")

    event_result = await db.execute(
        select(ProctoringEvent)
        .where(ProctoringEvent.session_id == case.session_id)
        .order_by(ProctoringEvent.created_at.asc())
    )
    events = event_result.scalars().all()
    return {
        "case_id": case.id,
        "session_id": case.session_id,
        "risk_score_at_creation": case.risk_score_at_creation,
        "risk_level_at_creation": case.risk_level_at_creation,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "category": event.category,
                "severity": event.severity,
                "details": event.details,
                "snapshot_url": event.snapshot_url,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


@router.post("/{case_id}/actions", response_model=ReviewCaseResponse)
async def act_on_review_case(
    case_id: uuid.UUID,
    payload: ReviewActionCreate,
    current_user: User = Depends(require_roles(_REVIEW_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    action = payload.action.upper()
    new_status = _ACTION_STATUS.get(action)
    if new_status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported review action: {payload.action}",
        )

    result = await db.execute(
        select(ReviewCase)
        .options(selectinload(ReviewCase.actions))
        .where(ReviewCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review case not found")
    if case.status in {ReviewStatus.DISMISSED, ReviewStatus.CONFIRMED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review case is already resolved")

    previous_status = case.status
    case.status = new_status
    case.assigned_reviewer_id = current_user.id
    if new_status in {ReviewStatus.DISMISSED, ReviewStatus.ESCALATED, ReviewStatus.CONFIRMED}:
        case.resolution_notes = payload.notes
        case.resolved_at = datetime.now(timezone.utc)
        case.resolved_by = current_user.id
    db.add(
        ReviewAction(
            review_case_id=case.id,
            reviewer_id=current_user.id,
            action=action,
            notes=payload.notes,
            previous_status=previous_status,
            new_status=new_status,
        )
    )
    await log_audit_event(
        db=db,
        action=f"REVIEW_{action}",
        resource_type="review_case",
        resource_id=str(case.id),
        details={"previous_status": previous_status.value, "new_status": new_status.value, "notes": payload.notes},
        user_id=current_user.id,
        institution_id=current_user.institution_id,
    )
    await db.commit()
    await db.refresh(case)
    return ReviewCaseResponse.model_validate(case)