"""Service for the Roster domain (Phase 5).

Handles monthly roster generation and read queries. Generation is
idempotent: re-running it for an already-generated month is a no-op
(returns the existing data). All date logic uses naive ``date`` objects
— ``roster_date`` is a calendar date, not an instant in time.
"""

from __future__ import annotations

from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.repositories.roster import RosterRepository
from app.schemas.roster import (
    EmployeeBrief,
    RosterEntry,
    RosterMonthMeta,
    RosterMonthResponse,
    ShiftBrief,
)


MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class RosterService:
    """High-level operations on the monthly roster."""

    def __init__(self, repository: RosterRepository) -> None:
        self.repository = repository

    # ---- read ----

    def get_month(
        self,
        year: int,
        month: int,
        db: Session,
        offset: int = 0,
        limit: int | None = None,
    ) -> RosterMonthResponse:
        """Return the roster for a month, with pagination on entries.

        If the month has no roster yet, returns an empty entries list with
        ``is_generated=False``.
        """
        active_employees = self.repository.list_active_employees()
        total_employees = len(active_employees)
        total_days = self.repository.days_in_month(year, month)
        total_records = self.repository.count_for_month(year, month)
        is_generated = total_records > 0

        rows = self.repository.list_for_month_paginated(
            year, month, offset=offset, limit=limit
        ) if is_generated else []

        return RosterMonthResponse(
            meta=RosterMonthMeta(
                year=year,
                month=month,
                month_name=MONTH_NAMES[month - 1],
                total_employees=total_employees,
                total_days=total_days,
                total_records=total_records,
                is_generated=is_generated,
            ),
            entries=[self._to_entry(r) for r in rows],
        )

    # ---- generation ----

    def generate_month(self, year: int, month: int, db: Session) -> RosterMonthResponse:
        """Generate the roster for a month if not already generated.

        Idempotent: returns the existing data (full month, no pagination)
        if the month has already been generated.
        """
        existing_pairs = self.repository.existing_pairs_in_month(year, month)
        if existing_pairs:
            # Already generated — return the full data set.
            return self.get_month(year, month, db)

        active_employees = self.repository.list_active_employees()
        total_days = self.repository.days_in_month(year, month)

        new_entries: List[Roster] = []
        for emp in active_employees:
            for day in range(1, total_days + 1):
                d = date(year, month, day)
                if (emp.id, d) in existing_pairs:
                    continue
                new_entries.append(
                    Roster(
                        employee_id=emp.id,
                        shift_type_id=None,
                        roster_date=d,
                        remarks=None,
                    )
                )

        if new_entries:
            self.repository.bulk_insert(new_entries)
            db.commit()

        return self.get_month(year, month, db)

    # ---- helpers ----

    @staticmethod
    def _to_entry(row: Roster) -> RosterEntry:
        emp = row.employee
        team_name = emp.team.team_name if emp.team else None
        shift: ShiftBrief | None = None
        if row.shift_type is not None:
            shift = ShiftBrief(
                id=row.shift_type.id,
                code=row.shift_type.code,
                display_name=row.shift_type.display_name,
                color=row.shift_type.color,
            )
        return RosterEntry(
            id=row.id,
            employee=EmployeeBrief(
                id=emp.id,
                employee_code=emp.employee_code,
                employee_name=emp.employee_name,
                designation=emp.designation,
                team_id=emp.team_id,
                team_name=team_name,
            ),
            date=row.roster_date,
            shift=shift,
            remarks=row.remarks,
        )
