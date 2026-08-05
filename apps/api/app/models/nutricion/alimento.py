from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import EstadoPesaje, GrupoAlimento
from app.models.types import IntPk, Macro, UsuarioFk

_MACROS = ("kcal_100g", "proteina_100g", "carbo_100g", "grasa_100g")


class Alimento(Base):
    """Todos los macros por 100 g. Universo cerrado (~40 alimentos).

    Convención del proyecto: todo se almacena en CRUDO. Mezclar crudo y cocido
    introduce un error cercano al 30% en carnes. Si una fuente da un valor
    cocido, se convierte antes de sembrarlo.

    `grupo` es lo que permite calcular `pct_comidas_con_vegetal`: cuenta
    `grupo = verdura`, no fruta ni tubérculo ni leguminosa.
    """

    __tablename__ = "alimento"
    __table_args__ = tuple(
        CheckConstraint(f"{macro} >= 0", name=f"{macro}_no_negativo")
        for macro in (*_MACROS, "fibra_100g")
    )

    id: Mapped[IntPk]
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    grupo: Mapped[GrupoAlimento] = mapped_column(
        Enum(GrupoAlimento, name="grupo_alimento"), nullable=False
    )
    estado_pesaje: Mapped[EstadoPesaje] = mapped_column(
        Enum(EstadoPesaje, name="estado_pesaje"),
        nullable=False,
        server_default=EstadoPesaje.crudo.value,
    )
    kcal_100g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    proteina_100g: Mapped[Macro] = mapped_column(nullable=False)
    carbo_100g: Mapped[Macro] = mapped_column(nullable=False)
    grasa_100g: Mapped[Macro] = mapped_column(nullable=False)
    fibra_100g: Mapped[Macro | None]
    fuente: Mapped[str | None] = mapped_column(String(60))


class Despensa(Base):
    """La lista de mercado es: `imprescindible = true AND en_stock = false`."""

    __tablename__ = "despensa"

    usuario_id: Mapped[UsuarioFk] = mapped_column(primary_key=True)
    alimento_id: Mapped[int] = mapped_column(
        ForeignKey("alimento.id"), primary_key=True
    )
    imprescindible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    en_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
