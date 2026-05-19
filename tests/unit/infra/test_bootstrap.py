from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.usecases.healthz_usecase import HealthzUseCase
from src.core.usecases.ledger_account_usecase import LedgerAccountUseCase
from src.core.usecases.tag_usecase import TagUseCase
from src.core.usecases.transaction_usecase import TransactionUseCase
from src.core.usecases.user_usecase import UserUseCase
from src.infra.bootstrap import (
    ApplicationContainer,
    build_application_container,
)
from src.infra.postgres.health import SQLAlchemyPostgresHealthAdapter
from src.infra.settings.models import Settings


def test_build_application_container_returns_loaded_dependencies():
    container = build_application_container()

    assert isinstance(container, ApplicationContainer)
    assert isinstance(container.settings, Settings)
    assert isinstance(container.postgres_engine, AsyncEngine)
    assert isinstance(container.postgres_session_factory, async_sessionmaker)
    assert container.postgres_session_factory.class_ is AsyncSession
    assert isinstance(
        container.postgres_health_output_port,
        SQLAlchemyPostgresHealthAdapter,
    )
    assert isinstance(container.healthz_input_port, HealthzUseCase)
    assert isinstance(container.ledger_account_input_port, LedgerAccountUseCase)
    assert isinstance(container.tag_input_port, TagUseCase)
    assert isinstance(container.transaction_input_port, TransactionUseCase)
    assert isinstance(container.user_input_port, UserUseCase)
