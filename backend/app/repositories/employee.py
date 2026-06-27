"""Repository for the ``Employee`` model."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee


class EmployeeRepository:
    """Data-access object for ``Employee`` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, employee_id: int) -> Optional[Employee]:
        """Return a single employee by id, or None."""
        return self.db.get(Employee, employee_id)

    def get_by_code(self, code: str) -> Optional[Employee]:
        """Return an employee by employee_code (case-insensitive), or None."""
        stmt = select(Employee).where(func.lower(Employee.employee_code) == func.lower(code))
        return self.db.execute(stmt).scalars().first()

    def get_by_email(self, email: str) -> Optional[Employee]:
        """Return an employee by email (case-insensitive), or None."""
        stmt = select(Employee).where(func.lower(Employee.email) == func.lower(email))
        return self.db.execute(stmt).scalars().first()

    def count(
        self,
        search: Optional[str] = None,
        team: Optional[int] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count employees matching the given filters."""
        stmt = select(func.count(Employee.id))
        stmt = self._apply_filters(stmt, search, team, status)
        return self.db.execute(stmt).scalar() or 0

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        team: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Employee]:
        """Return a page of employees matching the filters."""
        stmt = select(Employee).options(joinedload(Employee.team))
        stmt = self._apply_filters(stmt, search, team, status)
        stmt = stmt.order_by(Employee.employee_name.asc(), Employee.id.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.execute(stmt).unique().scalars().all())

    def create(self, employee: Employee) -> Employee:
        """Add a new employee and return it."""
        self.db.add(employee)
        self.db.flush()
        self.db.refresh(employee)
        return employee

    def update(self, employee: Employee) -> Employee:
        """Flush updates and return the refreshed instance."""
        self.db.flush()
        self.db.refresh(employee)
        return employee

    # ---- internal helpers ----

    @staticmethod
    def _apply_filters(stmt, search: Optional[str], team: Optional[int], status: Optional[str]):
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Employee.employee_code.ilike(pattern),
                    Employee.employee_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                    Employee.designation.ilike(pattern),
                )
            )
        if team is not None:
            stmt = stmt.where(Employee.team_id == team)
        if status == "active":
            stmt = stmt.where(Employee.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(Employee.is_active.is_(False))
        return stmt
