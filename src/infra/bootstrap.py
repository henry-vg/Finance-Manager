from dataclasses import dataclass

from src.core.ports.input.healthz_input_port import HealthzInputPort
from src.core.use_cases.healthz_use_case import HealthzUseCase
from src.infra.settings import (
    Settings,
    load_settings,
)


@dataclass(frozen=True)
class ApplicationContainer:
    settings: Settings
    healthz_input_port: HealthzInputPort


def build_application_container() -> ApplicationContainer:

    return ApplicationContainer(
        settings=load_settings(),
        healthz_input_port=HealthzUseCase(),
    )
