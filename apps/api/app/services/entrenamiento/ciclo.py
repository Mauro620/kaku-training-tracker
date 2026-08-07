"""Orquestación de ciclo, ciclo_semana, composición semanal y cumplimiento
(REGLAS_NEGOCIO §13)."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecursoNoEncontradoError
from app.models import Ciclo, CicloSemana, CicloSemanaComposicion, SesionPlan
from app.models.enums import FaseCiclo
from app.repositories import entrenamiento as repo
from app.schemas.entrenamiento.ciclo import (
    CicloCreate,
    ComposicionItem,
    CumplimientoItem,
)

# ---------- Ciclo ----------


async def crear_ciclo(
    session: AsyncSession, usuario_id: uuid.UUID, payload: CicloCreate
) -> Ciclo:
    ciclo = await repo.crear_ciclo(
        session,
        usuario_id=usuario_id,
        numero=payload.numero,
        objetivo=payload.objetivo,
        fecha_inicio=payload.fecha_inicio,
        semanas=payload.semanas,
    )
    await session.commit()
    await session.refresh(ciclo)
    return ciclo


async def listar_ciclos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Ciclo]:
    return await repo.listar_ciclos_por_usuario(session, usuario_id)


async def obtener_ciclo(
    session: AsyncSession, usuario_id: uuid.UUID, ciclo_id: int
) -> Ciclo:
    ciclo = await repo.obtener_ciclo_por_id(session, ciclo_id)
    if ciclo is None or ciclo.usuario_id != usuario_id:
        # Mismo tratamiento que un 404 real: no filtrar si el ciclo existe
        # pero es de otro usuario.
        raise RecursoNoEncontradoError(f"ciclo {ciclo_id} no encontrado")
    return ciclo


async def cerrar_ciclo(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    ciclo_id: int,
    fecha_cierre_real: date | None,
) -> Ciclo:
    ciclo = await obtener_ciclo(session, usuario_id, ciclo_id)
    cerrado = await repo.cerrar_ciclo(session, ciclo, fecha_cierre_real or date.today())
    await session.commit()
    await session.refresh(cerrado)
    return cerrado


# ---------- Ciclo semana ----------


async def crear_semana(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    ciclo_id: int,
    *,
    numero: int,
    fase: FaseCiclo,
    rpe_objetivo_min: int | None,
    rpe_objetivo_max: int | None,
    volumen_pct: int,
) -> CicloSemana:
    await obtener_ciclo(session, usuario_id, ciclo_id)  # valida dueño
    semana = await repo.crear_ciclo_semana(
        session,
        ciclo_id=ciclo_id,
        numero=numero,
        fase=fase,
        rpe_objetivo_min=rpe_objetivo_min,
        rpe_objetivo_max=rpe_objetivo_max,
        volumen_pct=volumen_pct,
    )
    await session.commit()
    await session.refresh(semana)
    return semana


async def listar_semanas(
    session: AsyncSession, usuario_id: uuid.UUID, ciclo_id: int
) -> list[CicloSemana]:
    await obtener_ciclo(session, usuario_id, ciclo_id)
    return await repo.listar_ciclo_semanas_por_ciclo(session, ciclo_id)


async def obtener_semana(
    session: AsyncSession, usuario_id: uuid.UUID, semana_id: int
) -> CicloSemana:
    semana = await repo.obtener_ciclo_semana_por_id(session, semana_id)
    if semana is None:
        raise RecursoNoEncontradoError(f"ciclo_semana {semana_id} no encontrada")
    await obtener_ciclo(session, usuario_id, semana.ciclo_id)  # valida dueño
    return semana


async def actualizar_semana(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    semana_id: int,
    *,
    fase: FaseCiclo,
    rpe_objetivo_min: int | None,
    rpe_objetivo_max: int | None,
    volumen_pct: int,
) -> CicloSemana:
    semana = await obtener_semana(session, usuario_id, semana_id)  # valida dueño
    actualizada = await repo.actualizar_ciclo_semana(
        session,
        semana,
        fase=fase,
        rpe_objetivo_min=rpe_objetivo_min,
        rpe_objetivo_max=rpe_objetivo_max,
        volumen_pct=volumen_pct,
    )
    await session.commit()
    await session.refresh(actualizada)
    return actualizada


async def eliminar_semana(
    session: AsyncSession, usuario_id: uuid.UUID, semana_id: int
) -> None:
    """Borra la semana y todo lo que cuelga de ella. Las sesiones reales ya
    registradas NO se borran (el entrenamiento pasó de verdad): solo
    pierden la referencia al plan (REGLAS_NEGOCIO §15, mismo criterio que
    el cascade real->bloque, pero acá es orquestado a mano porque no
    queremos que borrar una semana borre sesiones reales)."""
    semana = await obtener_semana(session, usuario_id, semana_id)  # valida dueño

    planes = await repo.listar_planes_por_ciclo_semana(session, semana_id)
    for plan in planes:
        await repo.desvincular_sesiones_de_plan(session, plan.id)
        await repo.eliminar_bloques_de_plan(session, plan.id)
        await repo.eliminar_sesion_plan(session, plan)

    await repo.eliminar_composicion_de_semana(session, semana_id)
    await repo.eliminar_ciclo_semana(session, semana)
    await session.commit()


async def listar_planes_de_semana(
    session: AsyncSession, usuario_id: uuid.UUID, semana_id: int
) -> list[SesionPlan]:
    await obtener_semana(session, usuario_id, semana_id)  # valida dueño
    return await repo.listar_planes_por_ciclo_semana(session, semana_id)


def calcular_rango_semana(
    fecha_inicio_ciclo: date, numero_semana: int
) -> tuple[date, date]:
    """No es una columna (docs/schema.dbml, REGLAS_NEGOCIO §13.1): se deriva
    de `ciclo.fecha_inicio` y `ciclo_semana.numero` cada vez, para no tener
    una segunda fuente de verdad que diverja si fecha_inicio cambia."""
    inicio = fecha_inicio_ciclo + timedelta(days=(numero_semana - 1) * 7)
    fin = inicio + timedelta(days=6)
    return inicio, fin


async def rango_de_semana(
    session: AsyncSession, semana: CicloSemana
) -> tuple[date, date]:
    ciclo = await repo.obtener_ciclo_por_id(session, semana.ciclo_id)
    assert ciclo is not None  # FK garantiza que existe
    return calcular_rango_semana(ciclo.fecha_inicio, semana.numero)


# ---------- Composición y cumplimiento ----------


async def reemplazar_composicion(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    semana_id: int,
    items: list[ComposicionItem],
) -> list[CicloSemanaComposicion]:
    await obtener_semana(session, usuario_id, semana_id)  # valida dueño
    creadas = await repo.reemplazar_composicion(
        session,
        semana_id,
        [(item.tipo_sesion_id, item.cantidad_objetivo) for item in items],
    )
    await session.commit()
    return creadas


async def obtener_composicion(
    session: AsyncSession, usuario_id: uuid.UUID, semana_id: int
) -> list[CicloSemanaComposicion]:
    await obtener_semana(session, usuario_id, semana_id)  # valida dueño
    return await repo.listar_composicion_por_semana(session, semana_id)


async def calcular_cumplimiento(
    session: AsyncSession, usuario_id: uuid.UUID, semana_id: int
) -> list[CumplimientoItem]:
    semana = await obtener_semana(session, usuario_id, semana_id)
    inicio, fin = await rango_de_semana(session, semana)
    composicion = await repo.listar_composicion_por_semana(session, semana_id)
    tipos = {t.id: t for t in await repo.listar_tipos_sesion(session)}

    resultado = []
    for item in composicion:
        tipo = tipos[item.tipo_sesion_id]
        hecho = await repo.contar_sesiones_por_tipo_en_rango(
            session, usuario_id, item.tipo_sesion_id, inicio, fin
        )
        resultado.append(
            CumplimientoItem(
                tipo_sesion_id=item.tipo_sesion_id,
                tipo_sesion_codigo=tipo.codigo,
                tipo_sesion_nombre=tipo.nombre,
                objetivo=item.cantidad_objetivo,
                hecho=hecho,
                cumplido=hecho >= item.cantidad_objetivo,
            )
        )
    return resultado
