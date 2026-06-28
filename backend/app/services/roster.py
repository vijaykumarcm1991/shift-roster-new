"""Service for the Roster domain (Phase 5 + Phase 7).

Handles monthly roster generation, read queries, and (Phase 7) single-cell
updates. Generation is idempotent: re-running it for an already-generated
month is a no-op (returns the existing data). All date logic uses naive
``date`` objects — ``roster_date`` is a calendar date, not an instant in
time.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.roster import Roster
from app.models.shift_type import ShiftType
from app.repositories.roster import RosterRepository
from app.repositories.shift_type import ShiftTypeRepository
from app.schemas.roster import (
    EmployeeBrief,
    RosterEntry,
    RosterEntryUpdate,
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

    def __init__(
        self,
        repository: RosterRepository,
        shift_type_repository: Optional[ShiftTypeRepository] = None,
    ) -> None:
        self.repository = repository
        # The shift-type repo is needed for validation in ``update_entry``.
        # It is optional so that existing callers that only use the read
        # path can keep the old single-argument constructor.
        self.shift_type_repository = shift_type_repository

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

    # ---- mutation (Phase 7) ----

    def update_entry(
        self,
        entry_id: int,
        data: RosterEntryUpdate,
        db: Session,
    ) -> RosterEntry:
        """Update a single roster entry. Returns the updated entry.

        Behavior:
        - Fields **omitted** from the request body are left unchanged.
        - Fields set to ``None`` (explicit null) clear the field.
        - ``shift_type_id`` is validated against the shift_types table:
          if a non-null value is provided, the id must exist and be active.
        - Raises ``HTTPException(404)`` if the entry does not exist.
        - Raises ``HTTPException(400)`` if the shift id is invalid.
        """
        entry = self.repository.get_by_id(entry_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roster entry {entry_id} not found",
            )

        # ``exclude_unset`` distinguishes "field not in request" (keep
        # current value) from "field explicitly set to None" (clear it).
        updates = data.model_dump(exclude_unset=True)

        if "shift_type_id" in updates:
            new_id = updates["shift_type_id"]
            if new_id is not None:
                # Validate the shift type exists and is active.
                if self.shift_type_repository is None:
                    # Defensive — should not happen in production because
                    # the endpoint always passes one, but raise clearly
                    # if it does so we never silently accept bad input.
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="shift_type_repository is not configured",
                    )
                shift_type: Optional[ShiftType] = (
                    self.shift_type_repository.get_by_id(new_id)
                )
                if shift_type is None or not shift_type.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid shift_type_id: {new_id}",
                    )
            entry.shift_type_id = new_id

        if "remarks" in updates:
            entry.remarks = updates["remarks"]

        db.commit()
        db.refresh(entry)
        return self._to_entry(entry)

    # ---- mutation (Phase 8) ----

    def update_entries_bulk(
        self,
        changes,  # List[RosterBulkItem]
        db: Session,
    ) -> dict:
        """Apply many cell changes in one call.

        Each item is processed independently.  Returns a dict with
        per-item results plus summary counts:

        ``{"results": [RosterBulkResultItem, ...], "updated_count": N,
          "unchanged_count": M, "error_count": K}``

        The endpoint returns 200 with this dict even when some items
        failed — the per-item ``status`` / ``error`` fields tell the
        frontend exactly what happened.  Only a top-level validation
        error (bad payload, unauthenticated) produces a 4xx response.
        """
        from app.schemas.roster import RosterBulkResultItem  # local import

        if self.shift_type_repository is None:
            # Defensive — endpoints always pass a repo.  If someone
            # calls this directly without one, fail loudly rather than
            # silently accepting unknown shift codes.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="shift_type_repository is not configured",
            )

        # Use Pydantic attribute access on the model instances so
        # ``item.date`` is a ``datetime.date`` (not a string).  When
        # ``item`` is a dict (e.g. for direct unit tests), normalise.
        def _item_attr(it, key):
            if isinstance(it, dict):
                v = it[key]
                if key == "date" and isinstance(v, str):
                    return date.fromisoformat(v)
                return v
            return getattr(it, key)

        def _item_date(it):
            if isinstance(it, dict):
                v = it["date"]
                return v if isinstance(v, date) else date.fromisoformat(v)
            return it.date

        # ---- 1. Bulk-resolve shift codes up front ----
        unique_codes: set = set()
        for c in changes:
            code = _item_attr(c, "shift_code")
            if code:
                unique_codes.add(code)
        code_map = self.shift_type_repository.bulk_get_by_codes(
            list(unique_codes)
        )

        # ---- 2. Bulk-fetch all affected rows in one query ----
        pairs = [(_item_attr(c, "employee_id"), _item_date(c)) for c in changes]
        rows_by_key = self.repository.bulk_get_by_employee_date(pairs)

        # ---- 3. Process each change ----
        results: list = []
        updated_count = 0
        unchanged_count = 0
        error_count = 0

        # Collect rows that actually changed so we can commit once at
        # the end.  If any single change fails, we still commit the
        # others (per the spec: "keep successful updates").
        modified_rows: list = []

        for item in changes:
            emp_id = _item_attr(item, "employee_id")
            d = _item_date(item)
            key = (emp_id, d)
            row = rows_by_key.get(key)
            if row is None:
                results.append(RosterBulkResultItem(
                    employee_id=emp_id,
                    date=d,
                    status="error",
                    error=(
                        f"No roster row found for employee {emp_id} on "
                        f"{d.isoformat()}. Generate the month first "
                        f"before editing."
                    ),
                ))
                error_count += 1
                continue

            shift_code = _item_attr(item, "shift_code")
            if shift_code is None:
                # Explicit null = clear the shift.
                if row.shift_type_id is None:
                    results.append(RosterBulkResultItem(
                        employee_id=emp_id,
                        date=d,
                        status="unchanged",
                        entry=self._to_entry(row),
                    ))
                    unchanged_count += 1
                    continue
                row.shift_type_id = None
                modified_rows.append(row)
                results.append(RosterBulkResultItem(
                    employee_id=emp_id,
                    date=d,
                    status="updated",
                    entry=None,  # filled in after commit+refresh below
                ))
                updated_count += 1
                continue

            # Non-null: resolve code → shift_type_id.
            shift = code_map.get(shift_code.upper())
            if shift is None:
                # Spec: "Invalid values should not overwrite existing
                # data." — we don't mutate the row, just return an error.
                results.append(RosterBulkResultItem(
                    employee_id=emp_id,
                    date=d,
                    status="error",
                    error=(
                        f"Unknown or inactive shift code: {shift_code!r}"
                    ),
                ))
                error_count += 1
                continue

            if row.shift_type_id == shift.id:
                results.append(RosterBulkResultItem(
                    employee_id=emp_id,
                    date=d,
                    status="unchanged",
                    entry=self._to_entry(row),
                ))
                unchanged_count += 1
                continue

            row.shift_type_id = shift.id
            modified_rows.append(row)
            results.append(RosterBulkResultItem(
                employee_id=emp_id,
                date=d,
                status="updated",
                entry=None,  # filled in after commit+refresh below
            ))
            updated_count += 1

        # ---- 4. Commit successful changes once ----
        if modified_rows:
            db.commit()
            for row in modified_rows:
                db.refresh(row)

        # ---- 5. Fill in `entry` for the updated items ----
        # Map (emp_id, date) → updated Roster so we can look up the
        # post-commit state for each result with status='updated'.
        if modified_rows:
            refreshed_keys = [(r.employee_id, r.roster_date) for r in modified_rows]
            refreshed_by_key = self.repository.bulk_get_by_employee_date(
                refreshed_keys
            )
            for r in results:
                if r.status == "updated":
                    r.entry = self._to_entry(
                        refreshed_by_key.get((r.employee_id, r.date))
                    )

        return {
            "results": results,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "error_count": error_count,
        }

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
