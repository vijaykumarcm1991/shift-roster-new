"""Authentication service — login, token creation, user lookup."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import MeResponse, TokenResponse


class AuthService:
    """Orchestrates authentication logic."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Verify credentials. Returns the User on success, None otherwise."""
        user = self.repository.get_by_username(username)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_token(self, user: User) -> TokenResponse:
        """Build a JWT for the given user."""
        token = create_access_token(
            subject=str(user.username),
            extra={"role": user.role},
        )
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    def update_last_login(self, user: User, db: Session) -> None:
        """Stamp the last_login timestamp."""
        user.last_login = datetime.now(timezone.utc)
        db.commit()

    @staticmethod
    def resolve_user_from_token(token: str, db: Session) -> Optional[User]:
        """Decode a JWT and return the corresponding User, or None."""
        payload = decode_access_token(token)
        if payload is None:
            return None
        username = payload.get("sub")
        if username is None:
            return None
        repo = UserRepository(db)
        user = repo.get_by_username(username)
        if user is None or not user.is_active:
            return None
        return user

    @staticmethod
    def user_to_me(user: User) -> MeResponse:
        """Convert a User model to a MeResponse schema."""
        return MeResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        )
