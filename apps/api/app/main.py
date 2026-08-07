"""Punto de entrada de la API."""

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routers import (
    alimentos_router,
    auth_router,
    bienestar_router,
    catalogos_router,
    ciclos_router,
    comidas_router,
    despensa_router,
    entrenamiento_router,
    habitos_router,
    health_router,
    hidratacion_router,
    molestias_router,
    parametros_router,
    planes_router,
    recetas_router,
    sueno_router,
)
from app.core.config import get_settings
from app.core.exceptions import InvarianteDeNegocioError, RecursoNoEncontradoError

# Excepción de dominio -> status HTTP. Único lugar del proyecto que traduce
# entre las dos: los servicios nunca importan HTTPException (AGENTS.md §5).
_STATUS_POR_EXCEPCION = {
    InvarianteDeNegocioError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RecursoNoEncontradoError: status.HTTP_404_NOT_FOUND,
}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    # allow_credentials=False: la auth va por Bearer token, no cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_lista,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for excepcion, codigo in _STATUS_POR_EXCEPCION.items():

        @app.exception_handler(excepcion)
        async def _manejar_error_de_dominio(
            _request: Request, exc: Exception, codigo: int = codigo
        ) -> JSONResponse:
            return JSONResponse(status_code=codigo, content={"detail": str(exc)})

    v1 = APIRouter(prefix=settings.api_v1_prefix)
    v1.include_router(health_router)
    v1.include_router(auth_router)
    v1.include_router(sueno_router)
    v1.include_router(bienestar_router)
    v1.include_router(molestias_router)
    v1.include_router(habitos_router)
    v1.include_router(hidratacion_router)
    v1.include_router(parametros_router)
    v1.include_router(entrenamiento_router)
    v1.include_router(catalogos_router)
    v1.include_router(ciclos_router)
    v1.include_router(planes_router)
    v1.include_router(alimentos_router)
    v1.include_router(recetas_router)
    v1.include_router(comidas_router)
    v1.include_router(despensa_router)
    app.include_router(v1)

    return app


app = create_app()
