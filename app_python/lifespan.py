import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the application...")
    app.state.startup_time = time.time()
    register_exception_handlers(app)
    yield
    logger.info("Shutting down the application...")
