"""Admin-only API endpoints.

All routes under this module require the ADMIN role.
"""

from fastapi import APIRouter, Depends

from app.core.auth import require_admin
from app.models.user import User
from app.schemas.auth import MeResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=MeResponse)
def admin_dashboard(current_user: User = Depends(require_admin)) -> MeResponse:
    """Placeholder admin endpoint — verifies admin access."""
    from app.services.auth import AuthService

    return AuthService.user_to_me(current_user)
