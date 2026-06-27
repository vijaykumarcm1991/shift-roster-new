"""``/api/teams`` endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.auth import require_admin
from app.models.user import User
from app.repositories.team import TeamRepository
from app.schemas.team import TeamCreate, TeamRead
from app.services.team import TeamService

router = APIRouter(tags=["teams"])


@router.get("/teams", response_model=List[TeamRead])
def list_teams(db: Session = Depends(db_session)) -> List[TeamRead]:
    """Return every team (empty list if none have been created yet)."""
    service = TeamService(TeamRepository(db))
    return service.list_teams()


@router.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
    body: TeamCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> TeamRead:
    """Create a new team. Admin-only."""
    service = TeamService(TeamRepository(db))
    try:
        return service.create_team(body, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
