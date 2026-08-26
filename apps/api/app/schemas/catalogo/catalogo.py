"""Los catálogos se siembran, no se crean por API en las fases 3 y 4.

Por eso casi todos solo tienen variante `Read`: un `Create` de `tipo_sesion`
sería una puerta para meter un tipo sin `demanda` coherente y romper el
semáforo de cerveza, que consulta exactamente ese campo. `ejercicio` es la
excepción (REGLAS_NEGOCIO §15): a diferencia de las taxonomías fijas del
negocio, el universo de ejercicios de una rutina real es abierto.
"""

import uuid
from datetime import date
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


class EjercicioRead(ReadBase):
    id: int
    nombre: str
    patron: str | None
    carga_lumbar: CargaLumbar
    tipo_sesion_id: int | None
    tipo_medicion: TipoMedicion
    descripcion: str | None
    # Backward-compat: `activo` aparece en R6 para reflejar la nueva columna.
    # El importador y los tests previos siguen importando este schema.
    activo: bool = True


class EjercicioListItem(ReadBase):
    """Item del listado de banco de ejercicios (R6).

    Trae `usos` (cuenta filas de `bloque` con este ejercicio) y `ultima_vez`
    (fecha del último uso) precomputados por la query del repo, así el
    frontend no necesita pedirlo en una segunda llamada.
    """

    id: int
    nombre: str
    patron: str | None
    carga_lumbar: CargaLumbar
    tipo_sesion_id: int | None
    tipo_medicion: TipoMedicion
    descripcion: str | None
    activo: bool
    usos: int
    ultima_vez: date | None


class EjercicioListRead(ReadBase):
    """Envelope del listado: items + total. Sin paginación todavía: el
    universo es chico (decenas de ejercicios), el `total` queda para que
    agregar LIMIT después no rompa el contrato."""

    items: list[EjercicioListItem]
    total: int


class EjercicioHistorialItem(ReadBase):
    """Últimas ejecuciones del ejercicio (R6, subquery top 5)."""

    sesion_id: uuid.UUID
    fecha: date
    bloque_id: int
    orden: int
    series: int | None
    reps: int | None
    peso_kg: Decimal | None


class EjercicioPosibleDuplicado(ReadBase):
    """Candidato a duplicado del ejercicio: similitud ≥0.75 contra el nombre
    propio, calculado en el service."""

    id: int
    nombre: str
    similitud: float


class EjercicioDetalleRead(ReadBase):
    """Detalle completo del ejercicio (R6): datos + historial + duplicados."""

    id: int
    nombre: str
    patron: str | None
    carga_lumbar: CargaLumbar
    tipo_sesion_id: int | None
    tipo_medicion: TipoMedicion
    descripcion: str | None
    activo: bool
    historial: list[EjercicioHistorialItem] = Field(default_factory=list)
    posibles_duplicados: list[EjercicioPosibleDuplicado] = Field(default_factory=list)


class EjercicioCreate(SchemaBase):
    """Crear ejercicio. Campos nuevos respecto al legacy: `patron` y
    `carga_lumbar` son opcionales (default None y 'baja' respectivamente).
    `tipo_medicion` sigue siendo obligatorio (REGLAS_NEGOCIO §15)."""

    nombre: str = Field(min_length=1, max_length=80)
    tipo_medicion: TipoMedicion
    descripcion: str | None = None
    patron: str | None = Field(default=None, max_length=40)
    carga_lumbar: CargaLumbar | None = None


class EjercicioUpdate(SchemaBase):
    """Editar ejercicio. `tipo_medicion` NO es editable: el schema base ya
    trae `extra='forbid'`, así que un cliente que mande ese campo recibe
    422 antes de tocar la base (REGLAS_NEGOCIO §15).

    Los campos son opcionales y None significa "no tocar". Para borrar la
    descripción se manda string vacío; el service lo traduce a None para
    no contaminar el contrato del schema."""

    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = None
    patron: str | None = Field(default=None, max_length=40)
    carga_lumbar: CargaLumbar | None = None
    activo: bool | None = None


class ZonaCorporalRead(ReadBase):
    id: int
    nombre: str


class TipoTestRead(ReadBase):
    id: int
    codigo: str
    nombre: str
    unidad: str
    mejor_es_mayor: bool


class ParametroRead(ReadBase):
    clave: str
    valor: Decimal
    unidad: str | None
    descripcion: str
