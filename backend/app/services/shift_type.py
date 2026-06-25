"""Service for the ``ShiftType`` domain."""

from __future__ import annotations

from typing import List

from app.models.shift_type import ShiftType
from app.repositories.shift_type import ShiftTypeRepository
from app.schemas.shift_type import ShiftTypeRead


class ShiftTypeService:
    """High-level operations on shift types."""

    def __init__(self, repository: ShiftTypeRepository) -> None:
        self.repository = repository

    def list_shift_types(self) -> List[ShiftTypeRead]:
        """Return all shift types as read-schema instances."""
        shift_types: List[ShiftType] = self.repository.list_all()
        return [ShiftTypeRead.model_validate(s) for s in shift_types]
