"""Phase 5 acceptance tests — monthly roster generation."""

from datetime import date
from typing import List

import pytest
from sqlalchemy import select

from app.models import Team, User
from app.models.employee import Employee as EmployeeModel
from app.models.roster import Roster as RosterModel
from app.repositories.roster import RosterRepository
from app.services.roster import RosterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_employees(db, count: int, *, team_id=None, is_active=True, prefix: str = "E") -> List[EmployeeModel]:
    """Create ``count`` employees with predictable codes/names."""
    # Find the next available index for this prefix to avoid unique
    # constraint failures when called more than once in a single test.
    existing = db.execute(
        select(EmployeeModel.employee_code)
    ).scalars().all()
    used = {code for code in existing if code.startswith(prefix)}
    start = 1
    while f"{prefix}{start:03d}" in used:
        start += 1
    rows = []
    for offset in range(count):
        idx = start + offset
        rows.append(
            EmployeeModel(
                employee_code=f"{prefix}{idx:03d}",
                employee_name=f"Employee {prefix}{idx:03d}",
                team_id=team_id,
                is_active=is_active,
            )
        )
    db.add_all(rows)
    db.commit()
    return rows


def _auth_header(client) -> dict:
    """Return an Authorization header for the default admin."""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_client(client, db):
    """Client with the default admin logged in.

    The test conftest's SQLite engine is independent of the app's
    production postgres engine, so the lifespan seed is a no-op here.
    We create the admin user directly in the test session instead.
    """
    from app.core.security import hash_password

    existing = db.execute(
        select(User).where(User.username == "admin")
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            User(
                username="admin",
                full_name="Administrator",
                email="admin@shiftroster.local",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
        )
        db.commit()

    headers = _auth_header(client)
    return client, headers


# ---------------------------------------------------------------------------
# AC-1: Roster generation creates the correct number of rows
# ---------------------------------------------------------------------------
class TestRosterGeneration:
    def _generate(self, db, year, month):
        repo = RosterRepository(db)
        service = RosterService(repo)
        return service.generate_month(year, month, db)

    def test_generates_465_rows_for_15_employees_31_days(self, db):
        _make_employees(db, 15)
        resp = self._generate(db, 2026, 7)
        assert resp.meta.total_employees == 15
        assert resp.meta.total_days == 31
        assert resp.meta.total_records == 15 * 31
        assert resp.meta.is_generated is True
        assert len(resp.entries) == 15 * 31

    def test_leap_year_february(self, db):
        _make_employees(db, 1)
        # 2024 is a leap year → 29 days
        resp = self._generate(db, 2024, 2)
        assert resp.meta.total_days == 29
        assert resp.meta.total_records == 29
        # 2023 is not → 28 days
        resp = self._generate(db, 2023, 2)
        assert resp.meta.total_days == 28
        assert resp.meta.total_records == 28

    def test_30_day_month(self, db):
        _make_employees(db, 2)
        resp = self._generate(db, 2026, 4)  # April = 30 days
        assert resp.meta.total_days == 30
        assert resp.meta.total_records == 60

    def test_31_day_month(self, db):
        _make_employees(db, 1)
        resp = self._generate(db, 2026, 1)  # January = 31 days
        assert resp.meta.total_days == 31
        assert resp.meta.total_records == 31

    def test_inactive_employees_skipped(self, db):
        _make_employees(db, 3, is_active=True, prefix="A")
        _make_employees(db, 2, is_active=False, prefix="B")
        resp = self._generate(db, 2026, 7)
        assert resp.meta.total_employees == 3  # only active counted
        assert resp.meta.total_records == 3 * 31

    def test_no_active_employees_generates_nothing(self, db):
        _make_employees(db, 5, is_active=False, prefix="X")
        resp = self._generate(db, 2026, 7)
        assert resp.meta.total_employees == 0
        assert resp.meta.total_records == 0
        assert resp.meta.is_generated is False

    def test_shift_type_id_is_null_for_new_rows(self, db):
        _make_employees(db, 1)
        self._generate(db, 2026, 7)
        rows = db.execute(select(RosterModel)).scalars().all()
        assert len(rows) == 31
        for r in rows:
            assert r.shift_type_id is None
            assert r.remarks is None


# ---------------------------------------------------------------------------
# AC-2: Idempotency
# ---------------------------------------------------------------------------
class TestIdempotency:
    def _generate(self, db, year, month):
        return RosterService(RosterRepository(db)).generate_month(year, month, db)

    def test_generating_twice_does_not_duplicate(self, db):
        _make_employees(db, 5)
        r1 = self._generate(db, 2026, 7)
        r2 = self._generate(db, 2026, 7)
        assert r1.meta.total_records == r2.meta.total_records == 5 * 31
        # DB-level count confirms no duplicates
        assert db.execute(select(RosterModel.id)).scalars().all().__len__() == 5 * 31

    def test_three_consecutive_generations_remain_stable(self, db):
        _make_employees(db, 3)
        for _ in range(3):
            self._generate(db, 2026, 7)
        count = len(db.execute(select(RosterModel.id)).scalars().all())
        assert count == 3 * 31

    def test_adding_employee_after_generation_does_not_backfill(self, db):
        _make_employees(db, 3, prefix="A")
        self._generate(db, 2026, 7)
        _make_employees(db, 2, prefix="B")  # add more active employees
        self._generate(db, 2026, 7)  # second generation is a no-op
        # Original generation only has 3 employees × 31 days
        count = len(db.execute(select(RosterModel.id)).scalars().all())
        assert count == 3 * 31


# ---------------------------------------------------------------------------
# AC-3: Response shape
# ---------------------------------------------------------------------------
class TestResponseShape:
    def test_entry_includes_employee_details(self, db):
        team = Team(team_name="Ops", display_order=1)
        db.add(team)
        db.commit()
        _make_employees(db, 1, team_id=team.id)
        service = RosterService(RosterRepository(db))
        resp = service.generate_month(2026, 7, db)
        entry = resp.entries[0]
        assert entry.employee.employee_code == "E001"
        assert entry.employee.employee_name == "Employee E001"
        assert entry.employee.team_name == "Ops"
        assert entry.shift is None  # empty initially
        assert entry.remarks is None
        assert entry.date == date(2026, 7, 1)

    def test_meta_includes_month_name(self, db):
        _make_employees(db, 1)
        service = RosterService(RosterRepository(db))
        resp = service.get_month(2026, 7, db)
        assert resp.meta.month_name == "July"
        assert resp.meta.is_generated is False
        assert resp.meta.total_records == 0
        assert resp.entries == []


# ---------------------------------------------------------------------------
# AC-4: HTTP API
# ---------------------------------------------------------------------------
class TestRosterAPI:
    def test_get_unauthenticated_returns_401(self, client):
        resp = client.get("/api/roster/2026/7")
        assert resp.status_code == 401

    def test_get_nonexistent_month_returns_empty(self, admin_client, db):
        client, headers = admin_client
        _make_employees(db, 3)
        resp = client.get("/api/roster/2026/7", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["is_generated"] is False
        assert data["meta"]["total_records"] == 0
        assert data["entries"] == []

    def test_generate_creates_roster(self, admin_client, db):
        client, headers = admin_client
        _make_employees(db, 2)
        resp = client.post("/api/roster/2026/7/generate", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["is_generated"] is True
        assert data["meta"]["total_records"] == 2 * 31
        assert len(data["entries"]) == 2 * 31

    def test_generate_is_idempotent(self, admin_client, db):
        client, headers = admin_client
        _make_employees(db, 2)
        client.post("/api/roster/2026/7/generate", headers=headers)
        resp2 = client.post("/api/roster/2026/7/generate", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["meta"]["total_records"] == 2 * 31

    def test_get_after_generate_returns_data(self, admin_client, db):
        client, headers = admin_client
        _make_employees(db, 1)
        client.post("/api/roster/2026/7/generate", headers=headers)
        resp = client.get("/api/roster/2026/7", headers=headers)
        data = resp.json()
        assert data["meta"]["is_generated"] is True
        assert data["meta"]["total_records"] == 31
        assert len(data["entries"]) == 31

    def test_get_with_limit_pagination(self, admin_client, db):
        client, headers = admin_client
        _make_employees(db, 2)
        client.post("/api/roster/2026/7/generate", headers=headers)
        resp = client.get(
            "/api/roster/2026/7?limit=10&offset=0", headers=headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) == 10

    def test_invalid_month_returns_422(self, admin_client):
        client, headers = admin_client
        resp = client.get("/api/roster/2026/13", headers=headers)
        assert resp.status_code == 422
        resp = client.get("/api/roster/2026/0", headers=headers)
        assert resp.status_code == 422

    def test_invalid_year_returns_422(self, admin_client):
        client, headers = admin_client
        resp = client.get("/api/roster/1999/7", headers=headers)
        assert resp.status_code == 422
        resp = client.get("/api/roster/2200/7", headers=headers)
        assert resp.status_code == 422
