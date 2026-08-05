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


class MomentoComida(StrEnum):
    desayuno = "desayuno"
    media_manana = "media_manana"
    almuerzo = "almuerzo"
    merienda = "merienda"
    cena = "cena"


class EstadoPesaje(StrEnum):
    crudo = "crudo"
    cocido = "cocido"


class CargaLumbar(StrEnum):
    alta = "alta"
    media = "media"
    baja = "baja"


class OrigenDato(StrEnum):
    manual = "manual"
    health_kit = "health_kit"
    notion_backfill = "notion_backfill"


class GrupoAlimento(StrEnum):
    """`verdura` es el único grupo que cuenta para pct_comidas_con_vegetal."""

    proteina_animal = "proteina_animal"
    lacteo = "lacteo"
    cereal = "cereal"
    leguminosa = "leguminosa"
    tuberculo = "tuberculo"
    verdura = "verdura"
    fruta = "fruta"
    grasa = "grasa"
    procesado = "procesado"
