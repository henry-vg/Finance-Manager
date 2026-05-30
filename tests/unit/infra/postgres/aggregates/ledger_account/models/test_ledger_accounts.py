from src.infra.postgres.aggregates.ledger_account.models.ledger_accounts import (
    LedgerAccountRecord,
)


def test_ledger_account_record_declares_expected_table_name() -> None:
    assert LedgerAccountRecord.__tablename__ == "ledger_accounts"


def test_ledger_account_record_table_matches_expected_shape() -> None:
    ledger_accounts_table = LedgerAccountRecord.__table__

    assert set(ledger_accounts_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "title",
        "type",
        "instrument_kind",
    }
    assert list(ledger_accounts_table.primary_key.columns.keys()) == ["id"]
    assert ledger_accounts_table.c["type"].type.name == "ledger_account_type_enum"
    assert (
        ledger_accounts_table.c["instrument_kind"].type.name
        == "ledger_account_instrument_kind_enum"
    )
