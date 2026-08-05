import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import BigIntPk, IdempotencyKey, UsuarioFk, UuidPk


class TestFisico(Base):
    """`superficie` y `condiciones` no son decorativos: comparar un sprint en
    pista contra uno en grama es comparar cosas distintas.

    El índice `(usuario_id, tipo_test_id, fecha)` NO es único a propósito: se
    puede repetir un test el mismo día. Por eso hace falta `idempotency_key`
    para que la cola de sync no duplique.
    """

    __tablename__ = "test_fisico"
    __table_args__ = (
        Index(
            "ix_test_fisico_usuario_id_tipo_test_id_fecha",
            "usuario_id",
            "tipo_test_id",
            "fecha",
        ),
    )

    id: Mapped[UuidPk]
    usuario_id: Mapped[UsuarioFk]
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_test_id: Mapped[int] = mapped_column(
        ForeignKey("tipo_test.id"), nullable=False
    )
    superficie: Mapped[str | None] = mapped_column(String(40))
    condiciones: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[IdempotencyKey]

    intentos: Mapped[list["TestIntento"]] = relationship(
        back_populates="test_fisico", order_by="TestIntento.numero"
    )


class TestIntento(Base):
    """Un modelo para todos los tests: RSA son 6 intentos, CMJ es el mejor de
    3, Yo-Yo es 1.

    Mejor, media y % de decremento se calculan en el mart, no se almacenan. En
    Yo-Yo IR1 `valor` es la distancia; el nivel se deriva de la distancia con
    la tabla del protocolo, no se captura.
    """

    __tablename__ = "test_intento"
    __table_args__ = (
        UniqueConstraint("test_fisico_id", "numero"),
        CheckConstraint("numero > 0", name="numero_positivo"),
        CheckConstraint("valor > 0", name="valor_positivo"),
    )

    id: Mapped[BigIntPk]
    test_fisico_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_fisico.id"), nullable=False
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)

    test_fisico: Mapped[TestFisico] = relationship(back_populates="intentos")
