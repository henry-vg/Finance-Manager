from tests.unit.helpers import assert_module_has_symbol


def test_ledger_account_repository_module_exposes_adapter() -> None:
    assert_module_has_symbol(
        "src.infra.postgres.aggregates.ledger_account.repository",
        "SQLAlchemyLedgerAccountOutputAdapter",
    )
