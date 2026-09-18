import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.institution import Institution
    from app.models.user import User

class Batch(TimeStampedUUIDModel):
    __tablename__ = "batches"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    grad_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_institution_batch_name"),
    )

    institution: Mapped["Institution"] = relationship("Institution", back_populates="batches")
    users: Mapped[List["User"]] = relationship("User", back_populates="batch")
