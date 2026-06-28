"""Pydantic schemas for roster read + write endpoints (Phase 5 + Phase 7).

- Phase 5: read schemas (``RosterEntry``, ``RosterMonthResponse``).
- Phase 7: write schema (``RosterEntryUpdate``) used by
  ``PATCH /api/roster/entries/{entry_id}`` to update a single cell.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    date: date
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
