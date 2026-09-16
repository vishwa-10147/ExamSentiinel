"""Risk weight configuration for the risk scoring engine."""

from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.institution import Institution


class RiskWeight(TimeStampedUUIDModel):
    """Configurable weight for a specific event type used by the risk engine.

    When ``institution_id`` is ``NULL`` the row acts as the global default.
    Institution-specific rows override the global default for that
    event type.
    """

    __tablename__ = "risk_weights"

    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "event_type",
            name="uq_institution_event_type_weight",
        ),
    )

    # Relationships
    institution: Mapped[Optional["Institution"]] = relationship("Institution")
