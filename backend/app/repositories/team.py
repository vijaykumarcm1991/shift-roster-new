"""Repository for the ``Team`` model."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team


class TeamRepository:
    """Data-access object for ``Team`` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> List[Team]:
        """Return every team, ordered by display_order then name."""
        stmt = select(Team).order_by(Team.display_order, Team.team_name)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, team_id: int) -> Optional[Team]:
        """Return a team by id, or None."""
        return self.db.get(Team, team_id)

    def get_by_name(self, name: str) -> Optional[Team]:
        """Return a team by exact name match, or None."""
        stmt = select(Team).where(Team.team_name == name)
        return self.db.execute(stmt).scalars().first()

    def create(self, team: Team) -> Team:
        """Add a new team and return it."""
        self.db.add(team)
        self.db.flush()
        self.db.refresh(team)
        return team
