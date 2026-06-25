"""Authentication endpoints — login, logout, current-user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, MeResponse, MessageResponse, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(db_session)) -> TokenResponse:
    """Authenticate with username & password. Returns a JWT."""
    service = AuthService(UserRepository(db))
    user = service.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    service.update_last_login(user, db)
    return service.create_token(user)


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    """Log out (the frontend discards the token)."""
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=MeResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> MeResponse:
    """Return the currently authenticated user's info."""
    return AuthService.user_to_me(current_user)
