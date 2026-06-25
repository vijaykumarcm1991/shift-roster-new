"""SQLAlchemy ORM models.

Phase 1 contains no business models. This file imports the shared
declarative base so that Alembic autogenerate can locate metadata.
"""

from app.db.base import Base  # noqa: F401
