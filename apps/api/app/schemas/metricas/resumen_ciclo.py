"""Forma del export `resumen_ciclo` (REGLAS_NEGOCIO §17).

Numeros como `float` y no `Decimal`: el consumidor es un LLM y un decimal
serializado como string (`"7.5"`) se lee peor que `7.5`. Es un export de solo
lectura; la precision ya se acoto al redondear (§14).
"""

from datetime import date
from typing import Literal

from app.schemas.base import ReadBase


class CicloResumen(ReadBase):
    numero: int
    objetivo: str
    estado: str
    fecha_inicio: date
    fecha_fin_prevista: date
    fecha_cierre_real: date | None
    semanas_totales: int
    # Ultimo dia que el resumen cubre: hoy, o el fin del ciclo si ya termino.
    informado_hasta: date


class CumplimientoSemana(ReadBase):
    planeadas: int
    cumplido: int
    movido: int
    descartado: int
    pendiente: int
    sesiones_sin_plan: int
    pct_ejecutado: float | None


class PlaneadoVsReal(ReadBase):
    """Solo sobre pares plan-sesion real (REGLAS_NEGOCIO §17)."""

    pares: int
    rpe_planeado_prom: float | None
    rpe_real_prom: float | None
    duracion_planeada_min: int
    duracion_real_min: int


class SesionResumen(ReadBase):
    dia_sugerido: int | None
    fecha_real: date | None
    tipo: str
    nombre: str | None
    estado_plan: str | None  # None = sesion libre, sin plan
    rpe_planeado: int | None
    rpe_real: int | None
    duracion_planeada_min: int | None
    duracion_real_min: int | None
    carga_srpe: int | None


class CargaSemana(ReadBase):
    planeada: int
    real: int


class PromedioDiario(ReadBase):
    promedio: float | None
    dias_con_dato: int
    objetivo: float


class HabitoSemana(ReadBase):
    nombre: str
    dias_cumplidos: int
    dias_con_registro: int
    dias_transcurridos: int
    pct_cumplimiento: float | None


class MedidaResumen(ReadBase):
    fecha: date
    peso_kg: float
    cintura_cm: float | None


class SemanaResumen(ReadBase):
    numero: int
    fase: str
    volumen_pct: int
    rpe_objetivo_min: int | None
    rpe_objetivo_max: int | None
    inicio: date
    fin: date
    estado: Literal["completa", "en_curso"]
    cumplimiento: CumplimientoSemana
    planeado_vs_real: PlaneadoVsReal
    carga: CargaSemana
    sesiones: list[SesionResumen]
    sueno_horas: PromedioDiario
    agua_ml: PromedioDiario
    habitos: list[HabitoSemana]
    medidas: list[MedidaResumen]


class ResultadoPrueba(ReadBase):
    fecha: date
    mejor: float
    media: float
    pct_decremento: float | None
    pct_cambio_vs_base: float | None


class PruebaResumen(ReadBase):
    codigo: str
    nombre: str
    unidad: str
    mejor_es_mayor: bool
    base_fecha: date
    base_mejor: float
    resultados: list[ResultadoPrueba]


class CambioCorporal(ReadBase):
    peso_inicial_kg: float
    peso_final_kg: float
    cambio_peso_kg: float
    cambio_cintura_cm: float | None


class TotalesCiclo(ReadBase):
    cumplimiento: CumplimientoSemana
    carga_real: int
    carga_planeada: int


class ResumenCicloRead(ReadBase):
    ciclo: CicloResumen
    totales: TotalesCiclo
    semanas: list[SemanaResumen]
    pruebas: list[PruebaResumen]
    cambio_corporal: CambioCorporal | None
