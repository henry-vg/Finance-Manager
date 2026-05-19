"""create currencies table

Revision ID: 20260518_000010
Revises: 20260511_000009
Create Date: 2026-05-18 00:00:10
"""

import sqlalchemy as sa
from alembic import op

revision = "20260518_000010"
down_revision = "20260511_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("iso_code", sa.String(length=3), nullable=False),
        sa.Column("iso_numeric", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
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
        sa.CheckConstraint(
            "decimal_places >= 0",
            name="ck_currencies_decimal_places",
        ),
        sa.CheckConstraint(
            "char_length(iso_code) = 3",
            name="ck_currencies_iso_code_length",
        ),
        sa.CheckConstraint(
            "char_length(iso_numeric) = 3",
            name="ck_currencies_iso_numeric_length",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_code", name="uq_currencies_iso_code"),
    )
    op.execute(
        """
        CREATE TRIGGER set_currencies_updated_at
        BEFORE UPDATE ON currencies
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_currencies_updated_at ON currencies")
    op.drop_table("currencies")
