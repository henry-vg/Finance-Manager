"""create statement cycles table

Revision ID: 20260510_000006
Revises: 20260510_000005
Create Date: 2026-05-10 00:00:06
"""

import sqlalchemy as sa
from alembic import op

revision = "20260510_000006"
down_revision = "20260510_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "statement_cycles",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("ledger_account_id", sa.Integer(), nullable=False),
        sa.Column("cycle_start", sa.Date(), nullable=False),
        sa.Column("cycle_end", sa.Date(), nullable=False),
        sa.Column("closing_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
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
            ["ledger_account_id"],
            ["ledger_accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE TRIGGER set_statement_cycles_updated_at
        BEFORE UPDATE ON statement_cycles
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_statement_cycles_updated_at ON statement_cycles",
    )
    op.drop_table("statement_cycles")
