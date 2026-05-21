import pytest

from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)


def test_healthz_status_exposes_all_public_members() -> None:
    assert tuple(HealthzStatus.__members__) == ("OK", "NOT_OK")


@pytest.mark.parametrize("status", [HealthzStatus.OK, HealthzStatus.NOT_OK])
def test_healthz_liveness_keeps_status(status: HealthzStatus) -> None:
    liveness = HealthzLiveness(status=status)

    assert liveness.status == status


def test_healthz_readiness_dependencies_keep_api_and_database_status() -> None:
    dependencies = HealthzReadinessDependencies(
        api=HealthzStatus.OK,
        database=HealthzStatus.NOT_OK,
    )

    assert dependencies.api == HealthzStatus.OK
    assert dependencies.database == HealthzStatus.NOT_OK


def test_healthz_readiness_keeps_nested_dependency_statuses() -> None:
    readiness = HealthzReadiness(
        status=HealthzStatus.OK,
        dependencies=HealthzReadinessDependencies(
            api=HealthzStatus.OK,
            database=HealthzStatus.NOT_OK,
        ),
    )

    assert readiness.dependencies.database == HealthzStatus.NOT_OK
    assert readiness.status == HealthzStatus.OK
