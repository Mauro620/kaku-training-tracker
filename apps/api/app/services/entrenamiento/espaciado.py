"""Validación de espaciado al sugerir día para un sesion_plan
(REGLAS_NEGOCIO §13.3).

No evalúa nada si `dia_sugerido` es None: un plan sin día sugerido no
compromete nada, no hay fecha candidata que validar.
"""

import math
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvarianteDeNegocioError
from app.models import Ciclo, CicloSemana, TipoSesion
from app.models.enums import Demanda
from app.repositories import entrenamiento as repo
from app.services.catalogo import parametro as parametro_service
from app.services.entrenamiento.ciclo import calcular_rango_semana

CODIGO_FUERZA = "fuerza"
CODIGO_PARTIDO = "partido"


def _fecha_absoluta(ciclo: Ciclo, semana: CicloSemana, dia_sugerido: int) -> date:
    inicio_semana, _ = calcular_rango_semana(ciclo.fecha_inicio, semana.numero)
    return inicio_semana + timedelta(days=dia_sugerido)


async def _horas_a_dias(session: AsyncSession, clave: str) -> int:
    parametro = await parametro_service.obtener(session, clave)
    return math.ceil(float(parametro.valor) / 24)


async def validar_espaciado(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    ciclo: Ciclo,
    semana: CicloSemana,
    tipo_sesion: TipoSesion,
    dia_sugerido: int | None,
) -> None:
    if dia_sugerido is None:
        return

    candidata = _fecha_absoluta(ciclo, semana, dia_sugerido)
    rango_desde = ciclo.fecha_inicio
    rango_hasta = ciclo.fecha_fin_prevista

    if tipo_sesion.codigo == CODIGO_FUERZA:
        min_dias = await _horas_a_dias(session, "fuerza_separacion_min_horas")
        reales = await repo.listar_fechas_por_tipo_en_rango(
            session, usuario_id, tipo_sesion.id, rango_desde, rango_hasta
        )
        planificadas = await _fechas_planificadas(session, ciclo, [tipo_sesion.id])
        for otra in [*reales, *planificadas]:
            if otra == candidata:
                continue
            if abs((otra - candidata).days) < min_dias:
                raise InvarianteDeNegocioError(
                    f"El día sugerido ({candidata}) queda a menos de "
                    f"{min_dias} días de otra sesión de fuerza ({otra}). "
                    f"Mínimo: fuerza_separacion_min_horas."
                )

    if tipo_sesion.codigo == CODIGO_PARTIDO:
        ventana_dias = await _horas_a_dias(session, "partido_ventana_previa_horas")
        tipos_alta = [
            t.id
            for t in await repo.listar_tipos_sesion(session)
            if t.demanda == Demanda.alta and t.codigo != CODIGO_PARTIDO
        ]
        reales = await repo.listar_fechas_de_demanda_en_rango(
            session, usuario_id, tipos_alta, rango_desde, rango_hasta
        )
        planificadas = await _fechas_planificadas(session, ciclo, tipos_alta)
        for otra in [*reales, *planificadas]:
            dias_antes = (candidata - otra).days
            if 0 < dias_antes <= ventana_dias:
                raise InvarianteDeNegocioError(
                    f"El día sugerido para el partido ({candidata}) tiene una "
                    f"sesión de demanda alta {dias_antes} día(s) antes ({otra}). "
                    f"Ventana requerida: partido_ventana_previa_horas."
                )


async def _fechas_planificadas(
    session: AsyncSession, ciclo: Ciclo, tipo_sesion_ids: list[int]
) -> list[date]:
    """Fechas absolutas de otros sesion_plan del mismo ciclo con
    dia_sugerido ya fijado, para los tipos dados."""
    planes = await repo.listar_planes_por_ciclo_y_tipos(
        session, ciclo.id, tipo_sesion_ids
    )
    if not planes:
        return []
    semanas = {
        s.id: s for s in await repo.listar_ciclo_semanas_por_ciclo(session, ciclo.id)
    }
    fechas = []
    for plan in planes:
        if plan.ciclo_semana_id is None or plan.dia_sugerido is None:
            continue
        semana = semanas.get(plan.ciclo_semana_id)
        if semana is None:
            continue
        fechas.append(_fecha_absoluta(ciclo, semana, plan.dia_sugerido))
    return fechas
