"""Pydantic schemas for roster read + write endpoints (Phase 5 + Phase 7 + Phase 8).

- Phase 5: read schemas (``RosterEntry``, ``RosterMonthResponse``).
- Phase 7: write schema (``RosterEntryUpdate``) used by
  ``PATCH /api/roster/entries/{entry_id}`` to update a single cell.
- Phase 8: bulk write schemas (``RosterBulkItem``,
  ``RosterBulkUpdate``, ``RosterBulkResultItem``,
  ``RosterBulkResult``) for the ``PATCH /api/roster/entries/bulk``
  endpoint that powers copy/paste and bulk updates.
"""

from datetime import date as _date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type alias because Pydantic 2.7.1 + Python 3.9 with
# ``from __future__ import annotations`` chokes on
# ``date: date = Field(...)`` — the field name clashes with the type
# annotation when evaluating.  Using ``Date`` as an alias keeps the
# wire format (``date``) intact while letting the class body parse.
Date = _date


class EmployeeBrief(BaseModel):
    """Minimal employee info embedded in a roster entry."""

    id: int
    employee_code: str
    employee_name: str
    designation: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None


class ShiftBrief(BaseModel):
    """Minimal shift info embedded in a roster entry. None if unassigned."""

    id: int
    code: str
    display_name: str
    color: str


class RosterEntry(BaseModel):
    """A single row in the monthly roster grid."""

    id: int
    employee: EmployeeBrief
    date: Date
    shift: Optional[ShiftBrief] = None
    remarks: Optional[str] = None


class RosterEntryUpdate(BaseModel):
    """Body for ``PATCH /api/roster/entries/{entry_id}``.

    Only the fields that are **explicitly set** in the request body are
    updated — omitted fields keep their current value.  To clear a shift,
    send ``{"shift_type_id": null}`` (explicit null).  Use the service
    layer's ``model_dump(exclude_unset=True)`` to distinguish between
    "field absent" and "field set to null".
    """

    shift_type_id: Optional[int] = Field(
        default=None,
        description=(
            "ID of the new shift type, or null to clear the shift. "
            "Omit the field entirely to leave the shift unchanged."
        ),
    )
    remarks: Optional[str] = Field(
        default=None,
        description=(
            "New remarks text, or null to clear. "
            "Omit the field entirely to leave remarks unchanged."
        ),
    )


# ---------------------------------------------------------------------------
# Phase 8 — bulk write
# ---------------------------------------------------------------------------

class RosterBulkItem(BaseModel):
    """One cell change in a bulk update.

    Identified by (employee_id, roster_date).  The new shift is given as
    a code (e.g. ``"S1"``, ``"GH"``) — the server resolves it to the
    shift_type_id.  An empty / null ``shift_code`` clears the shift.

    The frontend doesn't have easy access to internal employee ids and
    prefers working in (employee_code, date) — but the internal id is
    unambiguous and the wire format.  We use the internal id here.
    """

    employee_id: int = Field(..., description="Roster row's employee id.")
    date: Date = Field(..., description="Roster row's date.")
    shift_code: Optional[str] = Field(
        default=None,
        description=(
            "New shift code (e.g. 'S1', 'WO'), or null/empty to clear "
            "the shift.  An empty string '' is treated the same as null."
        ),
    )

    @field_validator("shift_code")
    @classmethod
    def _normalize_shift_code(cls, v):
        # Treat '' as null (clear the shift).  Case is preserved so
        # the service can do case-insensitive lookup.
        if v is None:
            return None
        v = v.strip()
        return v if v else None


class RosterBulkUpdate(BaseModel):
    """Body for ``PATCH /api/roster/entries/bulk``.

    A list of up to ~3,000 cell changes (100 employees × 31 days).  Each
    item is applied independently — invalid shifts or unknown
    (employee_id, date) pairs produce a per-item error and do NOT roll
    back successful items.  This matches the Phase 8 spec which says:
    "If part of the update fails, return meaningful validation errors
    and keep successful updates."
    """

    changes: List[RosterBulkItem] = Field(
        ...,
        description="List of cell changes to apply (max 3100 per call).",
    )

    @field_validator("changes")
    @classmethod
    def _limit_changes(cls, v):
        # Cap at one full month for 100 employees: 100 * 31 = 3100.
        # Anything beyond is almost certainly a bug or abuse.
        if len(v) > 3100:
            raise ValueError(
                f"too many changes in one request ({len(v)} > 3100)"
            )
        return v


class RosterBulkResultItem(BaseModel):
    """Per-item result of a bulk update.

    On success, ``entry`` echoes the updated row so the frontend can
    patch its in-memory state without re-fetching the whole month.
    On failure, ``error`` is a human-readable reason; ``entry`` is null
    and the existing row is left unchanged.
    """

    employee_id: int
    date: Date
    status: str = Field(..., description='"updated", "unchanged", or "error"')
    error: Optional[str] = None
    entry: Optional[RosterEntry] = None


class RosterBulkResult(BaseModel):
    """Top-level response of ``PATCH /api/roster/entries/bulk``.

    The HTTP status is 200 even when some items failed — the per-item
    ``status`` / ``error`` fields tell the frontend exactly what happened.
    Only a top-level validation error (bad payload, unauthenticated)
    produces a 4xx response.
    """

    results: List[RosterBulkResultItem]
    updated_count: int
    unchanged_count: int
    error_count: int


# Re-export at module level so callers that do
# ``from app.schemas.roster import Date`` get the alias.
Date = Date
class RosterMonthMeta(BaseModel):
    """Metadata about a month's roster."""

    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    month_name: str
    total_employees: int
    total_days: int
    total_records: int
    is_generated: bool


class RosterMonthResponse(BaseModel):
    """Full response for a single month."""

    model_config = ConfigDict(from_attributes=True)

    meta: RosterMonthMeta
    entries: List[RosterEntry]
