from dependencies import AppInstanceDep

from .models import HealthCheckResponse
import time
from fastapi import Depends
from typing import Annotated


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
