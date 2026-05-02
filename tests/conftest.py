import pytest

from src.core.domain.healthz import HealthzStatus
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.use_cases.healthz_use_case import HealthzUseCase
from src.infra.fastapi.app import create_http_app
from src.infra.settings import load_settings


class _HealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.OK


@pytest.fixture()
def app():
    healthy_database_health_output_port_stub = _HealthyDatabaseHealthOutputPortStub()
    return create_http_app(
        settings=load_settings(),
        healthz_input_port=HealthzUseCase(healthy_database_health_output_port_stub),
    )
