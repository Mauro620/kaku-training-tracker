"""Runner de seeds. Idempotente: correrlo dos veces deja lo mismo que una.

    make seed

Todo se escribe con `ON CONFLICT DO UPDATE` sobre la clave natural. Un seed que
falla al re-ejecutarse obliga a bajar la base para volver a sembrar, y eso
termina en alguien borrando datos reales.
"""

import asyncio
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.seguridad import hashear_password
from app.db.base import Base
from app.db.session import get_engine, get_sessionmaker
from app.models import (
    Alimento,
    AuthUsuario,
    Ejercicio,
    Habito,
    Parametro,
    TipoSesion,
    TipoTest,
    Usuario,
    ZonaCorporal,
)
from app.seeds.alimentos import ALIMENTOS, FUENTE
from app.seeds.catalogos import HABITOS, TIPOS_SESION, TIPOS_TEST, ZONAS_CORPORALES
from app.seeds.ejercicios import EJERCICIOS
from app.seeds.parametros import PARAMETROS

# Los valores semilla rigen "desde siempre". Una fecha fija los hace
# idempotentes: con CURRENT_DATE, re-sembrar mañana insertaría una segunda
# versión de cada parámetro en vez de actualizar la existente.
VIGENTE_DESDE_SEMILLA = date(2000, 1, 1)


async def _upsert(
    session: AsyncSession,
    modelo: type[Base],
    filas: list[dict[str, Any]],
    clave_natural: list[str],
) -> int:
    """Inserta o actualiza por clave natural. Devuelve cuántas filas tocó."""
    if not filas:
        return 0
    stmt = pg_insert(modelo).values(filas)
    a_actualizar = {
        col: getattr(stmt.excluded, col) for col in filas[0] if col not in clave_natural
    }
    # Una tabla cuya única columna ES la clave natural (zona_corporal) no tiene
    # nada que actualizar, y Postgres rechaza un SET vacío.
    await session.execute(
        stmt.on_conflict_do_update(index_elements=clave_natural, set_=a_actualizar)
        if a_actualizar
        else stmt.on_conflict_do_nothing(index_elements=clave_natural)
    )
    return len(filas)


async def _sembrar_usuario(session: AsyncSession, nombre: str) -> uuid.UUID:
    """El usuario único.

    Las credenciales son fase 2; acá solo el nombre, que es lo que necesitan las
    tablas con `usuario_id NOT NULL` para poder sembrarse.
    """
    existente = await session.scalar(select(Usuario).where(Usuario.nombre == nombre))
    if existente is not None:
        return existente.id

    usuario = Usuario(nombre=nombre)
    session.add(usuario)
    await session.flush()
    return usuario.id


async def sembrar(session: AsyncSession, nombre_usuario: str) -> dict[str, int]:
    settings = get_settings()
    if not settings.seed_usuario_email or not settings.seed_usuario_password:
        # Aborta antes de tocar la base: el api ya levanto con estas vars
        # vacias, pero el seed es quien crea la fila de AuthUsuario y sin
        # password no hay forma de loguearse.
        raise SystemExit(
            "SEED_USUARIO_EMAIL y SEED_USUARIO_PASSWORD son obligatorios para "
            "sembrar auth_usuario. Definilos en .env.local."
        )

    usuario_id = await _sembrar_usuario(session, nombre_usuario)
    password_hash = hashear_password(settings.seed_usuario_password)

    conteo = {
        "usuario": 1,
        "auth_usuario": await _upsert(
            session,
            AuthUsuario,
            [
                {
                    "usuario_id": usuario_id,
                    "email": settings.seed_usuario_email,
                    "password_hash": password_hash,
                }
            ],
            ["usuario_id"],
        ),
        "parametro": await _upsert(
            session,
            Parametro,
            [
                {
                    "clave": clave,
                    "valor": valor,
                    "unidad": unidad,
                    "descripcion": descripcion,
                    "vigente_desde": VIGENTE_DESDE_SEMILLA,
                }
                for clave, valor, unidad, descripcion in PARAMETROS
            ],
            ["clave", "vigente_desde"],
        ),
        "tipo_sesion": await _upsert(
            session,
            TipoSesion,
            [
                {"codigo": codigo, "nombre": nombre, "demanda": demanda}
                for codigo, nombre, demanda in TIPOS_SESION
            ],
            ["codigo"],
        ),
        "zona_corporal": await _upsert(
            session,
            ZonaCorporal,
            [{"nombre": nombre} for nombre in ZONAS_CORPORALES],
            ["nombre"],
        ),
        "tipo_test": await _upsert(
            session,
            TipoTest,
            [
                {
                    "codigo": codigo,
                    "nombre": nombre,
                    "unidad": unidad,
                    "mejor_es_mayor": mejor_es_mayor,
                }
                for codigo, nombre, unidad, mejor_es_mayor in TIPOS_TEST
            ],
            ["codigo"],
        ),
        "ejercicio": await _upsert(
            session,
            Ejercicio,
            [
                {"nombre": nombre, "patron": patron, "carga_lumbar": carga_lumbar}
                for nombre, patron, carga_lumbar in EJERCICIOS
            ],
            ["nombre"],
        ),
        "alimento": await _upsert(
            session,
            Alimento,
            [
                {
                    "nombre": nombre,
                    "grupo": grupo,
                    "kcal_100g": kcal,
                    "proteina_100g": proteina,
                    "carbo_100g": carbo,
                    "grasa_100g": grasa,
                    "fibra_100g": fibra,
                    "estado_pesaje": estado_pesaje,
                    "fuente": FUENTE,
                }
                for nombre, grupo, kcal, proteina, carbo, grasa, fibra, estado_pesaje in ALIMENTOS  # noqa: E501
            ],
            ["nombre"],
        ),
        "habito": await _upsert(
            session,
            Habito,
            [
                {"usuario_id": usuario_id, "nombre": nombre, "orden": orden}
                for orden, nombre in enumerate(HABITOS)
            ],
            ["usuario_id", "nombre"],
        ),
    }
    return conteo


async def main() -> None:
    settings = get_settings()
    async with get_sessionmaker()() as session:
        conteo = await sembrar(session, settings.seed_usuario_nombre)
        await session.commit()
    await get_engine().dispose()

    for tabla, filas in conteo.items():
        print(f"  {tabla:<16} {filas:>3}")
    print(f"  {'TOTAL':<16} {sum(conteo.values()):>3}")


if __name__ == "__main__":
    asyncio.run(main())
