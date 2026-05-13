from fastapi import APIRouter

from routes.visits.service import VisitsCounterDep

from .models import APIInfoResponse
from .service import RootServiceDep

root_router = APIRouter(prefix="")


@root_router.get("/")
async def get_api_info(
    service: RootServiceDep, counter: VisitsCounterDep
) -> APIInfoResponse:
    """Get API information and increment visit counter."""
    counter.increment()
    return await service.get_api_info()
