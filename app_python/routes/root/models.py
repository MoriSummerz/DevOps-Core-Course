from datetime import datetime

from pydantic import BaseModel
from typing import Literal


class ServiceInfo(BaseModel):
    name: str
    version: str
    description: str
    framework: Literal["FastAPI"] = "FastAPI"


class SystemInfo(BaseModel):
    hostname: str
    platform: str
    platform_version: str
    architecture: str
    cpu_count: int
    python_version: str


class RuntimeInfo(BaseModel):
    uptime_seconds: int
    uptime_human: str
    current_time: datetime
    timezone: str


class RequestInfo(BaseModel):
    client_ip: str
    user_agent: str
    method: str
    path: str


class Endpoint(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    description: str


class APIInfoResponse(BaseModel):
    service: ServiceInfo
    system: SystemInfo
    runtime: RuntimeInfo
    request: RequestInfo
    endpoints: list[Endpoint]
