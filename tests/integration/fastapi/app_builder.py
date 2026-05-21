from fastapi import FastAPI

from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.infra.fastapi.app import create_http_app
from src.infra.settings import Settings, load_settings
from tests.integration.fastapi.stubs import (
    CurrencyInputPortStub,
    LedgerAccountInputPortStub,
    ReadyHealthzInputPortStub,
    TagInputPortStub,
    UserInputPortStub,
)


def create_default_test_app(
    *,
    settings: Settings | None = None,
    healthz_input_port: HealthzInputPort | None = None,
    currency_input_port: CurrencyInputPort | None = None,
    ledger_account_input_port: LedgerAccountInputPort | None = None,
    tag_input_port: TagInputPort | None = None,
    user_input_port: UserInputPort | None = None,
) -> FastAPI:
    return create_http_app(
        settings=settings or load_settings(),
        healthz_input_port=healthz_input_port or ReadyHealthzInputPortStub(),
        currency_input_port=currency_input_port or CurrencyInputPortStub(),
        ledger_account_input_port=(
            ledger_account_input_port or LedgerAccountInputPortStub()
        ),
        tag_input_port=tag_input_port or TagInputPortStub(),
        user_input_port=user_input_port or UserInputPortStub(),
    )
