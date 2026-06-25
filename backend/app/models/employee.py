"""Employee ORM model."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.roster import Roster
    from app.models.team import Team


class Employee(Base, TimestampMixin):
    """An employee who can be assigned shifts in the roster."""

    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_team_id", "team_id"),
        Index("ix_employees_is_active", "is_active"),
        Index("ix_employees_team_active", "team_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    employee_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    designation: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="employees")
    roster_entries: Mapped[List["Roster"]] = relationship(
        "Roster",
        back_populates="employee",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Employee id={self.id} code={self.employee_code!r}>"
