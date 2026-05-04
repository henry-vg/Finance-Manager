"""baseline

Revision ID: 20250502_000001
Revises:
Create Date: 2026-05-02 00:00:01
"""

from alembic import op

revision = "20250502_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
