"""ShiftType ORM model."""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.roster import Roster


class ShiftType(Base, TimestampMixin):
    """A defined shift code (e.g. S1, S2, WO, GH) with a display color."""

    __tablename__ = "shift_types"
    __table_args__ = (
        Index("ix_shift_types_display_order", "display_order"),
        Index("ix_shift_types_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(
        String(16), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    roster_entries: Mapped[List["Roster"]] = relationship(
        "Roster",
        back_populates="shift_type",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ShiftType id={self.id} code={self.code!r}>"
