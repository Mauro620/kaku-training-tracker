"""Reglas de negocio del perfil del atleta."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError, RecursoNoEncontradoError
from app.models import PerfilAtleta
from app.repositories.catalogo import perfil as repo
from app.repositories.catalogo import tipo_sesion as repo_tipo_sesion
from app.schemas.catalogo.perfil import PerfilUpdate

_LISTAS = {
    "lesiones_activas",
    "objetivos",
    "eventos_fijos",
    "ventanas",
    "lugares",
    "equipamiento_propio",
}


async def obtener_perfil(session: AsyncSession, usuario_id: uuid.UUID) -> PerfilAtleta:
    perfil = await repo.obtener(session, usuario_id)
    if perfil is None:
        raise RecursoNoEncontradoError("el perfil del atleta no existe todavia")
    return perfil


async def guardar_perfil(
    session: AsyncSession, usuario_id: uuid.UUID, payload: PerfilUpdate
) -> PerfilAtleta:
    # Los tipos de sesion son un catalogo cerrado (PLAN_IMPORT.md §2.3): un
    # evento fijo con un tipo que no existe no se podria cruzar con el plan.
    validos = {t.codigo for t in await repo_tipo_sesion.listar(session)}
    desconocidos = sorted({e.tipo_sesion for e in payload.eventos_fijos} - validos)
    if desconocidos:
        raise InvarianteDeNegocioError(
            "tipo de sesion desconocido en eventos_fijos: "
            + ", ".join(desconocidos)
            + ". Validos: "
            + ", ".join(sorted(validos))
        )

    # mode="json": Decimal queda como numero JSON dentro del JSONB; las
    # columnas escalares se pasan tal cual.
    escalares: dict[str, Any] = payload.model_dump(
        exclude={
            "lesiones_activas",
            "objetivos",
            "eventos_fijos",
            "ventanas",
            "lugares",
        }
    )
    listas: dict[str, Any] = payload.model_dump(
        mode="json",
        include={
            "lesiones_activas",
            "objetivos",
            "eventos_fijos",
            "ventanas",
            "lugares",
        },
    )
    perfil = await repo.upsert(session, usuario_id, {**escalares, **listas})
    await session.commit()
    return perfil
