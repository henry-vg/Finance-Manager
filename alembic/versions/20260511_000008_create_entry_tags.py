"""create entry tags table

Revision ID: 20260511_000008
Revises: 20260511_000007
Create Date: 2026-05-11 00:00:09
"""

import sqlalchemy as sa
from alembic import op

revision = "20260511_000008"
down_revision = "20260511_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entry_tags",
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
        sa.PrimaryKeyConstraint("entry_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("entry_tags")
