"""Reglas de negocio de habito y habito_registro."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Habito, HabitoRegistro
from app.repositories.bienestar import habito as repo
from app.schemas.bienestar.habito import HabitoRegistroCreate


async def listar_habitos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    return await repo.listar_activos(session, usuario_id)


async def registrar(
    session: AsyncSession, usuario_id: uuid.UUID, payload: HabitoRegistroCreate
) -> HabitoRegistro:
    # El hábito tiene que existir Y pertenecer al usuario: sin este chequeo,
    # cualquiera podría marcar el hábito de otro usuario por id.
    habito = await repo.obtener_habito(session, usuario_id, payload.habito_id)
    if habito is None:
        raise RecursoNoEncontradoError(f"hábito {payload.habito_id} no encontrado")

    registro = await repo.upsert_registro(
        session,
        payload.habito_id,
        payload.fecha,
        payload.valor,
        idempotency_key=payload.idempotency_key,
    )
    await session.commit()
    return registro


async def listar_registros_de_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[HabitoRegistro]:
    return await repo.listar_registros_por_fecha(session, usuario_id, fecha)


# D1-D4 de la revision de UI: CRUD de habitos para la pantalla Ajustes.
# Archivado es `activo = false`, NUNCA DELETE (D3): borrar un habito
# deja huerfanas las filas de habito_registro y destruye el historico.


async def listar_todos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    return await repo.listar_todos(session, usuario_id)


async def crear_habito(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    nombre: str,
    orden: int,
) -> Habito:
    """Crea un habito. Como no hay DELETE, el nombre debe ser unico
    por usuario (la DB tiene UNIQUE (usuario_id, nombre))."""
    from sqlalchemy.exc import IntegrityError

    from app.core.exceptions import InvarianteDeNegocioError

    if not nombre.strip():
        raise InvarianteDeNegocioError("el nombre no puede estar vacio")
    try:
        habito = await repo.crear(
            session, usuario_id, nombre=nombre.strip(), orden=orden
        )
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise InvarianteDeNegocioError(
            f"ya existe un habito con nombre '{nombre.strip()}'"
        ) from e
    return habito


async def actualizar_habito(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    habito_id: int,
    *,
    nombre: str | None,
    activo: bool | None,
    orden: int | None,
) -> Habito:
    habito = await repo.obtener_habito(session, usuario_id, habito_id)
    if habito is None:
        from app.core.exceptions import RecursoNoEncontradoError

        raise RecursoNoEncontradoError(f"habito {habito_id} no encontrado")
    await repo.actualizar(session, habito, nombre=nombre, activo=activo, orden=orden)
    await session.commit()
    return habito


async def reordenar_habitos(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    ids_en_orden: list[int],
) -> None:
    """Aplica el orden nuevo a todos los habitos del usuario que
    esten en la lista. Los que no esten quedan donde estaban."""
    habitos = await repo.listar_todos(session, usuario_id)
    por_id = {h.id: h for h in habitos}
    for idx, h_id in enumerate(ids_en_orden):
        habito = por_id.get(h_id)
        if habito is None:
            # ids que no pertenecen al usuario: los ignoramos (no es
            # un error del cliente, es un id ajeno).
            continue
        await repo.actualizar(session, habito, orden=idx)
    await session.commit()
