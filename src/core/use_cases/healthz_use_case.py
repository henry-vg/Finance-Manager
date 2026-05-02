from src.core.domain.healthz import (
    HealthzLiveness,
    HealthzReadiness,
    HealthzReadinessDependencies,
    HealthzStatus,
)
from src.core.ports.input.healthz_input_port import HealthzInputPort


class HealthzUseCase(HealthzInputPort):
    def get_healthz_liveness(
        self,
    ) -> HealthzLiveness:
        return HealthzLiveness(
            status=HealthzStatus.OK,
        )

    def get_healthz_readiness(
        self,
    ) -> HealthzReadiness:
        api_server_status = self._get_api_server_status()

        status = (
            HealthzStatus.OK
            if all(
                dependency == HealthzStatus.OK
                for dependency in [
                    api_server_status,
                ]
            )
            else HealthzStatus.NOT_OK
        )

        return HealthzReadiness(
            status=status,
            dependencies=HealthzReadinessDependencies(
                api_server=api_server_status,
            ),
        )

    def _get_api_server_status(
        self,
    ) -> HealthzStatus:
        return HealthzStatus.OK
