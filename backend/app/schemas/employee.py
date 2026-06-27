"""Pydantic schemas for Employee CRUD endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmployeeCreate(BaseModel):
    """Payload for ``POST /api/employees``."""

    employee_code: str = Field(..., min_length=1, max_length=64)
    employee_name: str = Field(..., min_length=1, max_length=150)
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    designation: Optional[str] = Field(default=None, max_length=120)
    team_id: Optional[int] = Field(default=None)
    is_active: bool = True

    @field_validator("employee_code", "employee_name")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        """Trim whitespace and reject empty strings."""
        v = (value or "").strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("designation")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        return v or None


class EmployeeUpdate(BaseModel):
    """Payload for ``PUT /api/employees/{id}``."""

    employee_code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    employee_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    designation: Optional[str] = Field(default=None, max_length=120)
    team_id: Optional[int] = Field(default=None)
    is_active: Optional[bool] = None

    @field_validator("employee_code", "employee_name")
    @classmethod
    def _strip_required(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("designation")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        return v or None


class EmployeeRead(BaseModel):
    """Schema returned by read endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    employee_name: str
    email: Optional[str] = None
    designation: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseModel):
    """Paginated list wrapper for Employee endpoints."""

    items: List[EmployeeRead]
    total: int
    page: int
    page_size: int
    total_pages: int
