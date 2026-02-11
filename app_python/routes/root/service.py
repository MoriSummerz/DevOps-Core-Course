import os
import platform
import socket
import time
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.routing import APIRoute

from dependencies import AppInstanceDep

from .models import (
    APIInfoResponse,
    Endpoint,
    RequestInfo,
    RuntimeInfo,
    ServiceInfo,
    SystemInfo,
)


class RootService:
    def __init__(self, app: AppInstanceDep, request: Request):
        self.app = app
        self.request = request

    async def _get_service_info(self) -> ServiceInfo:
        return ServiceInfo(
            name=self.app.title,
            version=self.app.version,
            description=self.app.description,
        )

    @staticmethod
    async def _get_system_info() -> SystemInfo:
        return SystemInfo(
            hostname=socket.gethostname(),
            platform=platform.system(),
            platform_version=platform.version(),
            architecture=platform.machine(),
            cpu_count=os.cpu_count() or 1,
            python_version=platform.python_version(),
        )

    async def _get_runtime_info(self) -> RuntimeInfo:
        uptime_seconds = int(time.time() - self.app.state.startup_time)
        return RuntimeInfo(
            uptime_seconds=uptime_seconds,
            uptime_human=f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
            current_time=datetime.now(UTC),
            timezone=str(datetime.now().astimezone().tzinfo),
        )

    async def _get_request_info(self) -> RequestInfo:
        return RequestInfo(
            client_ip=self.request.client.host,
            user_agent=self.request.headers.get("user-agent"),
            method=self.request.method,
            path=self.request.url.path,
        )

    async def _get_endoints_info(self) -> list[Endpoint]:
        endpoints = []
        for route in self.app.routes:
            if isinstance(route, APIRoute):
                for method in route.methods:
                    endpoints.append(
                        Endpoint(
                            path=route.path,
                            method=method,
                            description=route.description,
                        )
                    )
        return endpoints

    async def get_api_info(self) -> APIInfoResponse:
        return APIInfoResponse(
            service=await self._get_service_info(),
            system=await self._get_system_info(),
            runtime=await self._get_runtime_info(),
            request=await self._get_request_info(),
            endpoints=await self._get_endoints_info(),
        )


RootServiceDep = Annotated[
    RootService,
    Depends(RootService),
]
