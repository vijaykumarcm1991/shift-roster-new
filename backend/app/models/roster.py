"""Roster ORM model."""

from __future__ import annotations

from datetime import date
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.shift_type import ShiftType


class Roster(Base, TimestampMixin):
    """A single shift assignment: one employee, one shift, one date."""

    __tablename__ = "roster"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "roster_date",
            name="uq_roster_employee_date",
        ),
        Index("ix_roster_roster_date", "roster_date"),
        Index("ix_roster_shift_type_id", "shift_type_id"),
        Index("ix_roster_date_shift", "roster_date", "shift_type_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    shift_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shift_types.id", ondelete="RESTRICT"),
        nullable=True,
    )

    roster_date: Mapped[date] = mapped_column(Date, nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="roster_entries"
    )
    shift_type: Mapped[Optional["ShiftType"]] = relationship(
        "ShiftType", back_populates="roster_entries"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Roster id={self.id} emp={self.employee_id} date={self.roster_date}>"
