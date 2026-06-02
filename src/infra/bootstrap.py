from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.ports.input.currency_input_port import CurrencyInputPort
from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.transaction_input_port import TransactionInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.ports.output.exchange_rate_output_port import ExchangeRateOutputPort
from src.core.usecases.currency_usecase import CurrencyUseCase
from src.core.usecases.healthz_usecase import HealthzUseCase
from src.core.usecases.ledger_account_usecase import LedgerAccountUseCase
from src.core.usecases.tag_usecase import TagUseCase
from src.core.usecases.transaction_usecase import TransactionUseCase
from src.core.usecases.user_usecase import UserUseCase
from src.infra.exchange_rate import MockExchangeRateOutputAdapter
from src.infra.postgres import (
    SQLAlchemyPostgresHealthAdapter,
    SQLAlchemyPostgresUnitOfWorkFactory,
    create_postgres_engine,
    create_postgres_session_factory,
)
from src.infra.security import ScryptPasswordHasher
from src.infra.settings import Settings, load_settings


@dataclass(frozen=True)
class ApplicationContainer:
    settings: Settings
    postgres_engine: AsyncEngine
    postgres_session_factory: async_sessionmaker[AsyncSession]
    postgres_health_output_port: DatabaseHealthOutputPort
    exchange_rate_output_port: ExchangeRateOutputPort
    healthz_input_port: HealthzInputPort
    currency_input_port: CurrencyInputPort
    ledger_account_input_port: LedgerAccountInputPort
    tag_input_port: TagInputPort
    transaction_input_port: TransactionInputPort
    user_input_port: UserInputPort


def build_application_container() -> ApplicationContainer:
    settings = load_settings()
    postgres_engine = create_postgres_engine(settings.postgres)
    postgres_session_factory = create_postgres_session_factory(postgres_engine)
    postgres_health_output_port = SQLAlchemyPostgresHealthAdapter(postgres_engine)
    exchange_rate_output_port = MockExchangeRateOutputAdapter()
    unit_of_work_output_port_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )
    password_hasher_output_port = ScryptPasswordHasher()

    return ApplicationContainer(
        settings=settings,
        postgres_engine=postgres_engine,
        postgres_session_factory=postgres_session_factory,
        postgres_health_output_port=postgres_health_output_port,
        exchange_rate_output_port=exchange_rate_output_port,
        healthz_input_port=HealthzUseCase(
            database_health_output_port=postgres_health_output_port,
        ),
        currency_input_port=CurrencyUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        ledger_account_input_port=LedgerAccountUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        tag_input_port=TagUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        transaction_input_port=TransactionUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
            exchange_rate_output_port=exchange_rate_output_port,
        ),
        user_input_port=UserUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
            password_hasher_output_port=password_hasher_output_port,
        ),
    )
