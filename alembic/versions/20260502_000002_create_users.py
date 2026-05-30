"""create users table

Revision ID: 20260502_000002
Revises: 20250502_000001
Create Date: 2026-05-02 00:00:02
"""

import sqlalchemy as sa
from alembic import op

revision = "20260502_000002"
down_revision = "20250502_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
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
    op.execute(
        """
        CREATE TRIGGER set_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_users_updated_at ON users")
    op.drop_table("users")
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
