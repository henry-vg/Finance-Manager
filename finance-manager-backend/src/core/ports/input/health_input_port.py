from typing import Protocol
from src.core.domain.health import Health

class HealthInputPort(Protocol):
    def get_health(self) -> Health: ...
