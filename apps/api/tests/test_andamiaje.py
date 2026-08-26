"""Tests del andamiaje de la API: el manejador central de excepciones traduce
cada `DomainError` al codigo HTTP que corresponde."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    ConflictoDeNegocioError,
    InvarianteDeNegocioError,
    RecursoNoEncontradoError,
)
from app.main import app


@pytest.fixture
async def cliente_con_ruta_de_test() -> AsyncGenerator[AsyncClient, None]:
    """Levanta un cliente con un endpoint efimero que dispara cada
    `DomainError` que nos interesa. La ruta se registra al inicio y se
    desregistra al final para no contaminar el resto de la suite."""

    from fastapi import Request
    from fastapi.responses import JSONResponse

    async def _levantar_conflicto(_: Request) -> JSONResponse:
        raise ConflictoDeNegocioError("duplicado")

    async def _levantar_invariante(_: Request) -> JSONResponse:
        raise InvarianteDeNegocioError("invalido")

    async def _levantar_no_encontrado(_: Request) -> JSONResponse:
        raise RecursoNoEncontradoError("ausente")

    app.add_api_route("/_test/conflicto", _levantar_conflicto, methods=["GET"])
    app.add_api_route("/_test/invariante", _levantar_invariante, methods=["GET"])
    app.add_api_route("/_test/no-encontrado", _levantar_no_encontrado, methods=["GET"])

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        # `app.router` no expone remove() estable, pero las rutas viven en
        # `app.routes`; las quitamos por referencia. Solo afecta al proceso
        # de tests, no al modulo importado.
        app.routes[:] = [
            r
            for r in app.routes
            if getattr(r, "path", "")
            not in {
                "/_test/conflicto",
                "/_test/invariante",
                "/_test/no-encontrado",
            }
        ]


async def test_conflicto_de_negocio_se_traduce_a_409(
    cliente_con_ruta_de_test: AsyncClient,
) -> None:
    respuesta = await cliente_con_ruta_de_test.get("/_test/conflicto")
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "duplicado"}


async def test_invariante_de_negocio_se_traduce_a_422(
    cliente_con_ruta_de_test: AsyncClient,
) -> None:
    respuesta = await cliente_con_ruta_de_test.get("/_test/invariante")
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "invalido"}


async def test_recurso_no_encontrado_se_traduce_a_404(
    cliente_con_ruta_de_test: AsyncClient,
) -> None:
    respuesta = await cliente_con_ruta_de_test.get("/_test/no-encontrado")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "ausente"}


def test_conflicto_de_negocio_es_una_invariante() -> None:
    """Para que el servicio que levante 409 pueda atraparlo con
    `except InvarianteDeNegocioError` si quiere tratar a todos los
    `DomainError` por igual (mismo origen conceptual)."""
    assert issubclass(ConflictoDeNegocioError, InvarianteDeNegocioError)
