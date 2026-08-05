import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import ReadBase, SchemaBase


class RegistroHidratacionCreate(SchemaBase):
    """`cantidad_ml` es lo que se toma en ESTE tap (ej. un termo de 750ml),
    no el total del día: se suma a lo ya registrado."""

    fecha: date
    cantidad_ml: int = Field(gt=0)


class RegistroHidratacionRead(ReadBase):
    id: int
    usuario_id: uuid.UUID
    fecha: date
    ml_totales: int
