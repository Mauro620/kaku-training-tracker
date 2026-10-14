"""Enums del dominio, tal cual el DBML.

Se mapean a tipos ENUM nativos de Postgres. Agregar un valor implica un
`ALTER TYPE` en una migración: es el precio de que la base rechace un valor
inválido en vez de aceptarlo y romper un cálculo tres meses después.
"""

from enum import StrEnum


class Demanda(StrEnum):
    alta = "alta"
    media = "media"
    baja = "baja"


class FaseCiclo(StrEnum):
    readaptacion = "readaptacion"
    carga = "carga"
    descarga = "descarga"


class EstadoCiclo(StrEnum):
    planificado = "planificado"
    activo = "activo"
    cerrado = "cerrado"


class EstadoSesionPlan(StrEnum):
    """Estado de ejecucion de un `sesion_plan`.

    `descartado` lo declara el usuario. `cumplido` y `movido` los escribe el
    service de sesion (`resolver_estado_de_plan`) cada vez que una sesion se
    crea, cambia de fecha o se borra: la columna es la fuente de verdad y el
    importador la lee directo, sin join contra `sesion`.
    """

    pendiente = "pendiente"
    cumplido = "cumplido"
    movido = "movido"
    descartado = "descartado"


class CargaLumbar(StrEnum):
    alta = "alta"
    media = "media"
    baja = "baja"


class TipoMedicion(StrEnum):
    """Determina que campos acepta un bloque de este ejercicio
    (REGLAS_NEGOCIO §15): carga->series/reps/peso_kg,
    distancia->reps/distancia_m, tiempo->duracion_s,
    tecnica->reps o duracion_s + calidad."""

    carga = "carga"
    distancia = "distancia"
    tiempo = "tiempo"
    tecnica = "tecnica"


class OrigenDato(StrEnum):
    manual = "manual"
    health_kit = "health_kit"
    notion_backfill = "notion_backfill"
