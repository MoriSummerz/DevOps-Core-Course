from pydantic import BaseModel


class VisitsResponse(BaseModel):
    visits: int
