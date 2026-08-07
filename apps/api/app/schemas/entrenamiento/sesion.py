import uuid
from datetime import date, datetime

from pydantic import Field

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
    sesion_plan_id: int | None = None
    tipo_sesion_id: int | None = None
    duracion_min: DuracionMin | None = None
    rpe: Rpe | None = None
    nota: str | None = None


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


# Resuelve las forward refs.
SesionCreate.model_rebuild()
SesionRead.model_rebuild()
