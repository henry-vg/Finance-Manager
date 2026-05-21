from tests.unit.helpers import assert_module_has_symbol


def test_user_input_port_module_exposes_protocol() -> None:
    assert_module_has_symbol(
        "src.core.ports.input.user_input_port",
        "UserInputPort",
    )
