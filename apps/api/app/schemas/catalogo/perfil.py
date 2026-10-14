"""Schemas del perfil del atleta.

Las listas son JSONB en la base; su forma se valida acá. Las reglas que cruzan
campos (una ventana solo puede apuntar a lugares declarados, inicio < fin) se
validan en el schema porque no necesitan la base. El unico chequeo que la
necesita (que `tipo_sesion` exista en el catalogo) vive en el service.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.schemas.base import ReadBase, SchemaBase
from app.schemas.types import DiaSemana, DuracionMin

Hora = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
"""'HH:MM' en 24 h. Cero a la izquierda obligatorio: asi el orden
alfabetico es el orden cronologico."""

Texto = Annotated[str, Field(min_length=1, max_length=200)]


class EventoFijo(SchemaBase):
    dia: DiaSemana
    hora: Hora
    tipo_sesion: Annotated[str, Field(min_length=1, max_length=30)]
    nombre: Texto
    duracion_min: DuracionMin | None = None


class Ventana(SchemaBase):
    dia: DiaSemana
    inicio: Hora
    fin: Hora
    lugares: list[Texto] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_orden(self) -> Self:
        if self.inicio >= self.fin:
            raise ValueError(
                f"ventana del dia {self.dia}: inicio ({self.inicio}) debe ser "
                f"anterior a fin ({self.fin})"
            )
        return self


class Lugar(SchemaBase):
    nombre: Texto
    equipamiento: list[Texto] = Field(default_factory=list)


class PerfilBase(SchemaBase):
    posicion: Annotated[str, Field(min_length=1, max_length=60)]
    rol_tactico: Annotated[str, Field(min_length=1)]
    pie_dominante: Annotated[str, Field(min_length=1, max_length=60)]
    talla_cm: Annotated[Decimal, Field(gt=0, max_digits=4, decimal_places=1)] | None = (
        None
    )
    peso_kg: Annotated[Decimal, Field(gt=0, max_digits=5, decimal_places=2)] | None = (
        None
    )
    lesiones_activas: list[Texto] = Field(default_factory=list)
    objetivos: list[Texto] = Field(default_factory=list)
    eventos_fijos: list[EventoFijo] = Field(default_factory=list)
    ventanas: list[Ventana] = Field(default_factory=list)
    lugares: list[Lugar] = Field(default_factory=list)
    equipamiento_propio: list[Texto] = Field(default_factory=list)


class PerfilUpdate(PerfilBase):
    """PUT: reemplaza el perfil completo. Es un registro unico y siempre se
    edita entero en una pantalla; un PATCH parcial sobre listas anidadas
    seria ambiguo (¿se agrega o se reemplaza?)."""

    @model_validator(mode="after")
    def _validar_coherencia(self) -> Self:
        nombres = [lugar.nombre for lugar in self.lugares]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise ValueError("lugares repetidos: " + ", ".join(repetidos))
        conocidos = set(nombres)
        for ventana in self.ventanas:
            desconocidos = [n for n in ventana.lugares if n not in conocidos]
            if desconocidos:
                raise ValueError(
                    f"ventana del dia {ventana.dia}: lugar no declarado en "
                    f"`lugares`: " + ", ".join(desconocidos)
                )
        return self


class PerfilRead(PerfilBase, ReadBase):
    actualizado_en: datetime
