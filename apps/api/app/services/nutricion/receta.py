"""Reglas de negocio de receta (REGLAS_NEGOCIO §12).

Los macros de una receta son derivados: se calculan al leer, nunca se
almacenan, para que corregir un `alimento` no deje totales viejos dando
vueltas."""

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Receta
from app.models.enums import MomentoComida
from app.repositories import nutricion as repo
from app.services.nutricion.calculo import MacroTotal, calcular_macros


async def _validar_alimentos(
    session: AsyncSession, items: list[tuple[int, Decimal]]
) -> None:
    ids = [alimento_id for alimento_id, _ in items]
    encontrados = {a.id for a in await repo.listar_alimentos_por_ids(session, ids)}
    faltantes = set(ids) - encontrados
    if faltantes:
        raise RecursoNoEncontradoError(
            f"alimento(s) no encontrado(s): {sorted(faltantes)}"
        )


async def crear_receta(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    *,
    nombre: str,
    momento_default: MomentoComida | None,
    items: list[tuple[int, Decimal]],
) -> Receta:
    await _validar_alimentos(session, items)
    receta = await repo.crear_receta(
        session, usuario_id=usuario_id, nombre=nombre, momento_default=momento_default
    )
    await repo.agregar_items_receta(session, receta.id, items)
    await session.commit()
    receta_completa = await repo.obtener_receta_por_id(session, receta.id)
    assert receta_completa is not None
    return receta_completa


async def obtener_receta(
    session: AsyncSession, usuario_id: uuid.UUID, receta_id: int
) -> Receta:
    receta = await repo.obtener_receta_por_id(session, receta_id)
    if receta is None or receta.usuario_id != usuario_id:
        raise RecursoNoEncontradoError(f"receta {receta_id} no encontrada")
    return receta


async def listar_recetas(session: AsyncSession, usuario_id: uuid.UUID) -> list[Receta]:
    return await repo.listar_recetas_por_usuario(session, usuario_id)


async def actualizar_receta(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    receta_id: int,
    *,
    nombre: str,
    momento_default: MomentoComida | None,
    items: list[tuple[int, Decimal]],
) -> Receta:
    """PUT reemplaza cabecera + items completo, igual que
    ciclo_semana_composicion y sesion: declarar la receta entera de una vez
    evita items viejos de un alimento que ya no forma parte de ella."""
    receta = await obtener_receta(session, usuario_id, receta_id)
    await _validar_alimentos(session, items)

    # Capturamos el id antes de expirar: si no, el siguiente uso de
    # `receta.id` (despues del DELETE) dispara una recarga lazy que no
    # puede resolverse dentro de un sync block async.
    rid = receta.id

    await repo.actualizar_receta_cabecera(
        session, receta, nombre=nombre, momento_default=momento_default
    )
    await repo.eliminar_items_receta(session, rid)
    # El DELETE fue via Core: el ORM todavia tiene los items viejos en la
    # coleccion `receta.items` (cargados por obtener_receta -> selectinload).
    # session.expire_all() descarta TODA la identidad cargada de la sesion,
    # no solo la relacion, asi evitamos que el proximo flush intente UPDATE
    # sobre filas que ya no existen en la DB.
    session.expire_all()
    await repo.agregar_items_receta(session, rid, items)
    await session.commit()

    receta_completa = await repo.obtener_receta_por_id(session, rid)
    assert receta_completa is not None
    return receta_completa


async def eliminar_receta(
    session: AsyncSession, usuario_id: uuid.UUID, receta_id: int
) -> None:
    receta = await obtener_receta(session, usuario_id, receta_id)
    # El FK de receta_item.receta_id NO tiene ON DELETE CASCADE (el DBML lo
    # deja no action a proposito: una receta borrada no deberia arrastrar
    # registros silenciosamente). Borramos los items primero para que el
    # commit no rebote con un FK violation.
    await repo.eliminar_items_receta(session, receta.id)
    await repo.eliminar_receta(session, receta)
    await session.commit()


async def calcular_macros_de_receta(
    session: AsyncSession, receta: Receta
) -> MacroTotal:
    alimentos = {
        a.id: a
        for a in await repo.listar_alimentos_por_ids(
            session, [item.alimento_id for item in receta.items]
        )
    }
    items = [(alimentos[item.alimento_id], item.cantidad_g) for item in receta.items]
    return calcular_macros(items)
