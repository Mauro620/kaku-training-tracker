"""Lectura de catálogos de entrenamiento. Sin reglas de negocio: el usuario
no crea valores, solo lee. El service existe igual para que el router nunca
importe el repositorio directo (ARCHITECTURE.md §2).

`ejercicio` es la excepción (REGLAS_NEGOCIO §15): el único catálogo que el
usuario puede ampliar, porque el universo de ejercicios de una rutina real
es abierto.
"""

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictoDeNegocioError, RecursoNoEncontradoError
from app.core.normalizacion import normalizar_para_busqueda
from app.core.similitud import _similitud_normalizada
from app.models import Bloque, Ejercicio, Sesion, TipoSesion, TipoTest, ZonaCorporal
from app.models.enums import TipoMedicion
from app.repositories.catalogo import ejercicio as repo_ejercicio
from app.repositories.catalogo import tipo_sesion as repo_tipo_sesion
from app.repositories.catalogo import tipo_test as repo_tipo_test
from app.repositories.catalogo import zona_corporal as repo_zona_corporal
from app.schemas.catalogo.catalogo import (
    EjercicioDetalleRead,
    EjercicioHistorialItem,
    EjercicioListItem,
    EjercicioListRead,
    EjercicioPosibleDuplicado,
)


async def listar_tipos_sesion(session: AsyncSession) -> list[TipoSesion]:
    return await repo_tipo_sesion.listar(session)


async def listar_ejercicios(session: AsyncSession) -> list[Ejercicio]:
    """Legacy: lista plana sin filtros. Mantenido por compatibilidad con
    callers que ya lo importan (el importador de planes lo usa para
    serializar el catalogo completo en /planes/importar/export)."""
    return await repo_ejercicio.listar(session)


async def listar_ejercicios_filtrado(
    session: AsyncSession,
    *,
    q: str | None,
    tipo_medicion: TipoMedicion | None,
    tipo_sesion_id: int | None,
    activo: bool,
    orden: Literal["nombre", "uso", "reciente"],
) -> EjercicioListRead:
    """Listado del banco con busqueda, filtros y orden.

    `q` se normaliza aca (no en el router): el repo recibe el termino ya
    limpio de acentos y case, y hace `ILIKE` con `translate` para acentos
    en la columna (Postgres no trae `unaccent` por default).
    """
    q_normalizado = normalizar_para_busqueda(q) if q else None
    # Si `q` es solo espacios o se normaliza a string vacio, lo tratamos
    # como None: no tiene sentido pasar `ILIKE '%%'` que matchea todo.
    if q_normalizado == "":
        q_normalizado = None
    filas, total = await repo_ejercicio.listar_filtrado(
        session,
        q=q_normalizado,
        tipo_medicion=tipo_medicion,
        tipo_sesion_id=tipo_sesion_id,
        activo=activo,
        orden=orden,
    )
    items = [
        EjercicioListItem(
            id=ejercicio.id,
            nombre=ejercicio.nombre,
            patron=ejercicio.patron,
            carga_lumbar=ejercicio.carga_lumbar,
            tipo_sesion_id=ejercicio.tipo_sesion_id,
            tipo_medicion=ejercicio.tipo_medicion,
            descripcion=ejercicio.descripcion,
            activo=ejercicio.activo,
            usos=usos,
            ultima_vez=ultima_vez,
        )
        for ejercicio, usos, ultima_vez in filas
    ]
    return EjercicioListRead(items=items, total=total)


async def obtener_detalle_ejercicio(
    session: AsyncSession, ejercicio_id: int
) -> EjercicioDetalleRead:
    """Detalle completo: datos + historial top 5 + candidatos a duplicado.

    La similitud se calcula en Python sobre los nombres: el umbral 0.75 es
    decision de negocio, no del repo (design #326).
    """
    ejercicio = await repo_ejercicio.obtener_por_id(session, ejercicio_id)
    if ejercicio is None:
        raise RecursoNoEncontradoError(f"ejercicio {ejercicio_id} no encontrado")

    # Historial: top 5 sesiones que usaron el ejercicio.
    sesiones = await repo_ejercicio.listar_historial(session, ejercicio_id, limite=5)
    historial = await _mapear_historial(session, ejercicio_id, sesiones)

    # Candidatos a duplicado: mismo tipo_medicion, id != self, activo.
    candidatos = await repo_ejercicio.listar_posibles_duplicados(session, ejercicio)
    duplicados: list[EjercicioPosibleDuplicado] = []
    for candidato in candidatos:
        similitud = _similitud_normalizada(candidato.nombre, ejercicio.nombre)
        if similitud >= 0.75:
            duplicados.append(
                EjercicioPosibleDuplicado(
                    id=candidato.id,
                    nombre=candidato.nombre,
                    similitud=similitud,
                )
            )
    # Orden por similitud descendente para que el mas probable salga primero.
    duplicados.sort(key=lambda d: d.similitud, reverse=True)

    return EjercicioDetalleRead(
        id=ejercicio.id,
        nombre=ejercicio.nombre,
        patron=ejercicio.patron,
        carga_lumbar=ejercicio.carga_lumbar,
        tipo_sesion_id=ejercicio.tipo_sesion_id,
        tipo_medicion=ejercicio.tipo_medicion,
        descripcion=ejercicio.descripcion,
        activo=ejercicio.activo,
        historial=historial,
        posibles_duplicados=duplicados,
    )


async def _mapear_historial(
    session: AsyncSession,
    ejercicio_id: int,
    sesiones: list[Sesion],
) -> list[EjercicioHistorialItem]:
    """Para cada sesion del top, agarra el bloque concreto del ejercicio y
    mapea a `EjercicioHistorialItem`.

    `listar_historial` devuelve sesiones, pero el schema pide campos del
    bloque (orden, series, reps, peso_kg). Hacemos el fetch de los bloques
    en una sola query y construimos el dict `sesion_id -> Bloque`.
    """
    from sqlalchemy import select

    if not sesiones:
        return []
    sesion_ids = [s.id for s in sesiones]
    bloques = (
        await session.scalars(
            select(Bloque).where(
                Bloque.ejercicio_id == ejercicio_id,
                Bloque.sesion_id.in_(sesion_ids),
            )
        )
    ).all()
    # Si el ejercicio aparece mas de una vez en la misma sesion (varias
    # bloques), nos quedamos con el primero por `orden`. La UI muestra una
    # linea por sesion, no por bloque.
    por_sesion: dict[Any, Bloque] = {}
    for bloque in bloques:
        if bloque.sesion_id not in por_sesion:
            por_sesion[bloque.sesion_id] = bloque

    resultado: list[EjercicioHistorialItem] = []
    for sesion in sesiones:
        encontrado: Bloque | None = por_sesion.get(sesion.id)
        if encontrado is None:
            # La sesion existe pero por algun motivo no tiene bloque de este
            # ejercicio (no deberia pasar: el JOIN lo filtra). Saltamos.
            continue
        bloque = encontrado
        resultado.append(
            EjercicioHistorialItem(
                sesion_id=sesion.id,
                fecha=sesion.fecha,
                bloque_id=bloque.id,
                orden=bloque.orden,
                series=bloque.series,
                reps=bloque.reps,
                peso_kg=bloque.peso_kg,
            )
        )
    return resultado


async def crear_ejercicio(
    session: AsyncSession,
    payload: dict[str, Any],
) -> Ejercicio:
    """Crear ejercicio. El dict viene del router via
    `payload.model_dump(exclude_unset=True)`.

    Valida duplicado de nombre normalizado: `Pallof Press` y `Pallof press`
    chocan porque la unicidad del schema es por nombre exacto. La
    normalizacion para busqueda no es la misma que para indice (preserva
    parentesis); usamos la misma que la busqueda para que `?q=pallof press`
    y un POST con `Pallof Press` sean consistentes.
    """
    nombre = payload["nombre"]
    nombre_normalizado = normalizar_para_busqueda(nombre)
    existente = await _buscar_por_nombre_normalizado(session, nombre_normalizado)
    if existente is not None:
        raise ConflictoDeNegocioError(
            f"ya existe un ejercicio llamado '{existente.nombre}'"
        )

    ejercicio = await repo_ejercicio.crear(
        session,
        nombre=nombre,
        tipo_medicion=payload["tipo_medicion"],
        descripcion=payload.get("descripcion"),
    )
    # Campos opcionales nuevos (R6): patron y carga_lumbar. Si vienen en
    # el payload, los pisamos despues del flush. Si no, quedan en su default.
    if "patron" in payload and payload["patron"] is not None:
        ejercicio.patron = payload["patron"]
    if "carga_lumbar" in payload and payload["carga_lumbar"] is not None:
        ejercicio.carga_lumbar = payload["carga_lumbar"]
    await session.commit()
    await session.refresh(ejercicio)
    return ejercicio


async def actualizar_ejercicio(
    session: AsyncSession,
    ejercicio_id: int,
    payload: dict[str, Any],
) -> Ejercicio:
    """Editar ejercicio. `payload` viene del router via
    `model_dump(exclude_unset=True)`: solo los campos que el cliente mando.

    Validaciones:
    - Si `nombre` cambia, no choca con otro activo normalizado (409).
    - `descripcion=""` se traduce a None (Pydantic acepta ambos, el contrato
      publico del schema no se toca).
    - `tipo_medicion` no llega aca (Pydantic `extra=forbid` en el Update).
    """
    ejercicio = await repo_ejercicio.obtener_por_id(session, ejercicio_id)
    if ejercicio is None:
        raise RecursoNoEncontradoError(f"ejercicio {ejercicio_id} no encontrado")

    if "nombre" in payload and payload["nombre"] != ejercicio.nombre:
        nombre_normalizado = normalizar_para_busqueda(payload["nombre"])
        choque = await _buscar_por_nombre_normalizado(session, nombre_normalizado)
        if choque is not None and choque.id != ejercicio.id:
            raise ConflictoDeNegocioError(
                f"ya existe un ejercicio llamado '{choque.nombre}'"
            )
        ejercicio.nombre = payload["nombre"]

    if "descripcion" in payload:
        # String vacio se traduce a None: el usuario quiere borrar.
        ejercicio.descripcion = payload["descripcion"] or None

    if "patron" in payload:
        ejercicio.patron = payload["patron"]

    if "carga_lumbar" in payload and payload["carga_lumbar"] is not None:
        ejercicio.carga_lumbar = payload["carga_lumbar"]

    if "activo" in payload and payload["activo"] is not None:
        ejercicio.activo = payload["activo"]

    await session.commit()
    await session.refresh(ejercicio)
    return ejercicio


async def _buscar_por_nombre_normalizado(
    session: AsyncSession, nombre_normalizado: str
) -> Ejercicio | None:
    """Busca un ejercicio cuyo nombre normalizado coincida con el termino.

    La unicidad del schema (`ejercicio.nombre UNIQUE`) es por nombre exacto;
    nosotros queremos ignorar acentos y mayusculas para que el usuario no
    pueda meter un duplicado en otra escritura. La query trae todos los
    activos y compara en Python (la cardinalidad es baja).
    """
    from sqlalchemy import select

    activos = (
        await session.scalars(select(Ejercicio).where(Ejercicio.activo.is_(True)))
    ).all()
    for candidato in activos:
        if normalizar_para_busqueda(candidato.nombre) == nombre_normalizado:
            return candidato
    return None


async def listar_zonas_corporales(session: AsyncSession) -> list[ZonaCorporal]:
    return await repo_zona_corporal.listar(session)


async def listar_tipos_test(session: AsyncSession) -> list[TipoTest]:
    return await repo_tipo_test.listar(session)
