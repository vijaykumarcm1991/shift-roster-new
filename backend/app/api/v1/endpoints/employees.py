"""Employee CRUD endpoints — list, get, create, update, soft-delete."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core.auth import require_admin
from app.models.user import User
from app.repositories.employee import EmployeeRepository
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    PaginatedResponse,
)
from app.services.employee import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])


def _format_validation_error(exc: ValidationError) -> str:
    """Convert a Pydantic ValidationError into a single human-readable string."""
    errors = exc.errors()
    if not errors:
        return "Invalid input"
    first = errors[0]
    loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    msg = first.get("msg", "Invalid input")
    if loc:
        return f"{loc}: {msg}"
    return msg


@router.get("", response_model=PaginatedResponse)
def list_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: Optional[str] = Query(default=None, max_length=120),
    team: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None, pattern="^(active|inactive)$"),
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> PaginatedResponse:
    """Return a paginated, filterable list of employees."""
    service = EmployeeService(EmployeeRepository(db))
    return service.list_employees(
        page=page, page_size=page_size, search=search, team=team, status=status
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> EmployeeRead:
    """Return a single employee by id."""
    service = EmployeeService(EmployeeRepository(db))
    result = service.get_employee(employee_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    body: EmployeeCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> EmployeeRead:
    """Create a new employee."""
    service = EmployeeService(EmployeeRepository(db))
    try:
        return service.create_employee(body, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> EmployeeRead:
    """Update an existing employee."""
    service = EmployeeService(EmployeeRepository(db))
    try:
        result = service.update_employee(employee_id, body, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@router.delete("/{employee_id}", response_model=EmployeeRead)
def delete_employee(
    employee_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(require_admin),
) -> EmployeeRead:
    """Soft-delete an employee (sets is_active=False)."""
    service = EmployeeService(EmployeeRepository(db))
    result = service.delete_employee(employee_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result
