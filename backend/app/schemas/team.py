"""Pydantic schema for the ``Team`` model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamBase(BaseModel):
    """Shared fields for a team."""

    team_name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class TeamRead(TeamBase):
    """Read schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
