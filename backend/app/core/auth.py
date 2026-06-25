"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.models.user import User
from app.services.auth import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(db_session),
) -> User:
    """Dependency: return the authenticated User or raise 401."""
    user = AuthService.resolve_user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: return the User only if their role is 'admin'."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
