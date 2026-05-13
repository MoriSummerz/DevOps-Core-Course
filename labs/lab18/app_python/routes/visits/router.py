from fastapi import APIRouter

from .models import VisitsResponse
from .service import VisitsCounterDep

visits_router = APIRouter(prefix="/visits")


@visits_router.get("/")
async def get_visits(counter: VisitsCounterDep) -> VisitsResponse:
    """Return the current visit count."""
    return VisitsResponse(visits=counter.get())
