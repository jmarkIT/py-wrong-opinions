"""Make week user_id nullable for unclaimed weeks

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make weeks.user_id nullable and change ondelete to SET NULL."""
    # For SQLite, batch_alter_table recreates the table with new schema
    # We need to specify recreate="always" and provide the new column definition
    with op.batch_alter_table(
        "weeks",
        schema=None,
        recreate="always",
        table_args=[
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name="fk_weeks_user_id_users", ondelete="SET NULL"
            ),
            sa.UniqueConstraint("year", "week_number", name="uq_year_week"),
        ],
    ) as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    """Revert weeks.user_id to non-nullable with CASCADE delete."""
    with op.batch_alter_table(
        "weeks",
        schema=None,
        recreate="always",
        table_args=[
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name="fk_weeks_user_id_users", ondelete="CASCADE"
            ),
            sa.UniqueConstraint("year", "week_number", name="uq_year_week"),
        ],
    ) as batch_op:
        # This will fail if there are NULL values in user_id
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
