from tests.unit.helpers import assert_module_has_symbol


def test_currency_repository_module_exposes_adapter() -> None:
    assert_module_has_symbol(
        "src.infra.postgres.aggregates.currency.repository",
        "SQLAlchemyCurrencyOutputAdapter",
    )
