from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.institution import Institution
from app.models.user import User, UserRole


router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])

DEFAULT_SETTINGS = {
    "support_email": "support@sentinel.edu",
    "timezone": "UTC",
    "enforce_admin_2fa": True,
    "evidence_retention_days": 30,
    "critical_risk_email_alerts": True,
}


class AdminSettingsResponse(BaseModel):
    institution_name: str
    support_email: EmailStr
    timezone: str
    enforce_admin_2fa: bool
    evidence_retention_days: int = Field(ge=1, le=3650)
    critical_risk_email_alerts: bool


class AdminSettingsUpdate(BaseModel):
    institution_name: str | None = Field(default=None, min_length=1, max_length=255)
    support_email: EmailStr | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    enforce_admin_2fa: bool | None = None
    evidence_retention_days: int | None = Field(default=None, ge=1, le=3650)
    critical_risk_email_alerts: bool | None = None


async def _get_institution(current_user: User, db: AsyncSession) -> Institution:
    if not current_user.institution_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin is not assigned to an institution")
    institution = await db.get(Institution, current_user.institution_id)
    if institution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    return institution


def _to_response(institution: Institution) -> AdminSettingsResponse:
    values: dict[str, Any] = {**DEFAULT_SETTINGS, **(institution.settings or {})}
    return AdminSettingsResponse(
        institution_name=institution.name,
        support_email=values["support_email"],
        timezone=values["timezone"],
        enforce_admin_2fa=values["enforce_admin_2fa"],
        evidence_retention_days=values["evidence_retention_days"],
        critical_risk_email_alerts=values["critical_risk_email_alerts"],
    )


@router.get("", response_model=AdminSettingsResponse)
async def get_admin_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    return _to_response(await _get_institution(current_user, db))


@router.put("", response_model=AdminSettingsResponse)
async def update_admin_settings(
    payload: AdminSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    institution = await _get_institution(current_user, db)
    changes = payload.model_dump(exclude_unset=True)
    if "institution_name" in changes:
        institution.name = changes.pop("institution_name")
    settings = {**DEFAULT_SETTINGS, **(institution.settings or {}), **changes}
    institution.settings = settings
    await db.commit()
    await db.refresh(institution)
    return _to_response(institution)
