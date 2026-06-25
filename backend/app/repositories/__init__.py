"""Repository pattern data-access layer.

Repositories encapsulate raw SQLAlchemy queries so that services
remain free of query-construction details and can be unit-tested
with a stubbed repository.
"""

from app.repositories.shift_type import ShiftTypeRepository  # noqa: F401
from app.repositories.team import TeamRepository  # noqa: F401
