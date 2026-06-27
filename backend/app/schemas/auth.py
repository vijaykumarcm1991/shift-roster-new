"""Pydantic schemas for authentication endpoints."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Login ---
class LoginRequest(BaseModel):
    """Payload for ``POST /api/auth/login``."""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """JWT token returned after successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiry


# --- Current user ---
class MeResponse(BaseModel):
    """Schema for ``GET /api/auth/me``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: Optional[str] = None
    role: str


# --- Generic message ---
class MessageResponse(BaseModel):
    """Simple message payload."""

    message: str
