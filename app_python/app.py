from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from config import settings
from lifespan import lifespan
from log_config import setup_json_logging
from middleware import RequestLoggingMiddleware
from routes import health_router, root_router

setup_json_logging()

app = FastAPI(
    title="devops-info-service",
    version="1.0.0",
    description="DevOps course info service",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

for router in [root_router, health_router]:
    app.include_router(router)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app", host=settings.host, port=settings.port, reload=settings.debug
    )
