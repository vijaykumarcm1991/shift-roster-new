"""Team ORM model."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Team(Base, TimestampMixin):
    """A logical grouping of employees (e.g. department / squad)."""

    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_display_order", "display_order"),
        Index("ix_teams_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        back_populates="team",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Team id={self.id} name={self.team_name!r}>"
