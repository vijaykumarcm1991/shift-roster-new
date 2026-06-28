"""Repository for the ``ShiftType`` model."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.shift_type import ShiftType


class ShiftTypeRepository:
    """Data-access object for ``ShiftType`` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> List[ShiftType]:
        """Return every shift type, ordered by display_order then code."""
        stmt = select(ShiftType).order_by(ShiftType.display_order, ShiftType.code)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, shift_type_id: int) -> Optional[ShiftType]:
        """Return a single shift type by id, or ``None`` if not found."""
        stmt = select(ShiftType).where(ShiftType.id == shift_type_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_by_code(self, code: str) -> Optional[ShiftType]:
        """Return an active shift type by its code (case-insensitive).

        Returns ``None`` if no active shift with that code exists.
        Phase 8 uses this to resolve ``shift_code`` strings from bulk
        paste payloads to internal shift_type_ids.
        """
        stmt = (
            select(ShiftType)
            .where(ShiftType.code.ilike(code))
            .where(ShiftType.is_active.is_(True))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def bulk_get_by_codes(self, codes: List[str]) -> dict[str, ShiftType]:
        """Bulk-resolve shift codes (case-insensitive) to their active rows.

        Returns a dict keyed by the **upper-cased** input code so the
        service can look up any of the resolved codes in O(1).  Codes
        that don't match any active row are simply absent.
        """
        if not codes:
            return {}
        upper_codes = list({c.upper() for c in codes if c})
        if not upper_codes:
            return {}
        stmt = (
            select(ShiftType)
            .where(ShiftType.code.in_(upper_codes))
            .where(ShiftType.is_active.is_(True))
        )
        return {row.code: row for row in self.db.execute(stmt).scalars().all()}
