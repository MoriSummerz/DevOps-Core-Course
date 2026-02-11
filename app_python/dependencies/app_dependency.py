from typing import Annotated

from fastapi import Depends, FastAPI, Request


def get_app_instance(request: Request) -> FastAPI:
    return request.app


AppInstanceDep = Annotated[
    FastAPI,
    Depends(get_app_instance),
]
