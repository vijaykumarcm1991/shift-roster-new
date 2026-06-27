"""Tests for the team management API."""

import pytest
from sqlalchemy import select

from app.repositories.team import TeamRepository
from app.services.team import TeamService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _auth_header(client) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_client(client, db):
    """TestClient logged in as admin (seeds the test DB with the admin user)."""
    from app.core.security import hash_password
    from app.models import User

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
    return client, _auth_header(client)


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------
class TestTeamService:
    def test_create_team(self, db):
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        result = svc.create_team(
            TeamCreate(team_name="Alpha", display_order=10), db
        )
        assert result.id is not None
        assert result.team_name == "Alpha"
        assert result.display_order == 10
        assert result.is_active is True

    def test_create_team_strips_whitespace(self, db):
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        result = svc.create_team(TeamCreate(team_name="  Bravo  "), db)
        assert result.team_name == "Bravo"

    def test_create_team_rejects_duplicate_name(self, db):
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        svc.create_team(TeamCreate(team_name="Charlie"), db)
        with pytest.raises(ValueError, match="already exists"):
            svc.create_team(TeamCreate(team_name="Charlie"), db)

    def test_create_team_rejects_empty_name(self, db):
        # Pure empty string is caught at the Pydantic schema layer (min_length=1).
        from pydantic import ValidationError
        from app.schemas.team import TeamCreate

        with pytest.raises(ValidationError):
            TeamCreate(team_name="")

    def test_create_team_rejects_whitespace_only_name(self, db):
        # Whitespace-only passes Pydantic but is rejected at the service layer.
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        with pytest.raises(ValueError, match="empty"):
            svc.create_team(TeamCreate(team_name="   "), db)

    def test_create_team_with_description(self, db):
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        result = svc.create_team(
            TeamCreate(
                team_name="Delta",
                description="Operations team",
                display_order=20,
                is_active=True,
            ),
            db,
        )
        assert result.description == "Operations team"

    def test_list_teams_returns_all(self, db):
        svc = TeamService(TeamRepository(db))
        from app.schemas.team import TeamCreate

        svc.create_team(TeamCreate(team_name="A", display_order=10), db)
        svc.create_team(TeamCreate(team_name="B", display_order=5), db)
        svc.create_team(TeamCreate(team_name="C", display_order=20), db)
        teams = svc.list_teams()
        assert len(teams) == 3
        # Ordered by display_order, then team_name
        assert [t.team_name for t in teams] == ["B", "A", "C"]


# ---------------------------------------------------------------------------
# HTTP API tests
# ---------------------------------------------------------------------------
class TestTeamAPI:
    def test_post_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/teams", json={"team_name": "Anonymous"}
        )
        assert resp.status_code == 401

    def test_post_creates_team(self, admin_client):
        client, headers = admin_client
        resp = client.post(
            "/api/teams",
            json={"team_name": "Echo", "display_order": 30},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["team_name"] == "Echo"
        assert data["display_order"] == 30
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_post_duplicate_returns_400(self, admin_client, db):
        client, headers = admin_client
        # First, seed via API
        client.post(
            "/api/teams",
            json={"team_name": "Foxtrot"},
            headers=headers,
        )
        # Second, should be rejected
        resp = client.post(
            "/api/teams",
            json={"team_name": "Foxtrot"},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    def test_post_empty_name_returns_422(self, admin_client):
        client, headers = admin_client
        resp = client.post(
            "/api/teams",
            json={"team_name": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_post_negative_display_order_returns_422(self, admin_client):
        client, headers = admin_client
        resp = client.post(
            "/api/teams",
            json={"team_name": "Golf", "display_order": -1},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_get_returns_created_teams(self, admin_client):
        client, headers = admin_client
        client.post(
            "/api/teams", json={"team_name": "Hotel"}, headers=headers
        )
        client.post(
            "/api/teams", json={"team_name": "India"}, headers=headers
        )
        resp = client.get("/api/teams", headers=headers)
        assert resp.status_code == 200
        names = [t["team_name"] for t in resp.json()]
        assert "Hotel" in names
        assert "India" in names

    def test_new_team_appears_in_employee_form(self, admin_client):
        """The new team should be retrievable via GET for the dropdown to populate."""
        client, headers = admin_client
        resp = client.post(
            "/api/teams",
            json={"team_name": "Juliet", "description": "J team"},
            headers=headers,
        )
        team_id = resp.json()["id"]
        # Fetch list and confirm presence
        resp = client.get("/api/teams", headers=headers)
        teams = {t["team_name"]: t for t in resp.json()}
        assert "Juliet" in teams
        assert teams["Juliet"]["id"] == team_id
        assert teams["Juliet"]["description"] == "J team"
