"""Usage metering and non-interruptive budget alerts."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.usage import BudgetAlert, UsageLog
from app.models.user import User, UserRole
from app.schemas.usage import BudgetAlertCreate, UsageCreate

router = APIRouter(prefix="/usage", tags=["Usage and Budgets"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def record_usage(payload: UsageCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR]))):
    entry = UsageLog(institution_id=payload.institution_id, metric=payload.metric, quantity=payload.quantity, metadata_json=payload.metadata)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    total = (await db.execute(select(func.coalesce(func.sum(UsageLog.quantity), 0.0)).where(UsageLog.institution_id == payload.institution_id, UsageLog.metric == payload.metric))).scalar_one()
    return {"id": entry.id, "metric": payload.metric, "quantity": payload.quantity, "total_usage": float(total)}


@router.post("/alerts", status_code=status.HTTP_201_CREATED)
async def create_budget_alert(payload: BudgetAlertCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles([UserRole.ADMIN]))):
    alert = BudgetAlert(**payload.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return {"id": alert.id, "metric": alert.metric, "threshold": alert.threshold, "current_usage": alert.current_usage, "throttling": "new_work_only"}


@router.get("/{institution_id}")
async def get_usage(institution_id, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR]))):
    result = await db.execute(select(UsageLog.metric, func.sum(UsageLog.quantity)).where(UsageLog.institution_id == institution_id).group_by(UsageLog.metric))
    return {"institution_id": institution_id, "usage": {metric: float(total) for metric, total in result.all()}}