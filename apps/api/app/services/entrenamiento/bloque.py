"""Validación de campos de bloque por `ejercicio.tipo_medicion`
(REGLAS_NEGOCIO §15).

Un CHECK de Postgres no puede consultar otra tabla para saber qué campos
son válidos según el ejercicio elegido; por eso la validación vive acá, no
en el modelo.
"""

from app.core.exceptions import InvarianteDeNegocioError
from app.models.enums import TipoMedicion

CAMPOS_PERMITIDOS: dict[TipoMedicion, frozenset[str]] = {
    TipoMedicion.carga: frozenset({"series", "reps", "peso"}),
    TipoMedicion.distancia: frozenset({"reps", "distancia"}),
    TipoMedicion.tiempo: frozenset({"duracion"}),
    TipoMedicion.tecnica: frozenset({"reps", "duracion", "calidad"}),
}


def validar_campos(
    tipo_medicion: TipoMedicion,
    *,
    ejercicio_nombre: str,
    series: object | None = None,
    reps: object | None = None,
    peso: object | None = None,
    distancia: object | None = None,
    duracion: object | None = None,
    calidad: object | None = None,
) -> None:
    """rpe y dolor_lumbar no se validan: todo tipo_medicion los acepta."""
    permitidos = CAMPOS_PERMITIDOS[tipo_medicion]
    presentes = {
        "series": series,
        "reps": reps,
        "peso": peso,
        "distancia": distancia,
        "duracion": duracion,
        "calidad": calidad,
    }
    invalidos = sorted(
        campo
        for campo, valor in presentes.items()
        if valor is not None and campo not in permitidos
    )
    if invalidos:
        raise InvarianteDeNegocioError(
            f"{ejercicio_nombre} es de tipo_medicion={tipo_medicion.value}: "
            f"no acepta {', '.join(invalidos)}."
        )
