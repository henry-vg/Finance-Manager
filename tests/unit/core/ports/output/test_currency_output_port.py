from tests.unit.helpers import assert_module_has_symbol


def test_currency_output_port_module_exposes_protocol() -> None:
    assert_module_has_symbol(
        "src.core.ports.output.currency_output_port",
        "CurrencyOutputPort",
    )
