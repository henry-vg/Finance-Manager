from tests.unit.helpers import assert_module_has_symbol


def test_ledger_account_input_port_module_exposes_protocol() -> None:
    assert_module_has_symbol(
        "src.core.ports.input.ledger_account_input_port",
        "LedgerAccountInputPort",
    )
