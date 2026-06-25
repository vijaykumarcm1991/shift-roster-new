"""Health-check response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for the ``/api/health`` endpoint."""

    status: str = "ok"
