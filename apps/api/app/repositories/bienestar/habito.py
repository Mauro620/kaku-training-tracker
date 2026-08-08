"""Persistencia de habito y habito_registro. Sin reglas de negocio."""

import uuid
from datetime import date
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Habito, HabitoRegistro


async def listar_activos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    return list(
        (
            await session.scalars(
                select(Habito)
                .where(Habito.usuario_id == usuario_id, Habito.activo.is_(True))
                .order_by(Habito.orden)
            )
        ).all()
    )


async def listar_todos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    """Pantalla de Ajustes: incluye archivados para mostrar el historial
    y permitir 'desarchivar' (volver a activo=true). Orden: activos
    primero por orden, despues archivados por nombre."""
    return list(
        (
            await session.scalars(
                select(Habito)
                .where(Habito.usuario_id == usuario_id)
                .order_by(Habito.activo.desc(), Habito.orden, Habito.nombre)
            )
        ).all()
    )


async def crear(
    session: AsyncSession, usuario_id: uuid.UUID, *, nombre: str, orden: int
) -> Habito:
    """Crea un habito nuevo del usuario. El nombre no puede estar
    repetido por (usuario_id, nombre) (constraint UNIQUE)."""
    habito = Habito(usuario_id=usuario_id, nombre=nombre, orden=orden)
    session.add(habito)
    await session.flush()
    return habito


async def actualizar(
    session: AsyncSession,
    habito: Habito,
    *,
    nombre: str | None = None,
    activo: bool | None = None,
    orden: int | None = None,
) -> Habito:
    """Modifica campos de un habito. Si activo=False, se archiva (D3 del
    prompt de revision UI: archivado NUNCA es DELETE)."""
    if nombre is not None:
        habito.nombre = nombre
    if activo is not None:
        habito.activo = activo
    if orden is not None:
        habito.orden = orden
    await session.flush()
    return habito


async def obtener_habito(
    session: AsyncSession, usuario_id: uuid.UUID, habito_id: int
) -> Habito | None:
    return cast(
        "Habito | None",
        await session.scalar(
            select(Habito).where(
                Habito.id == habito_id, Habito.usuario_id == usuario_id
            )
        ),
    )


async def upsert_registro(
    session: AsyncSession,
    habito_id: int,
    fecha: date,
    valor: bool,
    idempotency_key: uuid.UUID | None,
) -> HabitoRegistro:
    """PK compuesta `(habito_id, fecha)`. Fase 5: ver patron de 3 pasos en
    el repo de Sueno."""
    valores: dict[str, object] = {
        "habito_id": habito_id,
        "fecha": fecha,
        "valor": valor,
        "idempotency_key": idempotency_key,
    }

    if idempotency_key is not None:
        existente_por_key = await session.scalar(
            select(HabitoRegistro).where(
                HabitoRegistro.idempotency_key == idempotency_key
            )
        )
        if existente_por_key is not None:
            return existente_por_key

        stmt = (
            pg_insert(HabitoRegistro)
            .values(**valores)
            .on_conflict_do_nothing()
            .returning(HabitoRegistro)
        )
        creada = await session.scalar(stmt)
        if creada is not None:
            return creada

        actualizado = await session.scalar(
            update(HabitoRegistro)
            .where(
                HabitoRegistro.habito_id == habito_id,
                HabitoRegistro.fecha == fecha,
            )
            .values(
                valor=valor,
                idempotency_key=idempotency_key,
            )
            .returning(HabitoRegistro)
        )
        if actualizado is None:
            raise RuntimeError(
                "habito_registro no encontrado despues de on_conflict_do_nothing"
            )
        return actualizado

    stmt = (
        pg_insert(HabitoRegistro)
        .values(**valores)
        .on_conflict_do_update(
            index_elements=["habito_id", "fecha"], set_={"valor": valor}
        )
        .returning(HabitoRegistro)
    )
    resultado = await session.scalar(stmt)
    return cast("HabitoRegistro", resultado)


async def listar_registros_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[HabitoRegistro]:
    return list(
        (
            await session.scalars(
                select(HabitoRegistro)
                .join(Habito, Habito.id == HabitoRegistro.habito_id)
                .where(Habito.usuario_id == usuario_id, HabitoRegistro.fecha == fecha)
            )
        ).all()
    )
