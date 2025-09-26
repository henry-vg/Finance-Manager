from src.core.domain.health import (
    Health,
    Status,
)


class HealthUseCase:
    def __init__(self):
        pass

    def execute(self) -> Health:
        return Health(
            status=Status.HEALTHY,
        )
