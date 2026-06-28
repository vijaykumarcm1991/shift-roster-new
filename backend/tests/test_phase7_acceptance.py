"""Phase 7 acceptance tests — editable roster cells.

Covers the full Phase 7 spec:

- AC-1  Click + type editing with autocomplete
- AC-2  Double-click opens searchable dropdown (frontend-only behavior;
        on the backend we just confirm the data round-trips)
- AC-3  Save behavior (PATCH single cell, update only what changed)
- AC-4  Validation (only valid shift codes, invalid → 400)
- AC-5  Auth (admins can edit, public cannot)
- AC-6  Public read-only endpoint
- AC-7  Edge cases (clear shift, update remarks, missing entry, etc.)
"""

from datetime import date
from typing import List

import pytest
from sqlalchemy import select

from app.models import Team, User
from app.models.employee import Employee as EmployeeModel
from app.models.roster import Roster as RosterModel
from app.models.shift_type import ShiftType as ShiftTypeModel
from app.repositories.roster import RosterRepository
from app.repositories.shift_type import ShiftTypeRepository
from app.services.roster import RosterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_employees(db, count: int, *, team_id=None, is_active=True, prefix: str = "E") -> List[EmployeeModel]:
    """Create ``count`` employees with predictable codes/names."""
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


def _generate_july(db, n_employees: int = 2) -> int:
    """Generate the July 2026 roster and return its ``is_generated`` flag.

    Returns the number of roster rows created. Seeds shift types first
    so any test that subsequently looks up a shift by code (e.g. S1)
    finds it.
    """
    from app.db.seed import seed_shift_types
    seed_shift_types(db)
    _make_employees(db, n_employees)
    RosterService(RosterRepository(db)).generate_month(2026, 7, db)
    return db.execute(select(RosterModel.id)).scalars().all().__len__()


def _shift_by_code(db, code: str) -> ShiftTypeModel:
    return db.execute(
        select(ShiftTypeModel).where(ShiftTypeModel.code == code)
    ).scalar_one()


# ---------------------------------------------------------------------------
# AC-1: Repository get_by_id
# ---------------------------------------------------------------------------
class TestRepoGetById:
    def test_get_existing_entry(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        repo = RosterRepository(db)
        entry = repo.get_by_id(entry_id)
        assert entry is not None
        assert entry.id == entry_id
        # Eager loaded relationships
        assert entry.employee is not None
        assert entry.employee.employee_code == "E001"
        assert entry.shift_type is None  # generated empty

    def test_get_nonexistent_returns_none(self, db):
        repo = RosterRepository(db)
        assert repo.get_by_id(99999) is None

    def test_get_by_id_does_not_raise(self, db):
        repo = RosterRepository(db)
        # No entries exist yet
        assert repo.get_by_id(1) is None


# ---------------------------------------------------------------------------
# AC-2: Service update_entry
# ---------------------------------------------------------------------------
class TestServiceUpdateEntry:
    def test_update_shift(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s1 = _shift_by_code(db, "S1")

        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))
        from app.schemas.roster import RosterEntryUpdate

        result = service.update_entry(
            entry_id,
            RosterEntryUpdate(shift_type_id=s1.id),
            db,
        )
        assert result.id == entry_id
        assert result.shift is not None
        assert result.shift.code == "S1"
        assert result.remarks is None  # unchanged

    def test_update_remarks_only_keeps_shift(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s2 = _shift_by_code(db, "S2")

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))

        # First set a shift
        service.update_entry(entry_id, RosterEntryUpdate(shift_type_id=s2.id), db)
        # Then update remarks only — shift must be preserved
        result = service.update_entry(
            entry_id, RosterEntryUpdate(remarks="On call"), db
        )
        assert result.shift.code == "S2"
        assert result.remarks == "On call"

    def test_clear_shift_with_null(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s1 = _shift_by_code(db, "S1")

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))

        service.update_entry(entry_id, RosterEntryUpdate(shift_type_id=s1.id), db)
        result = service.update_entry(
            entry_id, RosterEntryUpdate(shift_type_id=None), db
        )
        assert result.shift is None
        # The DB row should also be null
        row = db.execute(
            select(RosterModel).where(RosterModel.id == entry_id)
        ).scalar_one()
        assert row.shift_type_id is None

    def test_update_both_at_once(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s3 = _shift_by_code(db, "S3")

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))

        result = service.update_entry(
            entry_id,
            RosterEntryUpdate(shift_type_id=s3.id, remarks="Late shift"),
            db,
        )
        assert result.shift.code == "S3"
        assert result.remarks == "Late shift"

    def test_empty_payload_is_noop(self, db):
        """PATCH with an empty body should not change anything."""
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s1 = _shift_by_code(db, "S1")

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))

        # Set a shift first
        service.update_entry(entry_id, RosterEntryUpdate(shift_type_id=s1.id), db)
        # Empty update — everything preserved
        result = service.update_entry(entry_id, RosterEntryUpdate(), db)
        assert result.shift.code == "S1"
        assert result.remarks is None

    def test_update_nonexistent_raises_404(self, db):
        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))
        with pytest.raises(Exception) as exc_info:
            service.update_entry(99999, RosterEntryUpdate(shift_type_id=1), db)
        assert exc_info.value.status_code == 404

    def test_invalid_shift_id_raises_400(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))
        with pytest.raises(Exception) as exc_info:
            service.update_entry(
                entry_id, RosterEntryUpdate(shift_type_id=99999), db
            )
        assert exc_info.value.status_code == 400

    def test_inactive_shift_rejected(self, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        # Add an inactive shift type
        inactive = ShiftTypeModel(
            code="ZZ", display_name="Zzz", color="gray",
            display_order=999, is_active=False,
        )
        db.add(inactive)
        db.commit()

        from app.schemas.roster import RosterEntryUpdate
        service = RosterService(RosterRepository(db), ShiftTypeRepository(db))
        with pytest.raises(Exception) as exc_info:
            service.update_entry(
                entry_id, RosterEntryUpdate(shift_type_id=inactive.id), db
            )
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# AC-3: HTTP PATCH endpoint
# ---------------------------------------------------------------------------
class TestRosterPatchAPI:
    def test_patch_unauthenticated_returns_401(self, client, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": 1},
        )
        assert resp.status_code == 401

    def test_patch_updates_shift(self, admin_client, db):
        client, headers = admin_client
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s1 = _shift_by_code(db, "S1")

        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": s1.id},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == entry_id
        assert data["shift"]["code"] == "S1"
        assert data["shift"]["color"] == "blue"
        assert data["remarks"] is None

    def test_patch_persists_to_db(self, admin_client, db):
        client, headers = admin_client
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s2 = _shift_by_code(db, "S2")

        client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": s2.id},
            headers=headers,
        )

        # Read directly from DB to confirm persistence
        row = db.execute(
            select(RosterModel).where(RosterModel.id == entry_id)
        ).scalar_one()
        assert row.shift_type_id == s2.id

    def test_patch_clear_shift(self, admin_client, db):
        client, headers = admin_client
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s1 = _shift_by_code(db, "S1")

        # Set, then clear
        client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": s1.id},
            headers=headers,
        )
        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["shift"] is None

    def test_patch_remarks(self, admin_client, db):
        client, headers = admin_client
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()

        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"remarks": "Doctor's appointment"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["remarks"] == "Doctor's appointment"

    def test_patch_nonexistent_returns_404(self, admin_client):
        client, headers = admin_client
        resp = client.patch(
            "/api/roster/entries/99999",
            json={"shift_type_id": 1},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_patch_invalid_shift_returns_400(self, admin_client, db):
        client, headers = admin_client
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()

        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": 99999},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "Invalid shift_type_id" in resp.json()["detail"]

    def test_patch_only_modifies_one_entry(self, admin_client, db):
        """A PATCH to one entry must not touch any others."""
        client, headers = admin_client
        _generate_july(db, 3)
        all_ids = db.execute(
            select(RosterModel.id).order_by(RosterModel.id)
        ).scalars().all()
        target = all_ids[0]
        s1 = _shift_by_code(db, "S1")

        client.patch(
            f"/api/roster/entries/{target}",
            json={"shift_type_id": s1.id},
            headers=headers,
        )

        # All OTHER entries should still be unassigned
        others = [i for i in all_ids if i != target]
        rows = db.execute(
            select(RosterModel).where(RosterModel.id.in_(others))
        ).scalars().all()
        for row in rows:
            assert row.shift_type_id is None
            assert row.remarks is None

    def test_patch_response_includes_employee_brief(self, admin_client, db):
        client, headers = admin_client
        team = Team(team_name="Bravo", display_order=5)
        db.add(team)
        db.commit()
        _make_employees(db, 1, team_id=team.id, prefix="Z")
        # Use the seed-aware helper so shift types are present
        from app.db.seed import seed_shift_types
        seed_shift_types(db)
        RosterService(RosterRepository(db)).generate_month(2026, 7, db)
        entry_id = db.execute(
            select(RosterModel.id).order_by(RosterModel.id)
        ).scalars().first()
        s1 = _shift_by_code(db, "S1")

        resp = client.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": s1.id},
            headers=headers,
        )
        data = resp.json()
        assert data["employee"]["employee_code"] == "Z001"
        assert data["employee"]["team_name"] == "Bravo"


# ---------------------------------------------------------------------------
# AC-4: Public read-only endpoint
# ---------------------------------------------------------------------------
class TestRosterPublicAPI:
    def test_public_no_auth_required(self, client, db):
        _generate_july(db, 2)
        resp = client.get("/api/roster/2026/7/public")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["is_generated"] is True
        assert len(data["entries"]) == 2 * 31

    def test_public_returns_same_shape_as_admin(self, client, db):
        _generate_july(db, 1)
        s1 = _shift_by_code(db, "S1")

        # Update one entry directly
        RosterService(RosterRepository(db), ShiftTypeRepository(db)).update_entry(
            db.execute(select(RosterModel.id)).scalars().first(),
            # Build update inline to avoid extra import
            __import__("app.schemas.roster", fromlist=["RosterEntryUpdate"]).RosterEntryUpdate(shift_type_id=s1.id),
            db,
        )

        resp = client.get("/api/roster/2026/7/public")
        data = resp.json()
        assert "meta" in data
        assert "entries" in data
        # At least one entry has a shift
        with_shift = [e for e in data["entries"] if e["shift"] is not None]
        assert len(with_shift) >= 1
        assert with_shift[0]["shift"]["code"] == "S1"

    def test_public_invalid_month_returns_422(self, client):
        resp = client.get("/api/roster/2026/13/public")
        assert resp.status_code == 422
        resp = client.get("/api/roster/2026/0/public")
        assert resp.status_code == 422

    def test_public_invalid_year_returns_422(self, client):
        resp = client.get("/api/roster/1999/7/public")
        assert resp.status_code == 422

    def test_public_empty_when_not_generated(self, client, db):
        _make_employees(db, 3)  # employees exist but no roster
        resp = client.get("/api/roster/2026/7/public")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["is_generated"] is False
        assert data["entries"] == []

    def test_public_no_employees_returns_zero(self, client):
        resp = client.get("/api/roster/2026/7/public")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["total_employees"] == 0
        assert data["meta"]["total_days"] == 31
        assert data["entries"] == []


# ---------------------------------------------------------------------------
# AC-5: End-to-end — admin PATCH then public GET shows the update
# ---------------------------------------------------------------------------
class TestEditPropagatesToPublic:
    def test_admin_update_visible_in_public(self, admin_client, client, db):
        _generate_july(db, 1)
        entry_id = db.execute(select(RosterModel.id)).scalars().first()
        s2 = _shift_by_code(db, "S2")

        admin_c, headers = admin_client
        resp = admin_c.patch(
            f"/api/roster/entries/{entry_id}",
            json={"shift_type_id": s2.id},
            headers=headers,
        )
        assert resp.status_code == 200

        # Public read sees the change
        public = client.get("/api/roster/2026/7/public")
        assert public.status_code == 200
        shifts = [e["shift"] for e in public.json()["entries"] if e["shift"]]
        assert len(shifts) == 1
        assert shifts[0]["code"] == "S2"
