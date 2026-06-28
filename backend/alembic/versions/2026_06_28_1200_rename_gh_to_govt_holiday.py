"""rename_GH_to_Govt_Holiday

GH was originally seeded as 'Gas Holiday'. That was a mistake —
GH stands for Government Holiday.  This migration renames the
display_name in the shift_types table so the existing data row
matches the corrected seed.

Revision ID: 2026_06_28_1200
Revises: 2026_06_27_1200
Create Date: 2026-06-28 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026_06_28_1200"
down_revision: Union[str, None] = "2026_06_27_1200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename GH's display_name from 'Gas Holiday' to 'Govt Holiday'."""
    op.execute(
        sa.text(
            "UPDATE shift_types "
            "SET display_name = 'Govt Holiday' "
            "WHERE code = 'GH' AND display_name = 'Gas Holiday'"
        )
    )


def downgrade() -> None:
    """Revert: rename 'Govt Holiday' back to 'Gas Holiday'.

    Only touches rows that were affected by the upgrade — leaves
    any other 'Govt Holiday' rows alone (there shouldn't be any,
    but be safe).
    """
    op.execute(
        sa.text(
            "UPDATE shift_types "
            "SET display_name = 'Gas Holiday' "
            "WHERE code = 'GH' AND display_name = 'Govt Holiday'"
        )
    )
