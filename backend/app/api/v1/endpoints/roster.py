"""``/api/roster`` endpoints (Phase 5 + Phase 7 + Phase 8).

- ``GET  /api/roster/{year}/{month}``           — admin read of a month
- ``POST /api/roster/{year}/{month}/generate``  — admin: idempotent generation
- ``GET  /api/roster/{year}/{month}/public``    — public read of a month
- ``PATCH /api/roster/entries/{entry_id}``      — admin: update a single cell
- ``PATCH /api/roster/entries/bulk``            — admin: update many cells in
                                                one call (Phase 8)

The admin endpoints require a valid admin JWT. The public endpoint is
used by the read-only roster viewer and is open to unauthenticated users.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.auth import require_admin
from app.models.user import User
from app.repositories.roster import RosterRepository
from app.repositories.shift_type import ShiftTypeRepository
from app.schemas.roster import (
    RosterBulkResult,
    RosterBulkUpdate,
    RosterEntry,
    RosterEntryUpdate,
    RosterMonthResponse,
)
from app.services.roster import RosterService

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("/{year}/{month}", response_model=RosterMonthResponse)
def get_roster_month(
    year: int,
    month: int,
    offset: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=None, ge=1, le=2000),
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> RosterMonthResponse:
    """Return the roster for a month (empty entries if not yet generated)."""
    _validate_year_month(year, month)
    service = RosterService(RosterRepository(db))
    return service.get_month(year, month, db, offset=offset, limit=limit)


@router.get("/{year}/{month}/public", response_model=RosterMonthResponse)
def get_roster_month_public(
    year: int,
    month: int,
    db: Session = Depends(db_session),
) -> RosterMonthResponse:
    """Return the roster for a month without authentication.

    Identical response to the admin endpoint but without ``require_admin``.
    Used by the public read-only roster viewer.
    """
    _validate_year_month(year, month)
    service = RosterService(RosterRepository(db))
    return service.get_month(year, month, db)


@router.post(
    "/{year}/{month}/generate",
    response_model=RosterMonthResponse,
    status_code=status.HTTP_200_OK,
)
def generate_roster_month(
    year: int,
    month: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> RosterMonthResponse:
    """Generate the roster for a month. Idempotent."""
    _validate_year_month(year, month)
    service = RosterService(RosterRepository(db))
    return service.generate_month(year, month, db)


@router.patch(
    "/entries/bulk",
    response_model=RosterBulkResult,
)
def update_roster_entries_bulk(
    payload: RosterBulkUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> RosterBulkResult:
    """Apply many cell changes in one call (Phase 8 — copy/paste, bulk).

    Each item is applied independently.  Unknown (employee_id, date)
    pairs and unknown / inactive shift codes produce a per-item error;
    the rest of the batch still goes through (the spec explicitly says
    "keep successful updates" if part of the update fails).  Returns a
    200 with the per-item results so the frontend can patch its
    in-memory state and show a summary toast — successful cells get
    the updated ``RosterEntry`` echoed back, failures get an error.

    Capped at 3,100 items per call (100 employees × 31 days).

    IMPORTANT: this route MUST be registered BEFORE
    ``/entries/{entry_id}`` — FastAPI matches routes in registration
    order, and ``bulk`` would otherwise be parsed as an integer
    ``entry_id`` and fail with a 422.
    """
    service = RosterService(
        RosterRepository(db),
        ShiftTypeRepository(db),
    )
    result = service.update_entries_bulk(payload.changes, db)
    return RosterBulkResult(**result)


@router.patch(
    "/entries/{entry_id}",
    response_model=RosterEntry,
)
def update_roster_entry(
    entry_id: int,
    payload: RosterEntryUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> RosterEntry:
    """Update a single roster cell (shift and/or remarks).

    Only the fields explicitly present in the request body are updated;
    omitted fields keep their current value.  To clear a shift, send
    ``{"shift_type_id": null}``.  Returns the updated entry.
    """
    service = RosterService(
        RosterRepository(db),
        ShiftTypeRepository(db),
    )
    return service.update_entry(entry_id, payload, db)


def _validate_year_month(year: int, month: int) -> None:
    """Validate a (year, month) pair. Raises 422 on out-of-range."""
    if not (1 <= month <= 12):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be between 1 and 12",
        )
    if not (2000 <= year <= 2100):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year must be between 2000 and 2100",
        )
