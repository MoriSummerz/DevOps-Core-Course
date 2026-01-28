from fastapi import Depends
from fastapi import FastAPI, Request
from typing import Annotated


def get_app_instance(request: Request) -> FastAPI:
    return request.app


AppInstanceDep = Annotated[
    FastAPI,
    Depends(get_app_instance),
]
