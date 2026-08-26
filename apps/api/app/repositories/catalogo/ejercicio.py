from datetime import date
from typing import Any, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bloque, Ejercicio, Sesion
from app.models.enums import CargaLumbar, TipoMedicion


async def listar(session: AsyncSession) -> list[Ejercicio]:
    resultado = await session.scalars(select(Ejercicio).order_by(Ejercicio.nombre))
    return list(resultado.all())


async def listar_por_ids(session: AsyncSession, ids: list[int]) -> list[Ejercicio]:
    if not ids:
        return []
    resultado = await session.scalars(select(Ejercicio).where(Ejercicio.id.in_(ids)))
    return list(resultado.all())


async def obtener_por_nombre(session: AsyncSession, nombre: str) -> Ejercicio | None:
    return cast(
        "Ejercicio | None",
        await session.scalar(select(Ejercicio).where(Ejercicio.nombre == nombre)),
    )


async def crear(
    session: AsyncSession,
    *,
    nombre: str,
    tipo_medicion: TipoMedicion,
    descripcion: str | None = None,
) -> Ejercicio:
    """Unico catalogo con creacion de usuario (REGLAS_NEGOCIO §15): el
    universo de ejercicios de una rutina real es abierto, a diferencia de
    tipo_sesion o zona_corporal. carga_lumbar/tipo_sesion_id quedan en su
    default (baja/NULL): el usuario no los declara al crear inline."""
    ejercicio = Ejercicio(
        nombre=nombre,
        tipo_medicion=tipo_medicion,
        carga_lumbar=CargaLumbar.baja,
        descripcion=descripcion,
    )
    session.add(ejercicio)
    await session.flush()
    return ejercicio


async def obtener_por_id(session: AsyncSession, ejercicio_id: int) -> Ejercicio | None:
    return cast(
        "Ejercicio | None",
        await session.scalar(select(Ejercicio).where(Ejercicio.id == ejercicio_id)),
    )


async def actualizar(
    session: AsyncSession,
    ejercicio: Ejercicio,
    *,
    nombre: str | None,
    descripcion: str | None,
) -> Ejercicio:
    """Solo nombre y descripcion. `tipo_medicion` NO se edita: cambiarlo
    invalidaria los bloques historicos, que se midieron con el anterior
    (REGLAS_NEGOCIO §15). None significa "no tocar", no "poner en NULL":
    para borrar la descripcion se manda string vacio."""
    if nombre is not None:
        ejercicio.nombre = nombre
    if descripcion is not None:
        ejercicio.descripcion = descripcion or None
    await session.flush()
    return ejercicio


# -------------------------------------------- R6 — Catálogo CRUD ----


async def listar_filtrado(
    session: AsyncSession,
    *,
    q: str | None,
    tipo_medicion: TipoMedicion | None,
    tipo_sesion_id: int | None,
    activo: bool,
    orden: Literal["nombre", "uso", "reciente"],
) -> tuple[list[tuple[Ejercicio, int, date | None]], int]:
    """Listado paginado del banco de ejercicios.

    Q1 (design #326): un solo SELECT con subquery agregada para `usos` y
    `ultima_vez`. La subquery cuenta filas de `bloque` y toma MAX(sesion.fecha)
    por `ejercicio_id`, así el frontend ve "usado 3 veces, ultima 2026-08-20"
    sin pedir una segunda llamada.

    Devuelve tuplas `(Ejercicio, usos, ultima_vez)` por item: el ORM no
    adjunta columnas agregadas como atributos, y acoplar el `Ejercicio` con
    metadatos que solo aplican al listado (no al detalle, no a un POST)
    ensucia el modelo. El service mapea a `EjercicioListItem`.

    El `q` ya viene normalizado desde el service (`normalizar_para_busqueda`):
    aca solo se hace `ILIKE` case-insensitive. La normalizacion de acentos
    se hace en el service porque Python puede pero Postgres requiere
    `unaccent` o `LOWER(translate(...))` para algo equivalente.

    `total` cuenta los matcheos totales sin LIMIT: si mas adelante se
    agrega paginacion, el caller ya tiene el numero para paginar.
    """
    # Subquery de uso: count de bloques + MAX de sesion.fecha por ejercicio.
    sub_uso = (
        select(
            Bloque.ejercicio_id.label("ejercicio_id"),
            func.count(Bloque.id).label("usos"),
            func.max(Sesion.fecha).label("ultima_vez"),
        )
        .join(Sesion, Sesion.id == Bloque.sesion_id)
        .group_by(Bloque.ejercicio_id)
        .subquery()
    )

    # Query principal: LEFT JOIN contra la subquery (ejercicios sin uso
    # quedan con usos=0 y ultima_vez=None, no excluidos).
    stmt = (
        select(
            Ejercicio,
            func.coalesce(sub_uso.c.usos, 0).label("usos"),
            sub_uso.c.ultima_vez,
        )
        .outerjoin(sub_uso, sub_uso.c.ejercicio_id == Ejercicio.id)
        .where(Ejercicio.activo == activo)
    )
    count_stmt = (
        select(func.count()).select_from(Ejercicio).where(Ejercicio.activo == activo)
    )

    if q is not None:
        # El `q` llega normalizado (sin acentos, lowercase) desde el service.
        # Postgres trae `ILIKE` pero NO es accent-insensitive por default.
        # Aplicamos `translate` para colapsar diacríticos en nombre y
        # descripción, así `q='elevacion'` matchea "Elevación" sin tener
        # que instalar la extensión `unaccent`.
        patron = _escapear_ilike(q)
        like = f"%{patron}%"
        nombre_norm = func.lower(_translate_sin_diacriticos(Ejercicio.nombre))
        descripcion_norm = func.lower(_translate_sin_diacriticos(Ejercicio.descripcion))
        filtro_q = nombre_norm.ilike(like, escape="\\") | descripcion_norm.ilike(
            like, escape="\\"
        )
        stmt = stmt.where(filtro_q)
        count_stmt = count_stmt.where(filtro_q)

    if tipo_medicion is not None:
        stmt = stmt.where(Ejercicio.tipo_medicion == tipo_medicion)
        count_stmt = count_stmt.where(Ejercicio.tipo_medicion == tipo_medicion)

    if tipo_sesion_id is not None:
        stmt = stmt.where(Ejercicio.tipo_sesion_id == tipo_sesion_id)
        count_stmt = count_stmt.where(Ejercicio.tipo_sesion_id == tipo_sesion_id)

    if orden == "nombre":
        stmt = stmt.order_by(Ejercicio.nombre)
    elif orden == "uso":
        # Mas usados primero; empates por nombre.
        stmt = stmt.order_by(func.coalesce(sub_uso.c.usos, 0).desc(), Ejercicio.nombre)
    else:  # "reciente"
        # Mas recientes primero; los sin uso quedan al final.
        stmt = stmt.order_by(sub_uso.c.ultima_vez.desc().nulls_last(), Ejercicio.nombre)

    filas = (await session.execute(stmt)).all()
    total = (await session.scalar(count_stmt)) or 0
    items: list[tuple[Ejercicio, int, date | None]] = [
        (fila[0], int(fila[1]), fila[2]) for fila in filas
    ]
    return items, int(total)


def _escapear_ilike(texto: str) -> str:
    """Escapa `%`, `_` y `\\` para que `ILIKE` los tome como literales.
    Sin esto, un usuario que busca `50%` matchearia cualquier cosa."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Mapeo de diacríticos a su base ASCII. Mantenido chico y conservador: solo
# los que aparecen en los seeds y nombres en español/inglés frecuentes.
_DIACRITICOS = "áéíóúÁÉÍÓÚñÑüÜ"
_BASES = "aeiouAEIOUnNuU"


def _translate_sin_diacriticos(columna: Any) -> Any:
    """`translate(col, 'áéíóú...', 'aeiou...')` para Postgres. Portatil: no
    requiere la extension `unaccent`, que no todos los Postgres traen."""
    return func.translate(columna, _DIACRITICOS, _BASES)


async def listar_historial(
    session: AsyncSession, ejercicio_id: int, *, limite: int
) -> list[Sesion]:
    """Ultimas `limite` sesiones que usaron el ejercicio. JOIN `bloque` con
    `sesion`, ORDER BY `sesion.fecha DESC, sesion.registrado_en DESC`. Dos
    sesiones del mismo dia se desempatan por cuando se cargaron (mismo
    criterio que `listar_ultimas` en sesion.py).

    Devuelve `Sesion` (no `Bloque`) porque la UI pinta una linea por sesion,
    no por bloque. El caller (service) hace el mapeo a `EjercicioHistorialItem`
    con los campos que quiere exponer (fecha, bloque_id, orden, series, etc).
    """
    bloque_sub = (
        select(Bloque.id, Bloque.sesion_id, Bloque.orden)
        .where(Bloque.ejercicio_id == ejercicio_id)
        .subquery()
    )
    resultado = await session.scalars(
        select(Sesion)
        .join(bloque_sub, bloque_sub.c.sesion_id == Sesion.id)
        .order_by(Sesion.fecha.desc(), Sesion.registrado_en.desc())
        .limit(limite)
    )
    return list(resultado.all())


async def listar_posibles_duplicados(
    session: AsyncSession, ejercicio: Ejercicio
) -> list[Ejercicio]:
    """Candidatos a duplicado: mismo `tipo_medicion`, distinto `id`, activos.

    El calculo de similitud se hace en Python (sobre los nombres) en el
    service, no aca: el umbral 0.75 es un corte arbitrario que pertenece a
    la capa de negocio.
    """
    resultado = await session.scalars(
        select(Ejercicio).where(
            Ejercicio.id != ejercicio.id,
            Ejercicio.tipo_medicion == ejercicio.tipo_medicion,
            Ejercicio.activo.is_(True),
        )
    )
    return list(resultado.all())


async def contar_usos(session: AsyncSession, ejercicio_id: int) -> int:
    """Cuenta filas de `bloque` para el ejercicio. NO cuenta `bloque_plan`:
    un ejercicio solo "usado" en planes (pero nunca ejecutado) tiene 0.

    El listado y el detalle usan `contar_usos` indirectamente via la
    subquery de `listar_filtrado`. Esta función queda para el caso
    `GET /ejercicios/{id}` cuando el cliente pide solo el conteo.
    """
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Bloque)
            .where(Bloque.ejercicio_id == ejercicio_id)
        )
        or 0
    )


async def archivar(session: AsyncSession, ejercicio: Ejercicio) -> None:
    """Soft delete: pone `activo = false`. La historia del usuario no se
    pierde porque `bloque.ejercicio_id` sigue apuntando al original
    (SPEC §2.3)."""
    ejercicio.activo = False
    await session.flush()
