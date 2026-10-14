"""Perfil del atleta: lo que un planificador (humano o LLM) necesita saber de
la persona para armar una semana. Un registro por usuario."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import Peso


class PerfilAtleta(Base):
    """Las listas (lesiones, objetivos, eventos fijos, ventanas, lugares) son
    JSONB y no tablas hijas: se leen y se escriben siempre completas, no se
    consultan por separado y el export para el LLM es el mismo JSON. La forma
    de cada elemento la valida Pydantic (`schemas/catalogo/perfil.py`); la
    base solo garantiza que cada columna sea un arreglo.

    `peso_kg` es el peso DECLARADO y es independiente de `medida_corporal`
    (que es el peso medido). Son dos hechos distintos y no se sincronizan.
    """

    __tablename__ = "perfil_atleta"
    __table_args__ = (
        CheckConstraint("talla_cm IS NULL OR talla_cm > 0", name="talla_cm_positiva"),
        CheckConstraint("peso_kg IS NULL OR peso_kg > 0", name="peso_kg_positivo"),
        *(
            CheckConstraint(f"jsonb_typeof({col}) = 'array'", name=f"{col}_es_arreglo")
            for col in (
                "lesiones_activas",
                "objetivos",
                "eventos_fijos",
                "ventanas",
                "lugares",
                "equipamiento_propio",
            )
        ),
    )

    # PK = FK: un perfil por usuario, igual que auth_usuario.
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuario.id"), primary_key=True
    )
    posicion: Mapped[str] = mapped_column(String(60), nullable=False)
    rol_tactico: Mapped[str] = mapped_column(Text, nullable=False)
    # Texto y no enum: incluye matices ("derecho, trabajando la zurda").
    pie_dominante: Mapped[str] = mapped_column(String(60), nullable=False)
    talla_cm: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    peso_kg: Mapped[Peso | None]
    lesiones_activas: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # En orden de prioridad: el primero es el mas importante.
    objetivos: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    eventos_fijos: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    ventanas: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    lugares: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    # Lo que el atleta lleva consigo y por tanto esta en CUALQUIER ventana
    # (conos, balon, bandas...), a diferencia del equipamiento de un lugar.
    equipamiento_propio: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
