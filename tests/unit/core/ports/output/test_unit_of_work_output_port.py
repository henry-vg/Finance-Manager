from tests.unit.helpers import assert_module_has_symbol


def test_unit_of_work_output_port_module_exposes_protocols() -> None:
    assert_module_has_symbol(
        "src.core.ports.output.unit_of_work_output_port",
        "UnitOfWorkOutputPort",
    )
    assert_module_has_symbol(
        "src.core.ports.output.unit_of_work_output_port",
        "UnitOfWorkOutputPortFactory",
    )
