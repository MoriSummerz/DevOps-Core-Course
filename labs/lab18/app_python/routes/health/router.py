from fastapi import APIRouter

from .models import HealthCheckResponse
from .service import HealthServiceDep

health_router = APIRouter(prefix="/health")


@health_router.get("/")
async def health_check(service: HealthServiceDep) -> HealthCheckResponse:
    """Health check endpoint"""
    return await service.get_health_check()
