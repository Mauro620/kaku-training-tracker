import uuid
from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    SmallInteger,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import BigIntPk, UsuarioFk

_ITEMS_HOOPER = ("sueno_pobre", "fatiga", "dolor_muscular", "estres")


class RegistroBienestar(Base):
    """Los cuatro ítems del índice de Hooper.

    Dirección: **1 es bueno, 5 es malo** en los cuatro. El campo se llama
    `sueno_pobre` y no `sueno_calidad` justamente para que el nombre apunte en
    la misma dirección que el valor: un campo llamado "calidad" donde 5 es la
    peor calidad es una inversión de signo esperando a pasar.

    La unicidad natural es `(usuario_id, fecha)`; `idempotency_key` es
    metadata para la cola de Fase 5. Nullable para admitir backfill
    historico (Fase 9, Notion).
    """

    __tablename__ = "registro_bienestar"
    __table_args__ = (
        UniqueConstraint("usuario_id", "fecha"),
        *(
            CheckConstraint(f"{item} BETWEEN 1 AND 5", name=f"{item}_rango")
            for item in _ITEMS_HOOPER
        ),
    )

    id: Mapped[BigIntPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    sueno_pobre: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fatiga: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    dolor_muscular: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    estres: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)

    # REGLAS_NEGOCIO §5: hooper = suma de los cuatro. Rango 4-20.
    hooper: Mapped[int] = mapped_column(
        SmallInteger, Computed(" + ".join(_ITEMS_HOOPER), persisted=True)
    )
