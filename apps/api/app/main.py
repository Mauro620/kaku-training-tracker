"""Punto de entrada de la API."""

from fastapi import APIRouter, FastAPI

from app.api.v1.routers import auth, health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    v1 = APIRouter(prefix=settings.api_v1_prefix)
    v1.include_router(health.router)
    v1.include_router(auth.router)
    app.include_router(v1)

    return app


app = create_app()
