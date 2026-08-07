"""Persistencia de test_fisico y test_intento. Sin reglas de negocio."""

import uuid
from datetime import date
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TestFisico, TestIntento


async def crear(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    idempotency_key: uuid.UUID,
    fecha: date,
    tipo_test_id: int,
    superficie: str | None,
    condiciones: str | None,
) -> TestFisico:
    """Inserta idempotente por `idempotency_key`. `(usuario_id, tipo_test_id,
    fecha)` no es unico a proposito: se puede repetir un test el mismo dia."""
    stmt = (
        pg_insert(TestFisico)
        .values(
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            fecha=fecha,
            tipo_test_id=tipo_test_id,
            superficie=superficie,
            condiciones=condiciones,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(TestFisico)
    )
    creado = await session.scalar(stmt)
    if creado is not None:
        return creado

    existente = await session.scalar(
        select(TestFisico).where(TestFisico.idempotency_key == idempotency_key)
    )
    if existente is None:
        raise RuntimeError(
            "test_fisico no encontrado despues de on_conflict_do_nothing"
        )
    return existente


async def agregar_intentos(
    session: AsyncSession, test_fisico_id: uuid.UUID, valores: list[Decimal]
) -> list[TestIntento]:
    nuevos = [
        TestIntento(test_fisico_id=test_fisico_id, numero=numero, valor=valor)
        for numero, valor in enumerate(valores, start=1)
    ]
    session.add_all(nuevos)
    await session.flush()
    return nuevos


async def contar_intentos(session: AsyncSession, test_fisico_id: uuid.UUID) -> int:
    """Cuenta via query, no via `test.intentos`: un objeto recien creado por
    `crear()` (INSERT...RETURNING) no trae la coleccion cargada, y acceder a
    la relacion lazy fuera del greenlet async rompe con MissingGreenlet."""
    total = await session.scalar(
        select(func.count())
        .select_from(TestIntento)
        .where(TestIntento.test_fisico_id == test_fisico_id)
    )
    return total or 0


async def eliminar_intentos(session: AsyncSession, test_fisico_id: uuid.UUID) -> None:
    await session.execute(
        delete(TestIntento).where(TestIntento.test_fisico_id == test_fisico_id)
    )


async def obtener_por_id(
    session: AsyncSession, test_fisico_id: uuid.UUID
) -> TestFisico | None:
    return cast(
        "TestFisico | None",
        await session.scalar(
            select(TestFisico)
            .where(TestFisico.id == test_fisico_id)
            .options(selectinload(TestFisico.intentos))
        ),
    )


async def listar_por_fecha(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[TestFisico]:
    resultado = await session.scalars(
        select(TestFisico)
        .where(TestFisico.usuario_id == usuario_id, TestFisico.fecha == fecha)
        .options(selectinload(TestFisico.intentos))
    )
    return list(resultado.all())


async def listar_por_tipo(
    session: AsyncSession, usuario_id: uuid.UUID, tipo_test_id: int
) -> list[TestFisico]:
    """Ordenado por fecha ascendente: el primero es `valor_base` para
    `pct_cambio` (REGLAS_NEGOCIO §8)."""
    resultado = await session.scalars(
        select(TestFisico)
        .where(
            TestFisico.usuario_id == usuario_id,
            TestFisico.tipo_test_id == tipo_test_id,
        )
        .options(selectinload(TestFisico.intentos))
        .order_by(TestFisico.fecha)
    )
    return list(resultado.all())


async def eliminar(session: AsyncSession, test_fisico: TestFisico) -> None:
    await session.delete(test_fisico)
    await session.flush()
