import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from app.models.enums import CargaLumbar, TipoMedicion
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import (
    Calidad,
    Distancia,
    DuracionMin,
    DuracionSeg,
    NoNegativo,
    Peso,
    Positivo,
    Rpe,
)


class SesionCreate(SchemaBase):
    """`id` e `idempotency_key` los genera el cliente antes de tener red.

    Repetir una `idempotency_key` tiene que devolver el recurso existente, no
    crear un duplicado ni fallar (fase 5).
    """

    id: uuid.UUID | None = None
    idempotency_key: uuid.UUID
    sesion_plan_id: int | None = None
    fecha: date
    tipo_sesion_id: int
    duracion_min: DuracionMin
    rpe: Rpe
    nota: str | None = None
    # Bloques opcionales en el mismo body. Si se mandan, se crean con el
    # `sesion_id` que el server asigna a la sesion. Si no, se crean via
    # POST /bloques/{sesion_id} por separado.
    bloques: list["BloqueSinSesionCreate"] | None = None


class SesionUpdate(SchemaBase):
    """PUT reemplaza la sesion completa (cabecera + bloques), igual que
    ciclo_semana_composicion: declarar todo de una vez evita bloques
    viejos de un `orden` que ya no existe. `sesion_plan_id` no se
    reasigna por acá: el link nace en la creación, no en la edición."""

    fecha: date
    tipo_sesion_id: int
    duracion_min: DuracionMin
    rpe: Rpe
    nota: str | None = None
    bloques: list["BloqueSinSesionCreate"] | None = None


class SesionRead(ReadBase):
    id: uuid.UUID
    usuario_id: uuid.UUID
    sesion_plan_id: int | None
    fecha: date
    tipo_sesion_id: int
    duracion_min: int
    rpe: int
    nota: str | None
    # Derivada, nunca se captura: carga_srpe = rpe * duracion_min.
    carga_srpe: int
    registrado_en: datetime
    # Bloques de la sesion, ordenados. El router los carga via selectinload
    # para evitar N+1 cuando se listan varias sesiones.
    bloques: list["BloqueRead"] = Field(default_factory=list)


class BloqueCreate(SchemaBase):
    """Que campos aplican los determina `ejercicio.tipo_medicion`
    (REGLAS_NEGOCIO §15): el service valida, acá todo es opcional salvo lo
    estructural (ejercicio, orden)."""

    sesion_id: uuid.UUID
    ejercicio_id: int
    orden: NoNegativo
    series: Positivo | None = None
    reps: Positivo | None = None
    distancia_m: Distancia | None = None
    duracion_s: DuracionSeg | None = None
    calidad: Calidad | None = None
    peso_kg: Peso | None = None
    rpe: Rpe | None = None
    dolor_lumbar: bool = False
    # DE ESTA VEZ (REGLAS_NEGOCIO §15), precargada desde bloque_plan.nota.
    nota: str | None = Field(default=None, max_length=120)


class BloqueSinSesionCreate(SchemaBase):
    """Un bloque dentro del body de POST /sesiones: el `sesion_id` lo
    completa el server con el id de la sesion que se acaba de crear."""

    ejercicio_id: int
    orden: NoNegativo
    series: Positivo | None = None
    reps: Positivo | None = None
    distancia_m: Distancia | None = None
    duracion_s: DuracionSeg | None = None
    calidad: Calidad | None = None
    peso_kg: Peso | None = None
    rpe: Rpe | None = None
    dolor_lumbar: bool = False
    nota: str | None = Field(default=None, max_length=120)


class BloqueUpdate(SchemaBase):
    ejercicio_id: int | None = None
    orden: NoNegativo | None = None
    series: Positivo | None = None
    reps: Positivo | None = None
    distancia_m: Distancia | None = None
    duracion_s: DuracionSeg | None = None
    calidad: Calidad | None = None
    peso_kg: Peso | None = None
    rpe: Rpe | None = None
    dolor_lumbar: bool | None = None
    nota: str | None = Field(default=None, max_length=120)


class BloqueRead(ReadBase):
    id: int
    sesion_id: uuid.UUID
    ejercicio_id: int
    orden: int
    series: int | None
    reps: int | None
    distancia_m: Distancia | None
    duracion_s: int | None
    calidad: int | None
    peso_kg: Peso | None
    rpe: int | None
    dolor_lumbar: bool
    nota: str | None


class BloqueDeltaRead(ReadBase):
    """`real - plan` por campo, NULL si falta el objetivo (SPEC §2.1).
    El router de detalle de sesion lo construye a partir de
    `app.services.catalogo.delta.delta_bloque`."""

    series: int | None
    reps: int | None
    peso_kg: Decimal | None
    distancia_m: Decimal | None
    duracion_s: int | None


class SesionDeltaRead(ReadBase):
    """Delta a nivel de sesion (SPEC §2.1). `carga_srpe` se calcula contra
    `duracion_min_est * rpe_objetivo` y es NULL si falta alguno."""

    duracion_min: int | None
    rpe: int | None
    carga_srpe: int | None


# Resuelve las forward refs.
SesionCreate.model_rebuild()
SesionUpdate.model_rebuild()
SesionRead.model_rebuild()


# ============================================================ detalle (R8) ==.
#
# Schemas para `GET /sesiones/{id}` (SPEC §3.7). Son subsets anidados de
# los schemas existentes (SesionRead, BloqueRead, etc.) para que el detalle
# se pueda serializar sin exponer columnas internas como `tipo_sesion_id` o
# `ejercicio_id` pelado.
#
# `plan` y `molestias` se dejan como `dict | None` / `list[dict]` por ahora:
# R9 va a introducir `PlanDetalleEnSesionRead` y `MolestiaDetalleRead` con
# su propia forma. Hasta entonces, el servicio pasa un `dict` armado a
# mano para que el contrato sea coherente con lo que el frontend va a
# terminar consumiendo.


class SesionTipoRead(ReadBase):
    """Subset de `TipoSesionRead` anidado en `SesionDetalleRead`. Sin
    `demanda` (info interna del catalogo, no del detalle)."""

    id: int
    codigo: str
    nombre: str


class BloqueEjercicioEnDetalleRead(ReadBase):
    """Subset del `EjercicioRead` para anidar en cada bloque del detalle.
    Sin `patron`, `tipo_sesion_id` ni `activo`: el detalle expone lo que
    el usuario ve al ejecutar (nombre, tipo de medicion, descripcion
    tecnica y carga lumbar para alertas)."""

    id: int
    nombre: str
    tipo_medicion: TipoMedicion
    descripcion: str | None
    carga_lumbar: CargaLumbar


class BloqueObjetivoRead(ReadBase):
    """Subset de `BloquePlanRead` para anidar en bloques y bloques no
    ejecutados. Sin `sesion_plan_id` (redundante con el padre) ni
    `ejercicio_id` (ya viene en `BloqueEjercicioEnDetalleRead`)."""

    id: int
    orden: int
    series: int | None
    reps_min: int | None
    reps_max: int | None
    peso_objetivo_kg: Decimal | None
    distancia_objetivo_m: Decimal | None
    duracion_objetivo_s: int | None
    nota: str | None


class BloqueDetalleRead(ReadBase):
    """Lo que el usuario ve al tocar un bloque en el detalle. Reune los
    datos crudos del bloque + su ejercicio + (si tiene) el objetivo
    planeado + el delta contra ese objetivo."""

    id: int
    sesion_id: uuid.UUID
    orden: int
    series: int | None
    reps: int | None
    distancia_m: Decimal | None
    duracion_s: int | None
    calidad: int | None
    peso_kg: Decimal | None
    rpe: int | None
    dolor_lumbar: bool
    nota: str | None
    ejercicio: BloqueEjercicioEnDetalleRead
    objetivo: BloqueObjetivoRead | None
    delta: BloqueDeltaRead


class BloqueNoEjecutadoRead(ReadBase):
    """Bloques del plan que no se ejecutaron (SPEC §3.7). Solo el minimo
    necesario para identificarlos y mostrar el objetivo que se salteo."""

    orden: int
    ejercicio_id: int
    ejercicio_nombre: str
    objetivo: BloqueObjetivoRead


class MolestiaDetalleRead(ReadBase):
    """Subset de `MolestiaRead` para anidar en el detalle de sesion: el
    nombre de la zona (no el id) + intensidad. Sin `nota`, `fecha` ni
    `idempotency_key`: el detalle expone lo que se ve en el feed."""

    zona: str
    intensidad: int


class PlanCicloRead(ReadBase):
    """Ciclo + semana del plan anidado en `PlanDetalleEnSesionRead`.
    `numero` y `semana` son los identificadores humanos; `fase` es la
    clave para pintar la banda de carga."""

    numero: int
    objetivo: str
    semana: int
    fase: str


class PlanDetalleEnSesionRead(ReadBase):
    """Plan asociado a la sesion (R9). Forma exacta: lo que el SPEC §3.7
    describe en el campo `plan`."""

    id: int
    nombre: str | None
    objetivo: str | None
    nota: str | None
    duracion_min_est: int | None
    rpe_objetivo: int | None
    estado: str
    dia_sugerido: int | None
    ciclo: PlanCicloRead | None


class SesionDetalleRead(ReadBase):
    """El detalle completo de la sesion (SPEC §3.7)."""

    id: uuid.UUID
    usuario_id: uuid.UUID
    sesion_plan_id: int | None
    fecha: date
    tipo_sesion: SesionTipoRead
    duracion_min: int
    rpe: int
    nota: str | None
    carga_srpe: int
    registrado_en: datetime
    plan: PlanDetalleEnSesionRead | None
    delta: SesionDeltaRead | None
    bloques: list[BloqueDetalleRead] = Field(default_factory=list)
    bloques_no_ejecutados: list[BloqueNoEjecutadoRead] = Field(default_factory=list)
    molestias: list[MolestiaDetalleRead] = Field(default_factory=list)
