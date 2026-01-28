from fastapi import APIRouter
from .models import APIInfoResponse
from .service import RootServiceDep

root_router = APIRouter(prefix="")


@root_router.get("/")
async def get_api_info(service: RootServiceDep) -> APIInfoResponse:
    """Get API information"""
    return await service.get_api_info()
