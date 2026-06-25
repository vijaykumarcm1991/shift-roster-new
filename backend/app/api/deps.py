"""Shared API dependencies."""

from typing import Generator

from sqlalchemy.orm import Session

from app.db.session import get_db


def db_session() -> Generator[Session, None, None]:
    """Yield a database session for route dependencies."""
    yield from get_db()
