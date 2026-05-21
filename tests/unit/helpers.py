import importlib
import inspect


def assert_module_has_symbol(
    module_name: str,
    symbol_name: str,
) -> None:
    module = importlib.import_module(module_name)
    symbol = getattr(module, symbol_name)
    public_members = {
        name
        for name, member in symbol.__dict__.items()
        if not name.startswith("_") and not inspect.ismodule(member)
    }
    has_explicit_contract = bool(public_members or "__call__" in symbol.__dict__)

    assert module.__name__ == module_name
    assert inspect.isclass(symbol)
    assert symbol.__module__ == module_name
    assert symbol.__name__ == symbol_name
    assert has_explicit_contract

    if symbol_name.endswith("Port") or symbol_name.endswith("PortFactory"):
        assert getattr(symbol, "_is_protocol", False)
