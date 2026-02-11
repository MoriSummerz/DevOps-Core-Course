from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uptime_seconds: int
