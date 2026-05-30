"""seed test data

Revision ID: 20260519_000009
Revises: 20260519_000008
Create Date: 2026-05-19 00:00:10
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260519_000009"
down_revision = "20260519_000008"
branch_labels = None
depends_on = None

USER_ID_START = 100001
TAG_ID_START = 110001
LEDGER_ACCOUNT_ID_START = 120001
TRANSACTION_ID_START = 130001
ENTRY_ID_START = 140001

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

transaction_status_enum = postgresql.ENUM(
    "PENDING",
    "POSTED",
    "VOIDED",
    name="transaction_status_enum",
    create_type=False,
)

users_table = sa.table(
    "users",
    sa.column("id", sa.Integer()),
    sa.column("first_name", sa.String(length=255)),
    sa.column("last_name", sa.String(length=255)),
    sa.column("email", sa.String(length=255)),
    sa.column("password_hash", sa.String(length=255)),
    sa.column("birth_date", sa.Date()),
)

currencies_table = sa.table(
    "currencies",
    sa.column("id", sa.Integer()),
    sa.column("iso_code", sa.String(length=3)),
    sa.column("iso_numeric", sa.String(length=3)),
    sa.column("name", sa.String(length=255)),
    sa.column("symbol", sa.String(length=16)),
    sa.column("decimal_places", sa.Integer()),
)

tags_table = sa.table(
    "tags",
    sa.column("id", sa.Integer()),
    sa.column("title", sa.String(length=255)),
)

ledger_accounts_table = sa.table(
    "ledger_accounts",
    sa.column("id", sa.Integer()),
    sa.column("title", sa.String(length=255)),
    sa.column("type", ledger_account_type_enum),
    sa.column("instrument_kind", ledger_account_instrument_kind_enum),
)

transactions_table = sa.table(
    "transactions",
    sa.column("id", sa.Integer()),
    sa.column("effective_at", sa.DateTime(timezone=True)),
    sa.column("title", sa.String(length=255)),
    sa.column("description", sa.Text()),
    sa.column("status", transaction_status_enum),
)

entries_table = sa.table(
    "entries",
    sa.column("id", sa.Integer()),
    sa.column("transaction_id", sa.Integer()),
    sa.column("ledger_account_id", sa.Integer()),
    sa.column("currency_id", sa.Integer()),
    sa.column("amount", sa.Numeric()),
    sa.column("statement_closing_date", sa.Date()),
    sa.column("statement_due_date", sa.Date()),
)

entry_tags_table = sa.table(
    "entry_tags",
    sa.column("entry_id", sa.Integer()),
    sa.column("tag_id", sa.Integer()),
)


def _build_currencies() -> list[dict[str, object]]:
    return [
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
    ]


def _build_users() -> list[dict[str, object]]:
    return [
        {
            "id": USER_ID_START + offset,
            "first_name": f"Seed{offset + 1:02d}",
            "last_name": "User",
            "email": f"seed.user.{offset + 1:02d}@example.com",
            "password_hash": f"seed-hash-{offset + 1:02d}",
            "birth_date": date(1990 + (offset % 10), (offset % 12) + 1, 1),
        }
        for offset in range(20)
    ]


def _build_tags() -> list[dict[str, object]]:
    tag_titles = [
        "Food",
        "Housing",
        "Travel",
        "Utilities",
        "Leisure",
        "Health",
        "Education",
        "Transport",
        "Family",
        "Work",
        "Income",
        "Emergency",
        "Shopping",
        "Bills",
        "Savings",
        "Transfer",
        "Opening Balance",
        "Cashback",
        "Foreign Currency",
        "Subscriptions",
    ]

    return [
        {
            "id": TAG_ID_START + offset,
            "title": tag_title,
        }
        for offset, tag_title in enumerate(tag_titles)
    ]


def _build_ledger_accounts() -> list[dict[str, object]]:
    account_specs = [
        ("Main Checking BRL", "ASSET", "BANK_ACCOUNT"),
        ("Wallet BRL", "ASSET", "WALLET"),
        ("Savings BRL", "ASSET", "BANK_ACCOUNT"),
        ("Visa Platinum BRL", "LIABILITY", "CREDIT_CARD"),
        ("Mastercard Black BRL", "LIABILITY", "CREDIT_CARD"),
        ("Salary Income BRL", "INCOME", None),
        ("Freelance Income BRL", "INCOME", None),
        ("Groceries Expense BRL", "EXPENSE", None),
        ("Rent Expense BRL", "EXPENSE", None),
        ("Travel Expense BRL", "EXPENSE", None),
        ("Emergency Fund Equity BRL", "EQUITY", None),
        ("Opening Balance Equity BRL", "EQUITY", None),
        ("Main Checking USD", "ASSET", "BANK_ACCOUNT"),
        ("Travel Card USD", "LIABILITY", "CREDIT_CARD"),
        ("Travel Expense USD", "EXPENSE", None),
        ("Main Checking EUR", "ASSET", "BANK_ACCOUNT"),
        ("Travel Card EUR", "LIABILITY", "CREDIT_CARD"),
        ("Travel Expense EUR", "EXPENSE", None),
        ("Cashback Asset BRL", "ASSET", None),
        ("Utilities Expense BRL", "EXPENSE", None),
    ]

    return [
        {
            "id": LEDGER_ACCOUNT_ID_START + offset,
            "title": title,
            "type": account_type,
            "instrument_kind": instrument_kind,
        }
        for offset, (title, account_type, instrument_kind) in enumerate(account_specs)
    ]


def _build_transaction_specs() -> list[dict[str, object]]:
    return [
        {
            "title": "Visa groceries run",
            "description": "Seed credit-card purchase 01",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 7,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 3,
            "amount": Decimal("245.80"),
            "statement_closing_date": date(2026, 5, 31),
            "statement_due_date": date(2026, 6, 10),
        },
        {
            "title": "Visa rent payment",
            "description": "Seed credit-card purchase 02",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 8,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 3,
            "amount": Decimal("1200.00"),
            "statement_closing_date": date(2026, 5, 31),
            "statement_due_date": date(2026, 6, 10),
        },
        {
            "title": "Mastercard travel booking",
            "description": "Seed credit-card purchase 03",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 9,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 4,
            "amount": Decimal("780.25"),
            "statement_closing_date": date(2026, 5, 28),
            "statement_due_date": date(2026, 6, 7),
        },
        {
            "title": "Visa utilities bundle",
            "description": "Seed credit-card purchase 04",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 19,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 3,
            "amount": Decimal("340.00"),
            "statement_closing_date": date(2026, 5, 31),
            "statement_due_date": date(2026, 6, 10),
        },
        {
            "title": "Mastercard weekend groceries",
            "description": "Seed credit-card purchase 05",
            "status": "VOIDED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 7,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 4,
            "amount": Decimal("186.90"),
            "statement_closing_date": date(2026, 5, 28),
            "statement_due_date": date(2026, 6, 7),
        },
        {
            "title": "Visa hotel booking",
            "description": "Seed credit-card purchase 06",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 9,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 3,
            "amount": Decimal("930.40"),
            "statement_closing_date": date(2026, 6, 30),
            "statement_due_date": date(2026, 7, 10),
        },
        {
            "title": "Mastercard electricity bill",
            "description": "Seed credit-card purchase 07",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 19,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 4,
            "amount": Decimal("289.55"),
            "statement_closing_date": date(2026, 6, 28),
            "statement_due_date": date(2026, 7, 7),
        },
        {
            "title": "Visa family dinner",
            "description": "Seed credit-card purchase 08",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 7,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 3,
            "amount": Decimal("154.70"),
            "statement_closing_date": date(2026, 6, 30),
            "statement_due_date": date(2026, 7, 10),
        },
        {
            "title": "Checking groceries",
            "description": "Seed debit purchase 09",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 7,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "amount": Decimal("98.30"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Checking rent transfer",
            "description": "Seed debit purchase 10",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 8,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "amount": Decimal("1400.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Wallet utilities cashout",
            "description": "Seed wallet purchase 11",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 19,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 1,
            "amount": Decimal("120.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Savings travel booking",
            "description": "Seed savings purchase 12",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 9,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 2,
            "amount": Decimal("450.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Salary deposit",
            "description": "Seed income transaction 13",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 5,
            "amount": Decimal("6200.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Freelance deposit",
            "description": "Seed income transaction 14",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 6,
            "amount": Decimal("1800.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Cashback recognition",
            "description": "Seed income transaction 15",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 18,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 6,
            "amount": Decimal("75.50"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Savings allocation",
            "description": "Seed transfer transaction 16",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 2,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "amount": Decimal("850.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Opening balance setup",
            "description": "Seed equity transaction 17",
            "status": "POSTED",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 0,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 11,
            "amount": Decimal("10000.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "Emergency reserve contribution",
            "description": "Seed equity transaction 18",
            "status": "PENDING",
            "currency_id": 1,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 2,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 10,
            "amount": Decimal("400.00"),
            "statement_closing_date": None,
            "statement_due_date": None,
        },
        {
            "title": "USD travel card charge",
            "description": "Seed foreign transaction 19",
            "status": "PENDING",
            "currency_id": 2,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 14,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 13,
            "amount": Decimal("320.00"),
            "statement_closing_date": date(2026, 6, 30),
            "statement_due_date": date(2026, 7, 10),
        },
        {
            "title": "EUR travel card charge",
            "description": "Seed foreign transaction 20",
            "status": "POSTED",
            "currency_id": 3,
            "positive_account_id": LEDGER_ACCOUNT_ID_START + 17,
            "negative_account_id": LEDGER_ACCOUNT_ID_START + 16,
            "amount": Decimal("280.00"),
            "statement_closing_date": date(2026, 6, 27),
            "statement_due_date": date(2026, 7, 8),
        },
    ]


def _build_transactions() -> list[dict[str, object]]:
    transaction_specs = _build_transaction_specs()

    return [
        {
            "id": TRANSACTION_ID_START + offset,
            "effective_at": datetime(
                2026,
                6,
                (offset % 28) + 1,
                10,
                0,
                tzinfo=UTC,
            ),
            "title": transaction_spec["title"],
            "description": transaction_spec["description"],
            "status": transaction_spec["status"],
        }
        for offset, transaction_spec in enumerate(transaction_specs)
    ]


def _build_entries() -> list[dict[str, object]]:
    entry_rows: list[dict[str, object]] = []

    for offset, transaction_spec in enumerate(_build_transaction_specs()):
        transaction_id = TRANSACTION_ID_START + offset
        positive_entry_id = ENTRY_ID_START + (offset * 2)
        negative_entry_id = positive_entry_id + 1

        entry_rows.append(
            {
                "id": positive_entry_id,
                "transaction_id": transaction_id,
                "ledger_account_id": transaction_spec["positive_account_id"],
                "currency_id": transaction_spec["currency_id"],
                "amount": transaction_spec["amount"],
                "statement_closing_date": None,
                "statement_due_date": None,
            },
        )
        entry_rows.append(
            {
                "id": negative_entry_id,
                "transaction_id": transaction_id,
                "ledger_account_id": transaction_spec["negative_account_id"],
                "currency_id": transaction_spec["currency_id"],
                "amount": -transaction_spec["amount"],
                "statement_closing_date": transaction_spec["statement_closing_date"],
                "statement_due_date": transaction_spec["statement_due_date"],
            },
        )

    return entry_rows


def _build_entry_tags() -> list[dict[str, object]]:
    return [
        {
            "entry_id": ENTRY_ID_START + (offset * 2),
            "tag_id": TAG_ID_START + offset,
        }
        for offset in range(20)
    ]


def _sync_identity_sequence(table_name: str) -> None:
    op.execute(
        sa.text(
            (
                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
                f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table_name}"
            ),
        ),
    )


def upgrade() -> None:
    op.bulk_insert(currencies_table, _build_currencies())
    op.bulk_insert(users_table, _build_users())
    op.bulk_insert(tags_table, _build_tags())
    op.bulk_insert(ledger_accounts_table, _build_ledger_accounts())
    op.bulk_insert(transactions_table, _build_transactions())
    op.bulk_insert(entries_table, _build_entries())
    op.bulk_insert(entry_tags_table, _build_entry_tags())

    _sync_identity_sequence("currencies")
    _sync_identity_sequence("users")
    _sync_identity_sequence("tags")
    _sync_identity_sequence("ledger_accounts")
    _sync_identity_sequence("transactions")
    _sync_identity_sequence("entries")


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM entry_tags WHERE entry_id BETWEEN :start_id AND :end_id",
        ),
        {
            "start_id": ENTRY_ID_START,
            "end_id": ENTRY_ID_START + 39,
        },
    )
    op.execute(
        sa.text("DELETE FROM entries WHERE id BETWEEN :start_id AND :end_id"),
        {
            "start_id": ENTRY_ID_START,
            "end_id": ENTRY_ID_START + 39,
        },
    )
    op.execute(
        sa.text(
            "DELETE FROM transactions WHERE id BETWEEN :start_id AND :end_id",
        ),
        {
            "start_id": TRANSACTION_ID_START,
            "end_id": TRANSACTION_ID_START + 19,
        },
    )
    op.execute(
        sa.text(
            "DELETE FROM ledger_accounts WHERE id BETWEEN :start_id AND :end_id",
        ),
        {
            "start_id": LEDGER_ACCOUNT_ID_START,
            "end_id": LEDGER_ACCOUNT_ID_START + 19,
        },
    )
    op.execute(
        sa.text("DELETE FROM tags WHERE id BETWEEN :start_id AND :end_id"),
        {
            "start_id": TAG_ID_START,
            "end_id": TAG_ID_START + 19,
        },
    )
    op.execute(
        sa.text("DELETE FROM users WHERE id BETWEEN :start_id AND :end_id"),
        {
            "start_id": USER_ID_START,
            "end_id": USER_ID_START + 19,
        },
    )
    op.execute(
        sa.text(
            "DELETE FROM currencies WHERE iso_code IN ('BRL', 'USD', 'EUR')",
        ),
    )

    _sync_identity_sequence("currencies")
    _sync_identity_sequence("users")
    _sync_identity_sequence("tags")
    _sync_identity_sequence("ledger_accounts")
    _sync_identity_sequence("transactions")
    _sync_identity_sequence("entries")
