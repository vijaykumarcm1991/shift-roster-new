"""Shared test fixtures.

Every test module gets an in-memory SQLite database that is created
fresh for each test function.  The FastAPI ``TestClient`` uses the
same session via an override of the ``db_session`` dependency.
"""

from typing import Generator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import db_session
from app.db.base import Base
from app.db.seed import seed_shift_types
from app.main import app


# ---------------------------------------------------------------------------
# SQLite engine that enforces FK constraints (disabled by default)
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=None,  # default — in-memory per connection
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[override]
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    class_=Session,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Yield a clean database session with all tables created."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI test client wired to the per-test database."""

    def _override_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass  # session lifecycle managed by the ``db`` fixture

    app.dependency_overrides[db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seeded_db(db: Session) -> Session:
    """Return a session after shift-type seed data has been inserted."""
    seed_shift_types(db)
    return db


@pytest.fixture(scope="function")
def seeded_client(seeded_db: Session) -> Generator[TestClient, None, None]:
    """Test client backed by a database that already has seed data."""

    def _override_db() -> Generator[Session, None, None]:
        try:
            yield seeded_db
        finally:
            pass

    app.dependency_overrides[db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
