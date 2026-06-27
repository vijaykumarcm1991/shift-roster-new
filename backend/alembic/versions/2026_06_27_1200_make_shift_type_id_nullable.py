"""make_shift_type_id_nullable

Phase 5: roster entries can be created without an assigned shift
(initially empty grid cells). The shift is filled in Phase 6.

Revision ID: 2026_06_27_1200
Revises: a9de19cbb87b
Create Date: 2026-06-27 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_06_27_1200"
down_revision: Union[str, None] = "a9de19cbb87b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow roster.shift_type_id to be NULL."""
    op.alter_column(
        "roster",
        "shift_type_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Revert: shift_type_id becomes required again.

    Note: this will fail if any roster rows have NULL shift_type_id.
    Backfill those rows first if you need to roll back.
    """
    op.alter_column(
        "roster",
        "shift_type_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
