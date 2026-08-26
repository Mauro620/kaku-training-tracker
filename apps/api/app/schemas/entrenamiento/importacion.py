"""Contrato del JSON de importacion de plan semanal.

El formato lo define `docs/PLAN_IMPORT.md`, que es tambien el documento que
el usuario le pasa a un LLM para que genere el plan.
Cualquier cambio acá tiene que reflejarse allá: ese doc es el prompt.

Lo que se valida en este modulo es todo lo que se puede saber sin tocar la
base (forma, rangos, coherencia entre campos del propio JSON). Lo que necesita
el catalogo o el historico (que el `tipo` exista, que un ejercicio ya creado no
cambie de `tipo_medicion`) lo valida el service.
"""

from datetime import date
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.enums import FaseCiclo, TipoMedicion
from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import (
    DiaSemana,
    Distancia,
    DuracionMin,
    DuracionSeg,
    Peso,
    Positivo,
    Rpe,
)

VERSION_SOPORTADA = 2

# Los tres exports documentados en PLAN_IMPORT.md §9. `str` y no un `Enum`:
# un enum en el path param hace que FastAPI devuelva 422 ante un valor
# desconocido, y el spec exige 404 (ver design). El membership check en el
# router es todo el "registro" que este recurso necesita.
EXPORT_RECURSOS: frozenset[str] = frozenset({"ejercicios", "reglas", "ejemplo"})


class CicloImport(SchemaBase):
    """`numero` es la identidad del ciclo para el usuario (UNIQUE). Si ya
    existe, el resto de los campos se ignoran: un ciclo en curso no se
    redefine desde una importacion de una sola semana."""

    numero: Positivo
    objetivo: str
    fecha_inicio: date
    semanas: Positivo = 4


class RpeObjetivoImport(SchemaBase):
    min: Rpe
    max: Rpe

    @model_validator(mode="after")
    def _validar_orden(self) -> Self:
        if self.min > self.max:
            raise ValueError("rpe_objetivo.min no puede superar a rpe_objetivo.max")
        return self


class SemanaImport(SchemaBase):
    numero: Positivo
    fase: FaseCiclo
    rpe_objetivo: RpeObjetivoImport | None = None
    volumen_pct: Positivo = 100


class BloqueImport(SchemaBase):
    """`tipo_medicion` determina que campos acepta el bloque (PLAN_IMPORT.md 4).
    Mandar uno que no aplica es un error, no algo que se ignora en silencio."""

    ejercicio: str = Field(min_length=1, max_length=80)
    tipo_medicion: TipoMedicion
    # Solo se usa al CREAR el ejercicio. Si ya existe y difiere, se conserva
    # la del catalogo y se avisa (PLAN_IMPORT.md §4.1).
    descripcion: str | None = None
    series: Positivo | None = None
    # `reps` exacto es azucar de `reps_min == reps_max`: el esquema solo tiene
    # el rango, y un objetivo exacto es un rango de amplitud cero.
    reps: Positivo | None = None
    reps_min: Positivo | None = None
    reps_max: Positivo | None = None
    peso_kg: Peso | None = None
    distancia_m: Distancia | None = None
    duracion_s: DuracionSeg | None = None
    # DE ESTA VEZ, va a bloque_plan.nota (PLAN_IMPORT.md §2.4).
    nota: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _validar_reps(self) -> Self:
        if self.reps is not None and (
            self.reps_min is not None or self.reps_max is not None
        ):
            raise ValueError(
                f"{self.ejercicio}: usar `reps` o `reps_min`+`reps_max`, no ambos"
            )
        if (self.reps_min is None) != (self.reps_max is None):
            raise ValueError(
                f"{self.ejercicio}: `reps_min` y `reps_max` van juntos o ninguno"
            )
        if (
            self.reps_min is not None
            and self.reps_max is not None
            and self.reps_min > self.reps_max
        ):
            raise ValueError(f"{self.ejercicio}: reps_min no puede superar a reps_max")
        return self

    @property
    def rango_reps(self) -> tuple[int | None, int | None]:
        if self.reps is not None:
            return self.reps, self.reps
        return self.reps_min, self.reps_max


class SesionImport(SchemaBase):
    """`tipo` es el `codigo` de `tipo_sesion`, no su id: el JSON lo escribe
    una persona (o un LLM) y no puede conocer ids de la base."""

    dia: DiaSemana
    tipo: str = Field(min_length=1, max_length=30)
    # Etiqueta legible y contexto de la semana: cambian semana a semana y se
    # reemplazan al reimportar (PLAN_IMPORT.md §2.3).
    nombre: str | None = Field(default=None, max_length=60)
    nota: str | None = None
    objetivo: str | None = None
    duracion_min: DuracionMin | None = None
    rpe_objetivo: Rpe | None = None
    bloques: list[BloqueImport] = Field(default_factory=list)

    @property
    def clave_import(self) -> str:
        """Identidad de la sesion dentro de la semana. Reimportar reemplaza el
        plan de la misma clave en vez de duplicarlo (PLAN_IMPORT.md 2.2)."""
        return f"{self.dia}-{self.tipo}"


class PlanSemanalImport(SchemaBase):
    version: int
    ciclo: CicloImport
    semana: SemanaImport
    sesiones: list[SesionImport] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_coherencia(self) -> Self:
        if self.version != VERSION_SOPORTADA:
            raise ValueError(
                f"version {self.version} no soportada (esperada: {VERSION_SOPORTADA})"
            )
        if self.semana.numero > self.ciclo.semanas:
            raise ValueError(
                f"la semana {self.semana.numero} excede las "
                f"{self.ciclo.semanas} semanas del ciclo {self.ciclo.numero}"
            )
        claves = [s.clave_import for s in self.sesiones]
        duplicadas = sorted({c for c in claves if claves.count(c) > 1})
        if duplicadas:
            raise ValueError(
                "dos sesiones comparten dia y tipo en la misma semana: "
                + ", ".join(duplicadas)
            )
        return self


class ImportacionResultado(ReadBase):
    """Lo que devuelve el endpoint (PLAN_IMPORT.md 7).

    `advertencias` no bloquea: son cosas que el usuario probablemente quiera
    revisar, no razones para rechazar la semana entera.

    `ciclo_semana_inicio` / `ciclo_semana_fin` se calculan desde
    `ciclo.fecha_inicio` y `ciclo_semana.numero`: le devuelven al cliente el
    rango de fechas que la importacion efectivamente cubrio, para que el
    usuario sepa en que ventana cae lo que acaba de planificar (sin esto, una
    importacion de "semana 2" en un ciclo que arranca el lunes se ve
    visualmente igual a una de "semana 1" hasta que abris el detalle).
    """

    ciclo_id: int
    ciclo_semana_id: int
    ciclo_semana_inicio: date
    ciclo_semana_fin: date
    sesiones_creadas: int
    sesiones_reemplazadas: int
    sesiones_omitidas: int
    ejercicios_creados: list[str] = Field(default_factory=list)
    advertencias: list[str] = Field(default_factory=list)


class ExportRead(ReadBase):
    """Respuesta de `GET /planes/importar/export/{recurso}` (PLAN_IMPORT.md
    §9). `contenido` siempre es un string listo para pegar: JSON serializado
    para `ejercicios`/`ejemplo`, markdown para `reglas`."""

    recurso: str
    formato: Literal["json", "markdown"]
    contenido: str
