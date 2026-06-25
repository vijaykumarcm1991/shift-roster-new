"""Pydantic schema for the ``ShiftType`` model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShiftTypeBase(BaseModel):
    """Shared fields for a shift type."""

    code: str = Field(..., min_length=1, max_length=16)
    display_name: str = Field(..., min_length=1, max_length=80)
    color: str = Field(..., min_length=1, max_length=16)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class ShiftTypeRead(ShiftTypeBase):
    """Read schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
