"""Institution usage metering and budget alert records."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimeStampedUUIDModel


class UsageLog(TimeStampedUUIDModel):
    __tablename__ = "usage_logs"

    institution_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class BudgetAlert(TimeStampedUUIDModel):
    __tablename__ = "budget_alerts"

    institution_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    current_usage: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_percent: Mapped[int] = mapped_column(default=80, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)