"""Los catálogos se siembran, no se crean por API en las fases 3 y 4.

Por eso casi todos solo tienen variante `Read`: un `Create` de `tipo_sesion`
sería una puerta para meter un tipo sin `demanda` coherente y romper el
semáforo de cerveza, que consulta exactamente ese campo. `ejercicio` es la
excepción (REGLAS_NEGOCIO §15): a diferencia de las taxonomías fijas del
negocio, el universo de ejercicios de una rutina real es abierto.
"""

import uuid
from decimal import Decimal

from pydantic import Field

from app.models.enums import CargaLumbar, Demanda, TipoMedicion
from app.schemas.base import ReadBase, SchemaBase


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


class EjercicioCreate(SchemaBase):
    nombre: str = Field(min_length=1, max_length=80)
    tipo_medicion: TipoMedicion


class EjercicioRead(ReadBase):
    id: int
    nombre: str
    patron: str | None
    carga_lumbar: CargaLumbar
    tipo_sesion_id: int | None
    tipo_medicion: TipoMedicion


class ZonaCorporalRead(ReadBase):
    id: int
    nombre: str


class ParametroRead(ReadBase):
    clave: str
    valor: Decimal
    unidad: str | None
    descripcion: str
