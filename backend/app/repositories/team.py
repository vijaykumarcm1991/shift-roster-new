"""Repository for the ``Team`` model."""

from __future__ import annotations

from typing import List

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
