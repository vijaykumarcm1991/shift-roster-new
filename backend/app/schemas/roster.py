"""Pydantic schemas for roster read endpoints (Phase 5)."""

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
