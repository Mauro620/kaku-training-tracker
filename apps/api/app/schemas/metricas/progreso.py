"""Respuestas de las cuatro tarjetas de Progreso (REGLAS_NEGOCIO §18).

Cada una trae su `conclusion`: la respuesta a la pregunta en una frase, generada
en el backend con las mismas cifras que el grafico para que no puedan divergir.
"""

from datetime import date
from typing import Literal

from app.schemas.base import ReadBase

# ----------------------------------------------------- 1. ¿Cumpli el plan? --


class SemanaCumplimiento(ReadBase):
    numero: int
    inicio: date
    fin: date
    planeadas: int
    cumplido: int
    movido: int
    descartado: int
    pendiente: int
    pct_cumplido: float | None
    pct_movido: float | None
    pct_descartado: float | None
    pct_pendiente: float | None


class CumplimientoRead(ReadBase):
    ciclo_numero: int | None
    semanas: list[SemanaCumplimiento]
    conclusion: str


# ------------------------------------------------ 2. ¿Estoy rindiendo mejor? --


class PuntoPrueba(ReadBase):
    fecha: date
    mejor: float
    pct_cambio_vs_base: float | None


class PruebaTendencia(ReadBase):
    codigo: str
    nombre: str
    unidad: str
    mejor_es_mayor: bool
    puntos: list[PuntoPrueba]


class MejorMarca(ReadBase):
    ejercicio_id: int
    ejercicio: str
    tipo_medicion: Literal["carga", "distancia", "tiempo", "tecnica"]
    # carga
    peso_max_kg: float | None = None
    rm_estimado_kg: float | None = None
    # tiempo / distancia / tecnica
    duracion_max_s: int | None = None
    distancia_max_m: float | None = None
    calidad_max: int | None = None
    fecha: date


class RendimientoRead(ReadBase):
    pruebas: list[PruebaTendencia]
    marcas: list[MejorMarca]
    conclusion: str


# ------------------------------------------------- 3. ¿Me estoy recuperando? --


class SemanaRecuperacion(ReadBase):
    inicio: date
    fin: date
    en_curso: bool
    carga_semanal: int
    acwr: float | None
    semaforo: Literal["baja", "verde", "amarillo", "rojo"] | None
    sueno_prom_h: float | None
    sueno_dias_con_dato: int


class BandasAcwr(ReadBase):
    min_seguro: float
    max_seguro: float
    alerta: float


class RecuperacionRead(ReadBase):
    semanas: list[SemanaRecuperacion]
    bandas: BandasAcwr
    sueno_objetivo_h: float
    conclusion: str


# ------------------------------------------------------ 4. ¿Voy hacia 11 %? --


class SemanaComposicion(ReadBase):
    inicio: date
    fecha_medida: date
    peso_kg: float
    cintura_cm: float | None


class ComposicionRead(ReadBase):
    semanas: list[SemanaComposicion]
    peso_objetivo_kg: float | None
    cambio_peso_kg: float | None
    cambio_cintura_cm: float | None
    conclusion: str
