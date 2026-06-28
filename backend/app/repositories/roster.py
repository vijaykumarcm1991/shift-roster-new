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

    def get_by_id(self, entry_id: int) -> Optional[Roster]:
        """Return a single roster entry by id, with eager-loaded relationships.

        Returns ``None`` if the id does not exist.  The eager loading means
        the caller can serialize the row (and its employee + shift_type)
        without a second round-trip.
        """
        stmt = (
            select(Roster)
            .options(
                joinedload(Roster.employee).joinedload(Employee.team),
                joinedload(Roster.shift_type),
            )
            .where(Roster.id == entry_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_employee_date(
        self, employee_id: int, roster_date: date
    ) -> Optional[Roster]:
        """Return the single roster row for (employee_id, date), or None.

        Eager-loads employee + shift_type so the caller can serialize
        the row in a single round-trip.
        """
        stmt = (
            select(Roster)
            .options(
                joinedload(Roster.employee).joinedload(Employee.team),
                joinedload(Roster.shift_type),
            )
            .where(
                and_(
                    Roster.employee_id == employee_id,
                    Roster.roster_date == roster_date,
                )
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def bulk_get_by_employee_date(
        self, pairs: List[Tuple[int, date]]
    ) -> dict[Tuple[int, date], Roster]:
        """Bulk fetch roster rows for a list of (employee_id, date) pairs.

        Returns a dict keyed by the same pairs so the service can look up
        each row in O(1).  Missing pairs are simply absent from the dict.
        Eager-loads employee + shift_type for serialization.

        The single-query approach is critical for Phase 8 performance: a
        100-employee × 31-day paste = 3,100 cells would otherwise mean
        3,100 round-trips.
        """
        if not pairs:
            return {}
        emp_ids = {eid for eid, _ in pairs}
        dates = {d for _, d in pairs}
        stmt = (
            select(Roster)
            .options(
                joinedload(Roster.employee).joinedload(Employee.team),
                joinedload(Roster.shift_type),
            )
            .where(
                and_(
                    Roster.employee_id.in_(emp_ids),
                    Roster.roster_date.in_(dates),
                )
            )
        )
        result: dict[Tuple[int, date], Roster] = {}
        for row in self.db.execute(stmt).unique().scalars().all():
            result[(row.employee_id, row.roster_date)] = row
        return result

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
