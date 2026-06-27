"""Repository for the ``Roster`` model (Phase 5)."""

from __future__ import annotations

import calendar
from datetime import date
from typing import List, Optional, Set, Tuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.models.roster import Roster


class RosterRepository:
    """Data-access object for ``Roster`` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- queries ----

    def month_bounds(self, year: int, month: int) -> Tuple[date, date]:
        """Return [start, end_exclusive) for a given month."""
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        return start, end

    def days_in_month(self, year: int, month: int) -> int:
        """Return the number of days in the given month (handles leap years)."""
        return calendar.monthrange(year, month)[1]

    def existing_pairs_in_month(
        self, year: int, month: int
    ) -> Set[Tuple[int, date]]:
        """Return (employee_id, roster_date) pairs that already exist for the month."""
        start, end = self.month_bounds(year, month)
        stmt = select(Roster.employee_id, Roster.roster_date).where(
            and_(Roster.roster_date >= start, Roster.roster_date < end)
        )
        return {(eid, d) for eid, d in self.db.execute(stmt).all()}

    def list_active_employees(self) -> List[Employee]:
        """Return every active employee, ordered by name then id."""
        stmt = (
            select(Employee)
            .where(Employee.is_active.is_(True))
            .order_by(Employee.employee_name.asc(), Employee.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_for_month(self, year: int, month: int) -> int:
        """Return the number of roster rows for the given month."""
        start, end = self.month_bounds(year, month)
        stmt = select(Roster.id).where(
            and_(Roster.roster_date >= start, Roster.roster_date < end)
        )
        return len(self.db.execute(stmt).scalars().all())

    def list_for_month(
        self, year: int, month: int
    ) -> List[Roster]:
        """Return all roster rows for the month, joined with employee + shift_type.

        Ordered by (date, employee_name) for a stable grid view.
        """
        start, end = self.month_bounds(year, month)
        stmt = (
            select(Roster)
            .options(
                joinedload(Roster.employee).joinedload(Employee.team),
                joinedload(Roster.shift_type),
            )
            .where(and_(Roster.roster_date >= start, Roster.roster_date < end))
            .order_by(Roster.roster_date.asc(), Roster.employee_id.asc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_month_paginated(
        self,
        year: int,
        month: int,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> List[Roster]:
        """Return a page of roster rows for the month."""
        start, end = self.month_bounds(year, month)
        stmt = (
            select(Roster)
            .options(
                joinedload(Roster.employee).joinedload(Employee.team),
                joinedload(Roster.shift_type),
            )
            .where(and_(Roster.roster_date >= start, Roster.roster_date < end))
            .order_by(Roster.roster_date.asc(), Roster.employee_id.asc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())

    # ---- mutations ----

    def bulk_insert(self, entries: List[Roster]) -> int:
        """Insert a batch of new roster rows. Returns count actually inserted.

        The caller is expected to have already filtered out duplicates; the
        unique constraint on (employee_id, roster_date) is a final safety net.
        """
        if not entries:
            return 0
        self.db.add_all(entries)
        self.db.flush()
        return len(entries)
