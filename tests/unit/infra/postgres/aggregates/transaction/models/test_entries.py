from sqlalchemy import Numeric

from src.infra.postgres.aggregates.transaction.models.entries import EntryRecord


def test_entry_record_declares_expected_table_name() -> None:
    assert EntryRecord.__tablename__ == "entries"


def test_entry_record_table_matches_expected_shape() -> None:
    entries_table = EntryRecord.__table__
    transaction_fk = next(iter(entries_table.c.transaction_id.foreign_keys))
    ledger_account_fk = next(iter(entries_table.c.ledger_account_id.foreign_keys))
    currency_fk = next(iter(entries_table.c.currency_id.foreign_keys))

    assert set(entries_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "transaction_id",
        "ledger_account_id",
        "currency_id",
        "amount",
        "statement_closing_date",
        "statement_due_date",
    }
    assert list(entries_table.primary_key.columns.keys()) == ["id"]
    assert isinstance(entries_table.c.amount.type, Numeric)
    assert transaction_fk.target_fullname == "transactions.id"
    assert transaction_fk.ondelete == "CASCADE"
    assert ledger_account_fk.target_fullname == "ledger_accounts.id"
    assert currency_fk.target_fullname == "currencies.id"
