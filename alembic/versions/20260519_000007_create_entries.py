"""create entries table

Revision ID: 20260519_000007
Revises: 20260518_000006
Create Date: 2026-05-19 00:00:08
"""

import sqlalchemy as sa
from alembic import op

revision = "20260519_000007"
down_revision = "20260518_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("ledger_account_id", sa.Integer(), nullable=False),
        sa.Column("currency_id", sa.Integer(), nullable=False),
        sa.Column("amount_in_dollars", sa.Numeric(), nullable=False),
        sa.Column(
            "planned_exchange_rate_to_dollars",
            sa.Numeric(),
            nullable=False,
        ),
        sa.Column(
            "posting_exchange_rate_to_dollars",
            sa.Numeric(),
            nullable=True,
        ),
        sa.Column("statement_closing_date", sa.Date(), nullable=True),
        sa.Column("statement_due_date", sa.Date(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ledger_account_id"],
            ["ledger_accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE TRIGGER set_entries_updated_at
        BEFORE UPDATE ON entries
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_entries_updated_at ON entries",
    )
    op.drop_table("entries")
