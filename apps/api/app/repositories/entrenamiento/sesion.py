"""Persistencia de sesion. Sin reglas de negocio.

El `idempotency_key` es unique en la tabla (docs/schema.dbml): si el cliente
reintenta el mismo POST, el INSERT colisiona. Aqui manejamos la colision
con `on_conflict_do_nothing` + un SELECT posterior: si el key ya existia,
devolvemos la sesion que ya estaba. Asi Fase 5 puede reintentar sin miedo.
"""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Sesion


async def crear(
    session: AsyncSession,
    *,
    sesion_id: uuid.UUID | None,
    idempotency_key: uuid.UUID,
    usuario_id: uuid.UUID,
    sesion_plan_id: int | None,
    fecha: date,
    tipo_sesion_id: int,
    duracion_min: int,
    rpe: int,
    nota: str | None,
) -> Sesion:
    """Inserta idempotente por `idempotency_key`. Si ya existe, devuelve la
    fila existente. `carga_srpe` lo calcula Postgres (columna generada)."""
    valores: dict[str, object] = {
        "id": sesion_id,
        "idempotency_key": idempotency_key,
        "usuario_id": usuario_id,
        "sesion_plan_id": sesion_plan_id,
        "fecha": fecha,
        "tipo_sesion_id": tipo_sesion_id,
        "duracion_min": duracion_min,
        "rpe": rpe,
        "nota": nota,
    }
    stmt = (
        pg_insert(Sesion)
        .values(**valores)
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(Sesion)
    )
    creada = await session.scalar(stmt)
    if creada is not None:
        return creada

    # Ya existia: la devolvemos.
    existente = await session.scalar(
        select(Sesion).where(Sesion.idempotency_key == idempotency_key)
    )
    if existente is None:
        # No deberia pasar: o la creamos o existia.
        raise RuntimeError("sesion no encontrada despues de on_conflict_do_nothing")
    return existente


async def obtener_por_id(session: AsyncSession, sesion_id: uuid.UUID) -> Sesion | None:
    return cast(
        "Sesion | None",
        await session.scalar(
            select(Sesion)
            .where(Sesion.id == sesion_id)
            .options(selectinload(Sesion.bloques))
        ),
    )


async def actualizar(
    session: AsyncSession,
    sesion: Sesion,
    *,
    fecha: date,
    tipo_sesion_id: int,
    duracion_min: int,
    rpe: int,
    nota: str | None,
) -> Sesion:
    sesion.fecha = fecha
    sesion.tipo_sesion_id = tipo_sesion_id
    sesion.duracion_min = duracion_min
    sesion.rpe = rpe
    sesion.nota = nota
    await session.flush()
    return sesion


async def eliminar(session: AsyncSession, sesion: Sesion) -> None:
    # Los bloques se van solos: FK ondelete=CASCADE (REGLAS_NEGOCIO §15).
    await session.delete(sesion)
    await session.flush()


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[Sesion]:
    """`selectinload` evita N+1: SesionRead siempre incluye `bloques`, así
    que cualquier consumidor de esta función los necesita cargados."""
    resultado = await session.scalars(
        select(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.fecha == fecha)
        .options(selectinload(Sesion.bloques))
        .order_by(Sesion.registrado_en)
    )
    return list(resultado.all())


async def contar_por_tipo_en_rango(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    tipo_sesion_id: int,
    desde: date,
    hasta: date,
) -> int:
    """Cuenta sesiones reales de un tipo dentro de un rango de fechas
    (inclusive). Usado para el cumplimiento por composición semanal."""
    return (
        await session.scalar(
            select(func.count())
            .select_from(Sesion)
            .where(
                Sesion.usuario_id == usuario_id,
                Sesion.tipo_sesion_id == tipo_sesion_id,
                Sesion.fecha >= desde,
                Sesion.fecha <= hasta,
            )
        )
    ) or 0


async def listar_fechas_por_tipo_en_rango(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    tipo_sesion_id: int,
    desde: date,
    hasta: date,
) -> list[date]:
    """Fechas de sesiones reales de un tipo dentro de un rango (inclusive).
    Usado para validar el espaciado entre sesiones del mismo tipo (ej.
    fuerza) o la ventana previa a un partido, al sugerir un día nuevo."""
    resultado = await session.scalars(
        select(Sesion.fecha)
        .where(
            Sesion.usuario_id == usuario_id,
            Sesion.tipo_sesion_id == tipo_sesion_id,
            Sesion.fecha >= desde,
            Sesion.fecha <= hasta,
        )
        .order_by(Sesion.fecha)
    )
    return list(resultado.all())


async def listar_fechas_de_demanda_en_rango(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    tipo_sesion_ids: list[int],
    desde: date,
    hasta: date,
) -> list[date]:
    """Fechas de sesiones reales de cualquiera de los tipos dados (usado con
    los tipos de demanda alta) dentro de un rango. Para la regla de la
    ventana previa a un partido."""
    if not tipo_sesion_ids:
        return []
    resultado = await session.scalars(
        select(Sesion.fecha)
        .where(
            Sesion.usuario_id == usuario_id,
            Sesion.tipo_sesion_id.in_(tipo_sesion_ids),
            Sesion.fecha >= desde,
            Sesion.fecha <= hasta,
        )
        .order_by(Sesion.fecha)
    )
    return list(resultado.all())
