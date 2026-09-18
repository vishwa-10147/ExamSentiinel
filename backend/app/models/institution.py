from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import Boolean, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.audit_log import AuditLog


class Institution(TimeStampedUUIDModel):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Monetization & Billing
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True, unique=True, index=True)
    subscription_tier: Mapped[str] = mapped_column(String(64), default="free", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="institution")
