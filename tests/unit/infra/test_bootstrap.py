from src.core.use_cases.healthz_use_case import HealthzUseCase
from src.infra.bootstrap import (
    ApplicationContainer,
    build_application_container,
)
from src.infra.settings.models import Settings


def test_build_application_container_returns_loaded_dependencies():
    container = build_application_container()

    assert isinstance(container, ApplicationContainer)
    assert isinstance(container.settings, Settings)
    assert isinstance(container.healthz_input_port, HealthzUseCase)
