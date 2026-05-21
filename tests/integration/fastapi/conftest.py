import pytest

from tests.integration.fastapi.stubs import (
    CurrencyInputPortStub,
    InMemoryLedgerAccountInputPortStub,
    InMemoryTagInputPortStub,
    InMemoryUserInputPortStub,
)


@pytest.fixture
def currency_input_port_stub() -> CurrencyInputPortStub:
    return CurrencyInputPortStub()


@pytest.fixture
def ledger_account_input_port_stub() -> InMemoryLedgerAccountInputPortStub:
    return InMemoryLedgerAccountInputPortStub()


@pytest.fixture
def tag_input_port_stub() -> InMemoryTagInputPortStub:
    return InMemoryTagInputPortStub()


@pytest.fixture
def user_input_port_stub() -> InMemoryUserInputPortStub:
    return InMemoryUserInputPortStub()
