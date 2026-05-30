"""create tags table

Revision ID: 20260510_000003
Revises: 20260502_000002
Create Date: 2026-05-10 00:00:04
"""

import sqlalchemy as sa
from alembic import op

revision = "20260510_000003"
down_revision = "20260502_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE TRIGGER set_tags_updated_at
        BEFORE UPDATE ON tags
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_tags_updated_at ON tags")
    op.drop_table("tags")
