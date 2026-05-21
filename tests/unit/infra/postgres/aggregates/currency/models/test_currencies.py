from sqlalchemy import CheckConstraint, String, UniqueConstraint

from src.infra.postgres.aggregates.currency.models.currencies import (
    CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME,
    CurrencyRecord,
)


def test_currency_record_declares_expected_table_name() -> None:
    assert CurrencyRecord.__tablename__ == "currencies"


def test_currency_record_declares_expected_unique_constraint_name() -> None:
    assert CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME == "uq_currencies_iso_code"


def test_currency_record_table_matches_expected_shape_and_constraints() -> None:
    currencies_table = CurrencyRecord.__table__
    constraints_by_name = {
        constraint.name: constraint
        for constraint in currencies_table.constraints
        if constraint.name is not None
    }

    assert set(currencies_table.columns.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "iso_code",
        "iso_numeric",
        "name",
        "symbol",
        "decimal_places",
    }
    assert list(currencies_table.primary_key.columns.keys()) == ["id"]
    assert isinstance(currencies_table.c.iso_code.type, String)
    assert isinstance(currencies_table.c.iso_numeric.type, String)
    assert isinstance(currencies_table.c.name.type, String)
    assert isinstance(currencies_table.c.symbol.type, String)
    assert isinstance(
        constraints_by_name[CURRENCY_ISO_CODE_UNIQUE_CONSTRAINT_NAME],
        UniqueConstraint,
    )
    assert isinstance(
        constraints_by_name["ck_currencies_decimal_places"],
        CheckConstraint,
    )
    assert isinstance(
        constraints_by_name["ck_currencies_iso_code_length"],
        CheckConstraint,
    )
    assert isinstance(
        constraints_by_name["ck_currencies_iso_numeric_length"],
        CheckConstraint,
    )
