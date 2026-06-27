"""Service for the ``Team`` domain."""

from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.models.team import Team
from app.repositories.team import TeamRepository
from app.schemas.team import TeamCreate, TeamRead


class TeamService:
    """High-level operations on teams."""

    def __init__(self, repository: TeamRepository) -> None:
        self.repository = repository

    def list_teams(self) -> List[TeamRead]:
        """Return all teams as read-schema instances."""
        teams: List[Team] = self.repository.list_all()
        return [TeamRead.model_validate(t) for t in teams]

    def create_team(self, data: TeamCreate, db: Session) -> TeamRead:
        """Create a new team. Raises ValueError on duplicate name."""
        name = (data.team_name or "").strip()
        if not name:
            raise ValueError("Team name must not be empty")

        if self.repository.get_by_name(name):
            raise ValueError(f"Team '{name}' already exists")

        team = Team(
            team_name=name,
            description=data.description,
            display_order=data.display_order,
            is_active=data.is_active,
        )
        team = self.repository.create(team)
        db.commit()
        return TeamRead.model_validate(team)
