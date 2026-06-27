"""Admin-only API endpoints.

All routes under this module require the ADMIN role.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.auth import require_admin
from app.models.user import User
from app.repositories.team import TeamRepository
from app.schemas.auth import MeResponse
from app.schemas.team import TeamRead
from app.services.auth import AuthService
from app.services.team import TeamService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=MeResponse)
def admin_dashboard(current_user: User = Depends(require_admin)) -> MeResponse:
    """Placeholder admin endpoint — verifies admin access."""
    return AuthService.user_to_me(current_user)


@router.get("/teams", response_model=List[TeamRead])
def list_teams_for_admin(
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> List[TeamRead]:
    """Return every team (admin-only). Used by the Employee Directory's team filter."""
    service = TeamService(TeamRepository(db))
    return service.list_teams()
