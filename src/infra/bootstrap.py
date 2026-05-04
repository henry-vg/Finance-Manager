from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.ports.input.user_input_port import UserInputPort
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.usecases.healthz_usecase import HealthzUseCase
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
        user_input_port=UserUseCase(
            unit_of_work_output_port_factory=unit_of_work_output_port_factory,
            password_hasher_output_port=password_hasher_output_port,
        ),
    )
