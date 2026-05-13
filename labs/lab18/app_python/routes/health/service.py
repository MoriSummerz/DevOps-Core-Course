import time
from typing import Annotated

from fastapi import Depends

from dependencies import AppInstanceDep

from .models import HealthCheckResponse


class HealthService:
    def __init__(self, app: AppInstanceDep):
        self.app = app

    async def get_health_check(self) -> HealthCheckResponse:
        return HealthCheckResponse(
            uptime_seconds=int(time.time() - self.app.state.startup_time),
        )


HealthServiceDep = Annotated[
    HealthService,
    Depends(HealthService),
]
