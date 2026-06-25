"""``/api/shift-types`` endpoint."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.repositories.shift_type import ShiftTypeRepository
from app.schemas.shift_type import ShiftTypeRead
from app.services.shift_type import ShiftTypeService

router = APIRouter(tags=["shift-types"])


@router.get("/shift-types", response_model=List[ShiftTypeRead])
def list_shift_types(db: Session = Depends(db_session)) -> List[ShiftTypeRead]:
    """Return every defined shift type."""
    service = ShiftTypeService(ShiftTypeRepository(db))
    return service.list_shift_types()
