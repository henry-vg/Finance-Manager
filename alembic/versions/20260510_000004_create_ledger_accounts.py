"""create ledger accounts table

Revision ID: 20260510_000004
Revises: 20260510_000003
Create Date: 2026-05-10 00:00:05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260510_000004"
down_revision = "20260510_000003"
branch_labels = None
depends_on = None


ledger_account_type_enum = postgresql.ENUM(
    "ASSET",
    "LIABILITY",
    "INCOME",
    "EXPENSE",
    "EQUITY",
    name="ledger_account_type_enum",
    create_type=False,
)

ledger_account_instrument_kind_enum = postgresql.ENUM(
    "BANK_ACCOUNT",
    "CREDIT_CARD",
    "WALLET",
    name="ledger_account_instrument_kind_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    ledger_account_type_enum.create(bind, checkfirst=True)
    ledger_account_instrument_kind_enum.create(bind, checkfirst=True)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", ledger_account_type_enum, nullable=False),
        sa.Column(
            "instrument_kind",
            ledger_account_instrument_kind_enum,
            nullable=True,
        ),
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
        CREATE TRIGGER set_ledger_accounts_updated_at
        BEFORE UPDATE ON ledger_accounts
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.execute(
        "DROP TRIGGER IF EXISTS set_ledger_accounts_updated_at ON ledger_accounts",
    )
    op.drop_table("ledger_accounts")

    ledger_account_instrument_kind_enum.drop(bind, checkfirst=True)
    ledger_account_type_enum.drop(bind, checkfirst=True)
