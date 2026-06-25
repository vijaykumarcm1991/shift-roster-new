"""Service for the ``Team`` domain."""

from __future__ import annotations

from typing import List

from app.models.team import Team
from app.repositories.team import TeamRepository
from app.schemas.team import TeamRead


class TeamService:
    """High-level operations on teams."""

    def __init__(self, repository: TeamRepository) -> None:
        self.repository = repository

    def list_teams(self) -> List[TeamRead]:
        """Return all teams as read-schema instances."""
        teams: List[Team] = self.repository.list_all()
        return [TeamRead.model_validate(t) for t in teams]
