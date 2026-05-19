from sqlalchemy import Numeric, String

from src.infra.postgres import postgres_metadata


def test_postgres_metadata_includes_transaction_tables() -> None:
    assert {"transactions", "entries", "entry_tags"}.issubset(
        postgres_metadata.tables,
    )


def test_transactions_table_matches_v1_base_shape() -> None:
    transactions_table = postgres_metadata.tables["transactions"]

    assert set(transactions_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "effective_at",
        "title",
        "description",
        "status",
        "currency",
    }
    assert list(transactions_table.primary_key.columns.keys()) == ["id"]
    assert transactions_table.c.status.type.name == "transaction_status_enum"
    assert isinstance(transactions_table.c.currency.type, String)


def test_entries_table_matches_v1_base_shape() -> None:
    entries_table = postgres_metadata.tables["entries"]
    transaction_fk = next(iter(entries_table.c.transaction_id.foreign_keys))
    ledger_account_fk = next(iter(entries_table.c.ledger_account_id.foreign_keys))

    assert set(entries_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "transaction_id",
        "ledger_account_id",
        "amount",
        "statement_closing_date",
        "statement_due_date",
    }
    assert list(entries_table.primary_key.columns.keys()) == ["id"]
    assert isinstance(entries_table.c.amount.type, Numeric)
    assert transaction_fk.target_fullname == "transactions.id"
    assert transaction_fk.ondelete == "CASCADE"
    assert ledger_account_fk.target_fullname == "ledger_accounts.id"


def test_entry_tags_table_uses_composite_primary_key() -> None:
    entry_tags_table = postgres_metadata.tables["entry_tags"]
    entry_fk = next(iter(entry_tags_table.c.entry_id.foreign_keys))
    tag_fk = next(iter(entry_tags_table.c.tag_id.foreign_keys))

    assert list(entry_tags_table.columns.keys()) == ["entry_id", "tag_id"]
    assert list(entry_tags_table.primary_key.columns.keys()) == ["entry_id", "tag_id"]
    assert entry_fk.target_fullname == "entries.id"
    assert entry_fk.ondelete == "CASCADE"
    assert tag_fk.target_fullname == "tags.id"
