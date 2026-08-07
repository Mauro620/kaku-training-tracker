"""Schemas de Despensa (Fase 6, ROADMAP §6).

La despensa es el subset del catalogo de alimentos que el usuario lleva a
casa. La lista de mercado es: `imprescindible = true AND en_stock = false`.

No es un espejo completo de `alimento`: si un alimento no aparece en la
despensa del usuario, no se asume `en_stock = false` por default — solo
significa que el usuario no lo incluye.
"""

from pydantic import ConfigDict

from app.schemas.base import ReadBase, SchemaBase


class DespensaUpsert(SchemaBase):
    """PUT reemplaza el par (imprescindible, en_stock) para un alimento.
    Si el alimento no estaba en la despensa del usuario, se crea."""

    imprescindible: bool = False
    en_stock: bool = True


class DespensaRead(ReadBase):
    """Read no expone `usuario_id` (siempre es el autenticado) ni la PK
    compuesta. La UI lista por nombre de alimento."""

    model_config = ConfigDict(from_attributes=True)

    alimento_id: int
    alimento_nombre: str
    imprescindible: bool
    en_stock: bool


class DespensaListaDeMercadoRead(SchemaBase):
    """Vista especializada: solo lo que hay que comprar (imprescindible +
    sin stock). Se devuelve como una lista de items para que la UI no
    tenga que filtrar el DespensaRead."""

    items: list[DespensaRead]
