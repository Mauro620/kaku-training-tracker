import uuid

from pydantic import Field

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import NoNegativo


class PartidoCreate(SchemaBase):
    """Un partido ES una sesion existente (REGLAS_NEGOCIO): `sesion_id`
    referencia una sesion ya creada, duracion y RPE viven ahi."""

    sesion_id: uuid.UUID
    rival: str | None = Field(default=None, max_length=80)
    formato: str | None = Field(default=None, max_length=20)
    minutos_jugados: NoNegativo
    goles: NoNegativo = 0
    asistencias: NoNegativo = 0
    recuperaciones: NoNegativo | None = None
    salio_bien: str | None = None
    a_ajustar: str | None = None


class PartidoRead(ReadBase):
    id: uuid.UUID
    sesion_id: uuid.UUID
    rival: str | None
    formato: str | None
    minutos_jugados: int
    goles: int
    asistencias: int
    recuperaciones: int | None
    salio_bien: str | None
    a_ajustar: str | None
