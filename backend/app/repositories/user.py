"""Repository for the ``User`` model."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Data-access object for ``User`` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_username(self, username: str) -> Optional[User]:
        """Return the user with the given username, or None."""
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalars().first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Return the user with the given id, or None."""
        return self.db.get(User, user_id)
