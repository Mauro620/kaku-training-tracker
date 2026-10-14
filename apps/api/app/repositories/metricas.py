"""Lecturas agregadas para las métricas de ciclo y de Progreso. Solo SELECT,
sin reglas de negocio: devuelven filas en crudo para que el servicio calcule."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Ciclo,
    CicloSemana,
    HabitoRegistro,
    MedidaCorporal,
    RegistroHidratacion,
    RegistroSueno,
    Sesion,
    SesionPlan,
    TestFisico,
    TipoSesion,
    TipoTest,
)
from app.models.bienestar.habito import Habito
from app.models.enums import EstadoCiclo


async def ciclo_resumible(session: AsyncSession, usuario_id: uuid.UUID) -> Ciclo | None:
    """El `activo` de mayor numero; si no hay, el `cerrado` de mayor numero
    (REGLAS_NEGOCIO §17). Un `planificado` no tiene historia."""
    for estado in (EstadoCiclo.activo, EstadoCiclo.cerrado):
        ciclo = await session.scalar(
            select(Ciclo)
            .where(Ciclo.usuario_id == usuario_id, Ciclo.estado == estado)
            .order_by(Ciclo.numero.desc())
            .limit(1)
        )
        if ciclo is not None:
            return ciclo
    return None


async def planes_del_ciclo(
    session: AsyncSession, ciclo_id: int
) -> list[tuple[SesionPlan, str, int]]:
    """`(plan, codigo del tipo, numero de semana)` de todos los planes."""
    filas = await session.execute(
        select(SesionPlan, TipoSesion.codigo, CicloSemana.numero)
        .join(CicloSemana, SesionPlan.ciclo_semana_id == CicloSemana.id)
        .join(TipoSesion, SesionPlan.tipo_sesion_id == TipoSesion.id)
        .where(CicloSemana.ciclo_id == ciclo_id)
        .order_by(CicloSemana.numero, SesionPlan.dia_sugerido, SesionPlan.id)
    )
    return [(p, codigo, numero) for p, codigo, numero in filas.all()]


async def sesiones_en_rango(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> list[tuple[Sesion, str]]:
    """`(sesion, codigo del tipo)` con fecha en [desde, hasta]."""
    filas = await session.execute(
        select(Sesion, TipoSesion.codigo)
        .join(TipoSesion, Sesion.tipo_sesion_id == TipoSesion.id)
        .where(
            Sesion.usuario_id == usuario_id,
            Sesion.fecha >= desde,
            Sesion.fecha <= hasta,
        )
        .order_by(Sesion.fecha, Sesion.registrado_en)
    )
    return [(s, codigo) for s, codigo in filas.all()]


async def sueno_en_rango(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> list[tuple[date, Decimal]]:
    filas = await session.execute(
        select(RegistroSueno.fecha, RegistroSueno.horas_sueno).where(
            RegistroSueno.usuario_id == usuario_id,
            RegistroSueno.fecha >= desde,
            RegistroSueno.fecha <= hasta,
        )
    )
    return [(f, h) for f, h in filas.all()]


async def hidratacion_en_rango(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> list[tuple[date, int]]:
    filas = await session.execute(
        select(RegistroHidratacion.fecha, RegistroHidratacion.ml_totales).where(
            RegistroHidratacion.usuario_id == usuario_id,
            RegistroHidratacion.fecha >= desde,
            RegistroHidratacion.fecha <= hasta,
        )
    )
    return [(f, ml) for f, ml in filas.all()]


async def habitos_activos(session: AsyncSession, usuario_id: uuid.UUID) -> list[Habito]:
    resultado = await session.scalars(
        select(Habito)
        .where(Habito.usuario_id == usuario_id, Habito.activo.is_(True))
        .order_by(Habito.orden, Habito.id)
    )
    return list(resultado.all())


async def registros_de_habitos_en_rango(
    session: AsyncSession, habito_ids: list[int], desde: date, hasta: date
) -> list[HabitoRegistro]:
    if not habito_ids:
        return []
    resultado = await session.scalars(
        select(HabitoRegistro).where(
            HabitoRegistro.habito_id.in_(habito_ids),
            HabitoRegistro.fecha >= desde,
            HabitoRegistro.fecha <= hasta,
        )
    )
    return list(resultado.all())


async def medidas_en_rango(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> list[MedidaCorporal]:
    resultado = await session.scalars(
        select(MedidaCorporal)
        .where(
            MedidaCorporal.usuario_id == usuario_id,
            MedidaCorporal.fecha >= desde,
            MedidaCorporal.fecha <= hasta,
        )
        .order_by(MedidaCorporal.fecha)
    )
    return list(resultado.all())


async def tests_con_tipo_hasta(
    session: AsyncSession, usuario_id: uuid.UUID, hasta: date
) -> list[tuple[TestFisico, TipoTest]]:
    """TODO el historico hasta `hasta`, con intentos: la base de §8 es el
    primer test historico, que puede ser anterior al ciclo."""
    filas = await session.execute(
        select(TestFisico, TipoTest)
        .join(TipoTest, TestFisico.tipo_test_id == TipoTest.id)
        .options(selectinload(TestFisico.intentos))
        .where(TestFisico.usuario_id == usuario_id, TestFisico.fecha <= hasta)
        .order_by(TestFisico.fecha, TestFisico.id)
    )
    return [(t, tipo) for t, tipo in filas.all()]
