"""add user soft delete columns

Revision ID: 20260504_000003
Revises: 20260502_000002
Create Date: 2026-05-04 00:00:03
"""

import sqlalchemy as sa
from alembic import op

revision = "20260504_000003"
down_revision = "20260502_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = TIMEZONE('UTC', CURRENT_TIMESTAMP);

            IF NEW.is_deleted IS TRUE AND OLD.is_deleted IS FALSE THEN
                NEW.deleted_at = TIMEZONE('UTC', CURRENT_TIMESTAMP);
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = TIMEZONE('UTC', CURRENT_TIMESTAMP);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
    )
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "is_deleted")
