from typing import Any, cast

from src.infra.postgres.aggregates.transaction.models.transactions import (
    TransactionRecord,
)


def test_transaction_record_declares_expected_table_name() -> None:
    assert TransactionRecord.__tablename__ == "transactions"


def test_transaction_record_table_matches_expected_shape() -> None:
    transactions_table = cast(Any, TransactionRecord).__table__

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
    }
    assert list(transactions_table.primary_key.columns.keys()) == ["id"]
    assert transactions_table.c.status.type.name == "transaction_status_enum"
