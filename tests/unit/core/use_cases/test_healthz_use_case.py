from src.core.domain.healthz import HealthzStatus
from src.core.use_cases.healthz_use_case import HealthzUseCase


def test_healthz_use_case_execute_returns_healthy():
    use_case = HealthzUseCase()
    result = use_case.get_healthz_liveness()

    assert result.status == HealthzStatus.OK


def test_healthz_use_case_readiness_returns_ok_with_api_server_dependency():
    use_case = HealthzUseCase()

    result = use_case.get_healthz_readiness()

    assert result.status == HealthzStatus.OK
    assert result.dependencies.api_server == HealthzStatus.OK
