from fastapi import HTTPException, FastAPI


async def handle_404_exception(_, __):
    raise HTTPException(status_code=404, detail="Not found")


async def handle_500_exception(_, exc: Exception):
    raise HTTPException(status_code=500, detail=f"Something went wrong: {exc}")


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(404, handle_404_exception)
    app.add_exception_handler(500, handle_500_exception)
