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
