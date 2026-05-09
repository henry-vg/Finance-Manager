import pytest

from src.core.domain.healthz import HealthzStatus
from src.core.ports.output.database_health_output_port import DatabaseHealthOutputPort
from src.core.usecases.healthz_usecase import HealthzUseCase


class _HealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.OK


class _UnhealthyDatabaseHealthOutputPortStub(DatabaseHealthOutputPort):
    async def get_database_status(self) -> HealthzStatus:
        return HealthzStatus.NOT_OK


def test_healthz_status_is_domain_owned_and_not_http_text() -> None:
    assert isinstance(HealthzStatus.OK.value, int)
    assert isinstance(HealthzStatus.NOT_OK.value, int)


@pytest.mark.anyio
async def test_healthz_usecase_execute_returns_healthy():
    use_case = HealthzUseCase(
        database_health_output_port=_HealthyDatabaseHealthOutputPortStub(),
    )
    result = await use_case.get_healthz_liveness()

    assert result.status == HealthzStatus.OK


@pytest.mark.anyio
async def test_healthz_usecase_readiness_returns_ok_with_api_server_dependency():
    use_case = HealthzUseCase(
        database_health_output_port=_HealthyDatabaseHealthOutputPortStub(),
    )

    result = await use_case.get_healthz_readiness()

    assert result.status == HealthzStatus.OK
    assert result.dependencies.api == HealthzStatus.OK
    assert result.dependencies.database == HealthzStatus.OK


@pytest.mark.anyio
async def test_healthz_usecase_readiness_returns_not_ok_when_database_is_unhealthy():
    use_case = HealthzUseCase(
        database_health_output_port=_UnhealthyDatabaseHealthOutputPortStub(),
    )

    result = await use_case.get_healthz_readiness()

    assert result.status == HealthzStatus.NOT_OK
    assert result.dependencies.api == HealthzStatus.OK
    assert result.dependencies.database == HealthzStatus.NOT_OK
