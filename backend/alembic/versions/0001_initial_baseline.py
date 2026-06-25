"""Initial baseline migration.

Revision ID: 0001_initial_baseline
Revises:
Create Date: 2024-01-01 00:00:00

This migration is intentionally empty. It exists to verify the
Alembic pipeline works end-to-end. Future schema changes should be
added in follow-up migrations.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No business tables yet — Phase 1 only verifies migrations work.
    pass


def downgrade() -> None:
    pass
