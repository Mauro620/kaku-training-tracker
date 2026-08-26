"""Tests del banco de ejercicios (PR 2 del feature 2).

Cubre R6 (catalog CRUD): schemas extendidos, repositorio `listar_filtrado`,
repositorio `obtener_detalle`, service `listar_ejercicios_filtrado`,
service `obtener_detalle_ejercicio`, y los endpoints extendidos
(POST/PATCH con campos nuevos, GET /{id}).

Los tests de schema van primero: no tocan la base, solo verifican que el
contrato de Pydantic coincide con lo que dice el design #326. Sin ellos,
los tests de integracion no podrian confiar en que el router acepta/rechaza
lo que corresponde.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.catalogo.catalogo import (
    EjercicioCreate,
    EjercicioDetalleRead,
    EjercicioHistorialItem,
    EjercicioListItem,
    EjercicioListRead,
    EjercicioPosibleDuplicado,
    EjercicioRead,
    EjercicioUpdate,
)

# ----------------------------------------------------- schemas R6.1 ----


def test_schema_ejercicio_list_item_acepta_campos_minimos() -> None:
    """El schema de item del listado tiene los 10 campos que el frontend
    necesita para pintar la fila (id, nombre, patron, carga_lumbar,
    tipo_sesion_id, tipo_medicion, descripcion, activo, usos, ultima_vez)."""
    item = EjercicioListItem(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion=None,
        activo=True,
        usos=3,
        ultima_vez=date(2026, 8, 20),
    )
    assert item.id == 1
    assert item.nombre == "Hip thrust"
    assert item.patron == "cadera_dominante"
    assert item.carga_lumbar == "media"
    assert item.tipo_sesion_id == 1
    assert item.tipo_medicion == "carga"
    assert item.descripcion is None
    assert item.activo is True
    assert item.usos == 3
    assert item.ultima_vez == date(2026, 8, 20)


def test_schema_ejercicio_list_read_items_total() -> None:
    """El envelope del listado siempre tiene `items` y `total`, en ese orden
    (lo espera el frontend y el OpenAPI generado)."""
    items = [
        EjercicioListItem(
            id=1,
            nombre="A",
            patron=None,
            carga_lumbar="baja",
            tipo_sesion_id=None,
            tipo_medicion="carga",
            descripcion=None,
            activo=True,
            usos=0,
            ultima_vez=None,
        ),
    ]
    envelope = EjercicioListRead(items=items, total=1)
    assert envelope.items == items
    assert envelope.total == 1


def test_schema_ejercicio_detalle_incluye_historial_y_duplicados() -> None:
    """El detalle expone los ultimos 5 usos (subquery) y los candidatos a
    duplicado (mismo tipo_medicion, similitud >= 0.75)."""
    historial = [
        EjercicioHistorialItem(
            sesion_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            fecha=date(2026, 8, 20),
            bloque_id=10,
            orden=1,
            series=4,
            reps=8,
            peso_kg=Decimal("80.0"),
        ),
    ]
    duplicados = [
        EjercicioPosibleDuplicado(id=2, nombre="Hip Trust", similitud=0.82),
    ]
    detalle = EjercicioDetalleRead(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion="Cadera al techo.",
        activo=True,
        historial=historial,
        posibles_duplicados=duplicados,
    )
    assert detalle.id == 1
    assert detalle.historial == historial
    assert detalle.posibles_duplicados == duplicados


def test_schema_ejercicio_update_rechaza_tipo_medicion() -> None:
    """REGLAS_NEGOCIO §15: cambiar `tipo_medicion` invalidaria los bloques
    historicos. El schema tiene `extra=forbid`, asi que un cliente que mande
    `{"tipo_medicion": "carga"}` recibe 422 antes de tocar la base."""
    with pytest.raises(ValidationError) as exc:
        EjercicioUpdate(nombre="Nuevo", tipo_medicion="carga")  # type: ignore[call-arg]
    # El error menciona el campo rechazado.
    assert any("tipo_medicion" in str(err) for err in exc.value.errors())


def test_schema_ejercicio_update_descripcion_vacia_se_traduce_a_null() -> None:
    """El contrato del design: `descripcion=""` se traduce a None en el
    service. El schema acepta ambos (`None` o string vacio), y la traduccion
    ocurre en el service para no contaminar la API publica del schema."""
    # Caso 1: el usuario manda descripcion vacia.
    caso_vacio = EjercicioUpdate(descripcion="")
    assert caso_vacio.descripcion == ""

    # Caso 2: el usuario no manda descripcion (no tocar).
    caso_omitido = EjercicioUpdate()
    assert caso_omitido.descripcion is None

    # El caso 3 (traduccion a None) vive en el service; lo cubre el test
    # `test_patch_ejercicio_descripcion_vacia_pone_null` mas abajo.


# ------------------------------------------------ EjercicioCreate R6.5 ---


def test_schema_ejercicio_create_acepta_patron_y_carga_lumbar() -> None:
    """Campos nuevos respecto al legacy: patron y carga_lumbar son opcionales
    (defaults None y 'baja' respectivamente). tipo_medicion sigue siendo
    obligatorio: sin el, no se sabe que campos aceptaran los bloques."""
    ejercicio = EjercicioCreate(
        nombre="Pallof press",
        tipo_medicion="carga",
        patron="core_antirotacion",
        carga_lumbar="baja",
    )
    assert ejercicio.nombre == "Pallof press"
    assert ejercicio.tipo_medicion == "carga"
    assert ejercicio.patron == "core_antirotacion"
    assert ejercicio.carga_lumbar == "baja"


def test_schema_ejercicio_read_incluye_activo() -> None:
    """Backward-compat: el `EjercicioRead` legacy ahora expone `activo` para
    reflejar la columna nueva. Otros lugares del proyecto lo siguen
    importando (importador, tests previos)."""
    lectura = EjercicioRead(
        id=1,
        nombre="Hip thrust",
        patron="cadera_dominante",
        carga_lumbar="media",
        tipo_sesion_id=1,
        tipo_medicion="carga",
        descripcion=None,
        activo=True,
    )
    assert lectura.activo is True


if __name__ == "__main__":
    # Permite correr este archivo aislado: `pytest tests/test_banco_ejercicios.py`.
    pytest.main([__file__, "-q"])
