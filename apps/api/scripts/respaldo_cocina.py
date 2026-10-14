"""Respaldo en JSON de las tablas de Cocina, previo a eliminarlas.

    uv run --directory apps/api python -m scripts.respaldo_cocina [ruta.json]

Opcional: la migracion de Cocina ya no lo exige. Solo lee. Usa SQL directo y
no los modelos porque los modelos de nutricion ya
no existen en el codigo. Incluye el parametro `proteina_g_por_kg`, que la
migracion tambien elimina. Sin argumento escribe en `respaldos/`, que esta
ignorado por git.
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db.session import get_engine

# Padres primero: el orden del archivo es el de una restauracion.
TABLAS = (
    "alimento",
    "receta",
    "receta_item",
    "despensa",
    "comida_log",
    "comida_item",
)


async def exportar() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    async with get_engine().connect() as conn:
        for tabla in TABLAS:
            filas = (
                await conn.execute(text(f"SELECT * FROM {tabla} ORDER BY 1"))
            ).mappings()
            out[tabla] = [dict(f) for f in filas]
        parametro = (
            await conn.execute(
                text("SELECT * FROM parametro WHERE clave = 'proteina_g_por_kg'")
            )
        ).mappings()
        out["parametro:proteina_g_por_kg"] = [dict(f) for f in parametro]
    await get_engine().dispose()
    return out


async def main(destino: Path) -> None:
    datos = await exportar()
    destino.parent.mkdir(parents=True, exist_ok=True)
    # default=str: Decimal, UUID y date no son JSON nativo.
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str))
    for tabla, filas in datos.items():
        print(f"  {tabla:<32} {len(filas):>5} filas")
    print(f"Respaldo escrito en {destino}")


if __name__ == "__main__":
    ruta = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("respaldos") / f"cocina_{date.today().isoformat()}.json"
    )
    asyncio.run(main(ruta))
