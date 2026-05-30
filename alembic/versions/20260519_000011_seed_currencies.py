"""seed currencies

Revision ID: 20260519_000011
Revises: 20260518_000010
Create Date: 2026-05-19 00:00:11
"""

import sqlalchemy as sa
from alembic import op

revision = "20260519_000011"
down_revision = "20260518_000010"
branch_labels = None
depends_on = None


currencies_table = sa.table(
    "currencies",
    sa.column("id", sa.Integer()),
    sa.column("iso_code", sa.String(length=3)),
    sa.column("iso_numeric", sa.String(length=3)),
    sa.column("name", sa.String(length=255)),
    sa.column("symbol", sa.String(length=16)),
    sa.column("decimal_places", sa.Integer()),
)


def upgrade() -> None:
    op.bulk_insert(
        currencies_table,
        [
            {
                "id": 1,
                "iso_code": "BRL",
                "iso_numeric": "986",
                "name": "Brazilian Real",
                "symbol": "R$",
                "decimal_places": 2,
            },
            {
                "id": 2,
                "iso_code": "USD",
                "iso_numeric": "840",
                "name": "United States Dollar",
                "symbol": "$",
                "decimal_places": 2,
            },
            {
                "id": 3,
                "iso_code": "EUR",
                "iso_numeric": "978",
                "name": "Euro",
                "symbol": "€",
                "decimal_places": 2,
            },
        ],
    )
    op.create_foreign_key(
        "fk_entries_currency_id_currencies",
        source_table="entries",
        referent_table="currencies",
        local_cols=["currency_id"],
        remote_cols=["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_entries_currency_id_currencies",
        "entries",
        type_="foreignkey",
    )
    op.execute(
        sa.text(
            "DELETE FROM currencies WHERE iso_code IN ('BRL', 'USD', 'EUR')",
        ),
    )
