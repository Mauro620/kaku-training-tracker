"""Cierre de semana (C de la revision de UI).

Para cada dia del rango, junta la data cruda de las 5 dimensiones
(sueno, sesion, hidratacion, habitos, bienestar). La UI calcula los
flags cumplidos y renderiza el grid 5x7.

La razon de devolver data cruda y no flags ya calculados: cambiar la
regla de cumplimiento (>= objetivo vs >= 80% del objetivo) es algo
que va a iterar, y la reglon de la iteracion es la UI.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Habito,
    HabitoRegistro,
    Parametro,
    RegistroBienestar,
    RegistroHidratacion,
    RegistroSueno,
    Sesion,
)
from app.repositories.bienestar import habito as repo_habito


@dataclass(frozen=True)
class DiaCierre:
    fecha: date
    # None cuando no hay registro ese dia.
    sueno_horas: Decimal | None
    sueno_objetivo_h: Decimal
    sesion_registrada: bool
    hidratacion_ml_totales: int | None
    hidratacion_objetivo_ml: int
    habitos_marcados: int
    habitos_activos: int
    bienestar_registrado: bool


async def datos_crudos_por_dia(
    session: AsyncSession,
    usuario_id: uuid.UUID,
    desde: date,
    hasta: date,
) -> list[DiaCierre]:
    """Devuelve un DiaCierre por cada dia del rango [desde, hasta].

    La data cruda de cada dimension se busca en bulk (1 query por
    dimension), no dia por dia, para mantener latencia baja.
    """
    objetivo_sueno = await _leer_parametro(
        session,
        clave="sueno_objetivo_horas",
        default=Decimal("7.0"),
    )
    objetivo_hidratacion = await _leer_parametro(
        session,
        clave="hidratacion_objetivo_ml",
        default=Decimal("3000"),
    )

    registros_sueno = await _bulk_sueno(session, usuario_id, desde, hasta)
    sesiones = await _bulk_sesiones_por_dia(session, usuario_id, desde, hasta)
    registros_hidratacion = await _bulk_hidratacion(session, usuario_id, desde, hasta)
    registros_habitos = await _bulk_habitos(session, usuario_id, desde, hasta)
    bienestar_registrado = await _bulk_bienestar(session, usuario_id, desde, hasta)
    habitos_activos = await repo_habito.listar_activos(session, usuario_id)
    total_habitos = len(habitos_activos)

    out: list[DiaCierre] = []
    d = desde
    while d <= hasta:
        out.append(
            DiaCierre(
                fecha=d,
                sueno_horas=registros_sueno.get(d),
                sueno_objetivo_h=objetivo_sueno,
                sesion_registrada=sesiones.get(d, False),
                hidratacion_ml_totales=registros_hidratacion.get(d),
                hidratacion_objetivo_ml=int(objetivo_hidratacion),
                habitos_marcados=registros_habitos.get(d, 0),
                habitos_activos=total_habitos,
                bienestar_registrado=d in bienestar_registrado,
            )
        )
        d = d + timedelta(days=1)
    return out


# ---------- Helpers internos: lecturas en bulk por dimension ----------


async def _bulk_sueno(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> dict[date, Decimal]:
    """Devuelve {fecha: horas_sueno} para los dias con registro dentro
    del rango. Las horas ya vienen calculadas por la DB (columna
    generada)."""
    resultado = await session.scalars(
        select(RegistroSueno).where(
            RegistroSueno.usuario_id == usuario_id,
            RegistroSueno.fecha >= desde,
            RegistroSueno.fecha <= hasta,
        )
    )
    return {r.fecha: r.horas_sueno for r in resultado.all()}


async def _bulk_sesiones_por_dia(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> dict[date, bool]:
    """{fecha: True} para los dias con al menos una sesion."""
    resultado = await session.execute(
        select(Sesion.fecha)
        .where(
            Sesion.usuario_id == usuario_id,
            Sesion.fecha >= desde,
            Sesion.fecha <= hasta,
        )
        .group_by(Sesion.fecha)
    )
    return {fecha: True for (fecha,) in resultado.all()}


async def _bulk_hidratacion(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> dict[date, int]:
    """{fecha: ml_totales} para los dias con registro."""
    resultado = await session.execute(
        select(
            RegistroHidratacion.fecha,
            RegistroHidratacion.ml_totales,
        ).where(
            RegistroHidratacion.usuario_id == usuario_id,
            RegistroHidratacion.fecha >= desde,
            RegistroHidratacion.fecha <= hasta,
        )
    )
    return {row[0]: row[1] for row in resultado.all()}


async def _bulk_habitos(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> dict[date, int]:
    """{fecha: True count} para los dias con al menos un registro.

    Solo cuentan los registros en True (los False se ignoran: el
    usuario no marco nada ese dia, no es un habito 'cumplido' pero
    tampoco un 'incumplido' para un habito que no le interesa).

    Si el usuario no registro ninguno, el dia no aparece en el dict
    (la UI considera 'sin dato' cuando marcados==0 y activos>0).
    """
    resultado = await session.execute(
        select(
            HabitoRegistro.fecha,
            func.count(HabitoRegistro.habito_id),
        )
        .join(Habito, Habito.id == HabitoRegistro.habito_id)
        .where(
            Habito.usuario_id == usuario_id,
            Habito.activo.is_(True),
            HabitoRegistro.fecha >= desde,
            HabitoRegistro.fecha <= hasta,
            HabitoRegistro.valor.is_(True),
        )
        .group_by(HabitoRegistro.fecha)
    )
    return {row[0]: row[1] for row in resultado.all()}


async def _bulk_bienestar(
    session: AsyncSession, usuario_id: uuid.UUID, desde: date, hasta: date
) -> set[date]:
    """Set de fechas del rango que tienen registro de bienestar."""
    resultado = await session.scalars(
        select(RegistroBienestar.fecha).where(
            RegistroBienestar.usuario_id == usuario_id,
            RegistroBienestar.fecha >= desde,
            RegistroBienestar.fecha <= hasta,
        )
    )
    return set(resultado.all())


async def _leer_parametro(
    session: AsyncSession, *, clave: str, default: Decimal
) -> Decimal:
    """Lee un parametro sembrado. Lo dejo como helper aca en lugar de
    importarlo del repo para evitar un ciclo entre servicios."""
    valor = await session.scalar(
        select(Parametro.valor).where(Parametro.clave == clave)
    )
    if valor is None:
        return default
    return valor if valor > 0 else default
