from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.ledger_account_input_port import LedgerAccountInputPort
from src.core.ports.input.statement_cycle_input_port import StatementCycleInputPort
from src.core.ports.input.tag_input_port import TagInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.usecases.healthz_usecase import HealthzUseCase
from src.core.usecases.ledger_account_usecase import LedgerAccountUseCase
from src.core.usecases.statement_cycle_usecase import StatementCycleUseCase
from src.core.usecases.tag_usecase import TagUseCase
from src.core.usecases.user_usecase import UserUseCase
from src.infra.postgres import (
    SQLAlchemyPostgresHealthAdapter,
    SQLAlchemyPostgresUnitOfWorkFactory,
    create_postgres_engine,
    create_postgres_session_factory,
)
from src.infra.security import ScryptPasswordHasher
from src.infra.settings import (
    Settings,
    load_settings,
)


@dataclass(frozen=True)
class ApplicationContainer:
    settings: Settings
    postgres_engine: AsyncEngine
    postgres_session_factory: async_sessionmaker[AsyncSession]
    postgres_health_output_port: DatabaseHealthOutputPort
    healthz_input_port: HealthzInputPort
    ledger_account_input_port: LedgerAccountInputPort
    statement_cycle_input_port: StatementCycleInputPort
    tag_input_port: TagInputPort
    user_input_port: UserInputPort


def build_application_container() -> ApplicationContainer:
    settings = load_settings()
    postgres_engine = create_postgres_engine(settings.postgres)
    postgres_session_factory = create_postgres_session_factory(postgres_engine)
    postgres_health_output_port = SQLAlchemyPostgresHealthAdapter(postgres_engine)
    unit_of_work_output_port_factory = SQLAlchemyPostgresUnitOfWorkFactory(
        postgres_session_factory,
    )
    password_hasher_output_port = ScryptPasswordHasher()

    return ApplicationContainer(
        settings=settings,
        postgres_engine=postgres_engine,
        postgres_session_factory=postgres_session_factory,
        postgres_health_output_port=postgres_health_output_port,
        healthz_input_port=HealthzUseCase(
            database_health_output_port=postgres_health_output_port,
        ),
        ledger_account_input_port=LedgerAccountUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        statement_cycle_input_port=StatementCycleUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        tag_input_port=TagUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
        ),
        user_input_port=UserUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
            password_hasher_output_port=password_hasher_output_port,
        ),
    )
