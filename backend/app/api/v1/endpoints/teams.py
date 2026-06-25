"""``/api/teams`` endpoint."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.repositories.team import TeamRepository
from app.schemas.team import TeamRead
from app.services.team import TeamService

router = APIRouter(tags=["teams"])


@router.get("/teams", response_model=List[TeamRead])
def list_teams(db: Session = Depends(db_session)) -> List[TeamRead]:
    """Return every team (empty list if none have been created yet)."""
    service = TeamService(TeamRepository(db))
    return service.list_teams()
