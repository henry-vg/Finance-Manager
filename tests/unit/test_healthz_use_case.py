from src.core.domain.healthz import HealthzStatus
from src.core.use_cases.healthz_use_case import HealthzUseCase


def test_healthz_use_case_execute_returns_healthy():
    use_case = HealthzUseCase()
    result = use_case.get_healthz_liveness()

    assert result.status == HealthzStatus.OK
