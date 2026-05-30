"""create transactions table

Revision ID: 20260511_000006
Revises: 20260510_000005
Create Date: 2026-05-11 00:00:07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260511_000006"
down_revision = "20260510_000005"
branch_labels = None
depends_on = None


transaction_status_enum = postgresql.ENUM(
    "PENDING",
    "POSTED",
    "VOIDED",
    name="transaction_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    transaction_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", transaction_status_enum, nullable=False),
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
        CREATE TRIGGER set_transactions_updated_at
        BEFORE UPDATE ON transactions
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.execute(
        "DROP TRIGGER IF EXISTS set_transactions_updated_at ON transactions",
    )
    op.drop_table("transactions")

    transaction_status_enum.drop(bind, checkfirst=True)
