from fastapi import FastAPI
from config import settings
from routes import root_router, health_router
import logging
from lifespan import lifespan

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="devops-info-service",
    version="1.0.0",
    description="DevOps course info service",
    debug=settings.debug,
    lifespan=lifespan,
)
for router in [root_router, health_router]:
    app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app", host=settings.host, port=settings.port, reload=settings.debug
    )
