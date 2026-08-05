"""Los catálogos se siembran, no se crean por API en las fases 3 y 4.

Por eso solo tienen variante `Read`: un `Create` de `tipo_sesion` sería una
puerta para meter un tipo sin `demanda` coherente y romper el semáforo de
cerveza, que consulta exactamente ese campo.
"""

import uuid
from decimal import Decimal

from app.models.enums import CargaLumbar, Demanda
from app.schemas.base import ReadBase


class UsuarioRead(ReadBase):
    id: uuid.UUID
    nombre: str
    peso_objetivo_kg: Decimal | None
    agua_objetivo_ml_min: int | None
    agua_objetivo_ml_max: int | None


class TipoSesionRead(ReadBase):
    id: int
    codigo: str
    nombre: str
    demanda: Demanda


class EjercicioRead(ReadBase):
    id: int
    nombre: str
    patron: str | None
    carga_lumbar: CargaLumbar


class ZonaCorporalRead(ReadBase):
    id: int
    nombre: str


class ParametroRead(ReadBase):
    clave: str
    valor: Decimal
    unidad: str | None
    descripcion: str
