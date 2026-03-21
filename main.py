from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.routes import router
from core.config_loader import get_settings
from core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(log_level=settings.log_level, logs_dir=settings.logs_dir)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AtlasKernel — intelligent prompt router and executor.",
        lifespan=lifespan,
    )

    app.include_router(router, prefix="/v1")

    return app


app = create_app()
