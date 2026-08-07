"""Reglas de negocio de comida_log (REGLAS_NEGOCIO §12)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError, RecursoNoEncontradoError
from app.models import ComidaLog
from app.models.enums import MomentoComida
from app.repositories import nutricion as repo
from app.services.nutricion.calculo import MacroTotal, calcular_macros, sumar_macros
from app.services.nutricion.receta import calcular_macros_de_receta, obtener_receta


async def registrar_comida(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    idempotency_key: uuid.UUID,
    fecha: date,
    momento: MomentoComida,
    receta_id: int | None,
    nota: str | None,
    items: list[tuple[int, Decimal]],
) -> ComidaLog:
    """`receta_id` xor `items`: una comida con receta resuelve sus
    ingredientes via `receta_item` (REGLAS_NEGOCIO), no se duplican acá."""
    if receta_id is not None:
        if items:
            raise InvarianteDeNegocioError(
                "una comida con receta no lleva items sueltos: los ingredientes "
                "se resuelven via la receta"
            )
        await obtener_receta(session, usuario_id, receta_id)
    elif not items:
        raise InvarianteDeNegocioError(
            "una comida sin receta necesita al menos un item"
        )
    else:
        ids = [alimento_id for alimento_id, _ in items]
        encontrados = {a.id for a in await repo.listar_alimentos_por_ids(session, ids)}
        faltantes = set(ids) - encontrados
        if faltantes:
            raise RecursoNoEncontradoError(
                f"alimento(s) no encontrado(s): {sorted(faltantes)}"
            )

    comida = await repo.crear_comida(
        session,
        usuario_id=usuario_id,
        idempotency_key=idempotency_key,
        fecha=fecha,
        momento=momento,
        receta_id=receta_id,
        nota=nota,
    )
    if items and not comida.items:
        await repo.agregar_items_comida(session, comida.id, items)
    await session.commit()

    comida_completa = await repo.obtener_comida_por_id(session, comida.id)
    assert comida_completa is not None
    return comida_completa


async def obtener_comida(
    session: AsyncSession, usuario_id: uuid.UUID, comida_id: uuid.UUID
) -> ComidaLog:
    comida = await repo.obtener_comida_por_id(session, comida_id)
    if comida is None or comida.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"comida {comida_id} no encontrada")
    return comida


async def eliminar_comida(
    session: AsyncSession, usuario_id: uuid.UUID, comida_id: uuid.UUID
) -> None:
    comida = await obtener_comida(session, usuario_id, comida_id)
    await repo.eliminar_comida(session, comida)
    await session.commit()


async def calcular_macros_de_comida(
    session: AsyncSession, usuario_id: uuid.UUID, comida: ComidaLog
) -> MacroTotal:
    if comida.receta_id is not None:
        receta = await obtener_receta(session, usuario_id, comida.receta_id)
        return await calcular_macros_de_receta(session, receta)
    alimentos = {
        a.id: a
        for a in await repo.listar_alimentos_por_ids(
            session, [item.alimento_id for item in comida.items]
        )
    }
    items = [(alimentos[item.alimento_id], item.cantidad_g) for item in comida.items]
    return calcular_macros(items)


async def listar_comidas_del_dia(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> list[ComidaLog]:
    return await repo.listar_comidas_por_fecha(session, usuario_id, fecha)


async def calcular_macros_del_dia(
    session: AsyncSession, usuario_id: uuid.UUID, fecha: date
) -> MacroTotal:
    """Macros del dia = suma de las recetas registradas mas los
    `comida_item` sueltos (REGLAS_NEGOCIO §12)."""
    comidas = await repo.listar_comidas_por_fecha(session, usuario_id, fecha)
    totales = [
        await calcular_macros_de_comida(session, usuario_id, comida)
        for comida in comidas
    ]
    return sumar_macros(totales)
