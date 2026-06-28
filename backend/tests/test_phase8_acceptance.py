"""Phase 8 acceptance tests — bulk roster updates (copy/paste backend).

Covers:
- Single-cell bulk update
- Multi-cell rectangular paste
- Invalid shift code → per-item error, other items still applied
- Blank shift_code → clears the shift
- Same shift as current → "unchanged" (not an error)
- Unknown (employee_id, date) pair → per-item error
- 401 unauthenticated
- 403 non-admin
- Cap at 3100 items per request
- Updated entry is echoed back with new shift details
- Repeated paste with same data is idempotent
"""

from datetime import date
from typing import List

import pytest
from sqlalchemy import select

from app.models import Roster as RosterModel
from app.models import ShiftType
from app.schemas.roster import RosterBulkItem, RosterBulkUpdate
from app.services.roster import RosterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_employees(db, count: int) -> list:
    """Create ``count`` active employees with predictable codes."""
    rows = []
    for i in range(1, count + 1):
        rows.append({
            "employee_code": f"E{i:03d}",
            "employee_name": f"Employee {i:03d}",
            "is_active": True,
        })
    from app.models import Employee
    for r in rows:
        db.add(Employee(**r))
    db.commit()
    return db.execute(select(Employee)).scalars().all()


def _generate(db, year: int, month: int) -> None:
    """Generate the roster for the given month."""
    from app.repositories.roster import RosterRepository
    RosterService(RosterRepository(db)).generate_month(year, month, db)


def _shift_id(db, code: str) -> int:
    return db.execute(
        select(ShiftType).where(ShiftType.code == code)
    ).scalar_one().id


def _auth_header(client) -> dict:
    """Return an Authorization header for the default admin."""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin_client(seeded_client, seeded_db):
    """Client with the default admin logged in, backed by a seeded DB.

    The conftest's SQLite engine is independent of the production
    postgres engine, so the lifespan seed is a no-op here.  We
    create the admin user in the test engine instead.
    """
    from app.core.security import hash_password
    from app.models import User
    existing = seeded_db.execute(
        select(User).where(User.username == "admin")
    ).scalar_one_or_none()
    if existing is None:
        seeded_db.add(
            User(
                username="admin",
                full_name="Administrator",
                email="admin@shiftroster.local",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
        )
        seeded_db.commit()

    return _auth_header(seeded_client)


# ---------------------------------------------------------------------------
# AC-1: Happy path — single + multi + rectangular
# ---------------------------------------------------------------------------
class TestBulkHappyPath:
    def test_single_cell_update(self, db, client, admin_client):
        _make_employees(db, 3)
        _generate(db, 2026, 7)

        employees = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().all()
        e1 = employees[0]
        s1 = _shift_id(db, "S1")

        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [
                {"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}
            ]},
            headers=admin_client,
        )
        if resp.status_code != 200:
            print("DEBUG response:", resp.status_code, resp.text)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated_count"] == 1
        assert body["unchanged_count"] == 0
        assert body["error_count"] == 0
        assert body["results"][0]["status"] == "updated"
        assert body["results"][0]["entry"]["shift"]["code"] == "S1"

    def test_multi_cell_rectangular_paste(self, db, client, admin_client):
        _make_employees(db, 5)
        _generate(db, 2026, 7)

        employees = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().all()
        e1, e2 = employees[0], employees[1]

        changes = [
            {"employee_id": e1.id, "date": "2026-07-10", "shift_code": "S1"},
            {"employee_id": e1.id, "date": "2026-07-11", "shift_code": "S2"},
            {"employee_id": e2.id, "date": "2026-07-10", "shift_code": "WO"},
            {"employee_id": e2.id, "date": "2026-07-11", "shift_code": "L"},
        ]
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": changes},
            headers=admin_client,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["updated_count"] == 4
        assert body["error_count"] == 0

        # Verify in DB
        s1 = _shift_id(db, "S1")
        s2 = _shift_id(db, "S2")
        s_wo = _shift_id(db, "WO")
        s_l = _shift_id(db, "L")
        rows = db.execute(
            select(RosterModel).where(
                RosterModel.employee_id.in_([e1.id, e2.id]),
                RosterModel.roster_date.in_([date(2026,7,10), date(2026,7,11)]),
            )
        ).scalars().all()
        by_key = {(r.employee_id, r.roster_date): r for r in rows}
        assert by_key[(e1.id, date(2026,7,10))].shift_type_id == s1
        assert by_key[(e1.id, date(2026,7,11))].shift_type_id == s2
        assert by_key[(e2.id, date(2026,7,10))].shift_type_id == s_wo
        assert by_key[(e2.id, date(2026,7,11))].shift_type_id == s_l

    def test_blank_shift_clears(self, db, client, admin_client):
        _make_employees(db, 1)
        _generate(db, 2026, 7)
        e1 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().first()
        s_s1 = _shift_id(db, "S1")

        # First set a shift
        client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}]},
            headers=admin_client,
        )
        # Then clear it
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": None}]},
            headers=admin_client,
        )
        body = resp.json()
        assert body["updated_count"] == 1
        assert body["results"][0]["entry"]["shift"] is None

        # DB check
        row = db.execute(
            select(RosterModel).where(
                RosterModel.employee_id == e1.id,
                RosterModel.roster_date == date(2026, 7, 15),
            )
        ).scalar_one()
        assert row.shift_type_id is None

    def test_empty_string_treated_as_null(self, db, client, admin_client):
        """Per the spec: 'Blank values should clear the shift'."""
        _make_employees(db, 1)
        _generate(db, 2026, 7)
        e1 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().first()

        # Set then clear with empty string
        r1 = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}]},
            headers=admin_client,
        )
        print("\nDEBUG first PATCH:", r1.status_code, r1.json())
        r2 = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": ""}]},
            headers=admin_client,
        )
        print("DEBUG second PATCH:", r2.status_code, r2.json())
        body = r2.json()
        assert body["updated_count"] == 1
        assert body["results"][0]["entry"]["shift"] is None

    def test_unchanged_when_same_shift(self, db, client, admin_client):
        """Pasting the same value should be 'unchanged', not 'updated'."""
        _make_employees(db, 1)
        _generate(db, 2026, 7)
        e1 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().first()

        # Set once
        client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}]},
            headers=admin_client,
        )
        # Paste the same value
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}]},
            headers=admin_client,
        )
        body = resp.json()
        assert body["updated_count"] == 0
        assert body["unchanged_count"] == 1
        assert body["results"][0]["status"] == "unchanged"

    def test_partial_failure_keeps_successful(self, db, client, admin_client):
        """Per the spec: 'keep successful updates' even if some fail."""
        _make_employees(db, 2)
        _generate(db, 2026, 7)
        e1, e2 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().all()

        changes = [
            {"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"},
            {"employee_id": e2.id, "date": "2026-07-15", "shift_code": "INVALID"},
            {"employee_id": e1.id, "date": "2026-07-16", "shift_code": "S2"},
        ]
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": changes},
            headers=admin_client,
        )
        body = resp.json()
        # HTTP is still 200
        assert resp.status_code == 200
        # 2 succeeded, 1 failed
        assert body["updated_count"] == 2
        assert body["error_count"] == 1
        assert body["unchanged_count"] == 0
        # The error item is item index 1
        assert body["results"][1]["status"] == "error"
        assert "INVALID" in body["results"][1]["error"]
        # Succeeded items have an entry
        assert body["results"][0]["entry"]["shift"]["code"] == "S1"
        assert body["results"][2]["entry"]["shift"]["code"] == "S2"

    def test_unknown_employee_id_errors(self, db, client, admin_client):
        _make_employees(db, 1)
        _generate(db, 2026, 7)

        changes = [
            {"employee_id": 99999, "date": "2026-07-15", "shift_code": "S1"}
        ]
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": changes},
            headers=admin_client,
        )
        body = resp.json()
        assert body["updated_count"] == 0
        assert body["error_count"] == 1
        assert "No roster row" in body["results"][0]["error"]

    def test_invalid_shift_does_not_overwrite(self, db, client, admin_client):
        """Per the spec: 'Invalid values should not overwrite existing data.'"""
        _make_employees(db, 1)
        _generate(db, 2026, 7)
        e1 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().first()
        s_s1 = _shift_id(db, "S1")

        # Set S1
        client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "S1"}]},
            headers=admin_client,
        )

        # Try to set INVALID — should error, S1 should still be in DB
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "INVALID"}]},
            headers=admin_client,
        )
        body = resp.json()
        assert body["updated_count"] == 0
        assert body["error_count"] == 1
        assert "INVALID" in body["results"][0]["error"]

        # DB should still have S1
        row = db.execute(
            select(RosterModel).where(
                RosterModel.employee_id == e1.id,
                RosterModel.roster_date == date(2026, 7, 15),
            )
        ).scalar_one()
        assert row.shift_type_id == s_s1

    def test_inactive_shift_treated_as_invalid(self, db, client, admin_client):
        """Inactive shifts should not be assignable."""
        from app.models import ShiftType as STModel
        # Add an inactive shift type
        db.add(STModel(code="ZZZ", display_name="Zzz", color="gray",
                      display_order=999, is_active=False))
        db.commit()

        _make_employees(db, 1)
        _generate(db, 2026, 7)
        e1 = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().first()

        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [{"employee_id": e1.id, "date": "2026-07-15", "shift_code": "ZZZ"}]},
            headers=admin_client,
        )
        body = resp.json()
        assert body["error_count"] == 1
        assert "ZZZ" in body["results"][0]["error"]


# ---------------------------------------------------------------------------
# AC-2: Auth
# ---------------------------------------------------------------------------
class TestBulkAuth:
    def test_unauthenticated_returns_401(self, client, db):
        _make_employees(db, 1)
        _generate(db, 2026, 7)
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": []},
        )
        assert resp.status_code == 401

    def test_non_admin_returns_403(self, client, db):
        # Create a non-admin user
        from app.core.security import hash_password
        from app.models import User
        existing = db.execute(
            select(User).where(User.username == "viewer")
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                User(
                    username="viewer",
                    full_name="Viewer",
                    email="viewer@shiftroster.local",
                    password_hash=hash_password("viewer123"),
                    role="viewer",
                    is_active=True,
                )
            )
            db.commit()

        resp = client.post(
            "/api/auth/login",
            json={"username": "viewer", "password": "viewer123"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# AC-3: Validation
# ---------------------------------------------------------------------------
class TestBulkValidation:
    def test_too_many_changes_returns_422(self, client, admin_client):
        """Cap at 3100 items per request."""
        items = [
            {"employee_id": 1, "date": "2026-07-15", "shift_code": "S1"}
        ] * 3101
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": items},
            headers=admin_client,
        )
        assert resp.status_code == 422

    def test_empty_changes_list_returns_200_with_zero_count(self, client, admin_client):
        """Empty (but valid) changes list — vacuous success."""
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": []},
            headers=admin_client,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["updated_count"] == 0
        assert body["unchanged_count"] == 0
        assert body["error_count"] == 0

    def test_invalid_date_format_returns_422(self, client, admin_client):
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [
                {"employee_id": 1, "date": "not-a-date", "shift_code": "S1"}
            ]},
            headers=admin_client,
        )
        assert resp.status_code == 422

    def test_missing_employee_id_returns_422(self, client, admin_client):
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": [
                {"date": "2026-07-15", "shift_code": "S1"}
            ]},
            headers=admin_client,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-4: Performance smoke test
# ---------------------------------------------------------------------------
class TestBulkPerformance:
    def test_one_month_100_employees(self, db, client, admin_client):
        """100 employees × 31 days = 3,100 cells in one call.

        Spec says the grid should remain responsive with at least
        100 employees × 31 days.  Backend should handle 3,100 cell
        changes in a single request.
        """
        _make_employees(db, 100)
        _generate(db, 2026, 7)
        employees = db.execute(select(__import__("app.models", fromlist=["Employee"]).Employee)).scalars().all()

        changes = [
            {"employee_id": e.id, "date": f"2026-07-{(d % 31) + 1:02d}", "shift_code": "S1"}
            for e in employees
            for d in range(31)
        ]
        assert len(changes) == 3100
        resp = client.patch(
            "/api/roster/entries/bulk",
            json={"changes": changes},
            headers=admin_client,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["updated_count"] == 3100
        assert body["error_count"] == 0
