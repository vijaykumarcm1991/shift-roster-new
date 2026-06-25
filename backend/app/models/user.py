"""User ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    """An authenticated user of the application (admin or future roles)."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"
