import uuid
from datetime import date, datetime

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import DuracionMin, NoNegativo, Peso, Positivo, Rpe


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


class SerieCreate(SchemaBase):
    sesion_id: uuid.UUID
    ejercicio_id: int
    orden: NoNegativo
    series: Positivo
    reps: Positivo
    peso_kg: Peso | None = None
    rpe: Rpe | None = None
    dolor_lumbar: bool = False


class SerieUpdate(SchemaBase):
    ejercicio_id: int | None = None
    orden: NoNegativo | None = None
    series: Positivo | None = None
    reps: Positivo | None = None
    peso_kg: Peso | None = None
    rpe: Rpe | None = None
    dolor_lumbar: bool | None = None


class SerieRead(ReadBase):
    id: int
    sesion_id: uuid.UUID
    ejercicio_id: int
    orden: int
    series: int
    reps: int
    peso_kg: Peso | None
    rpe: int | None
    dolor_lumbar: bool
