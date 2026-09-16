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