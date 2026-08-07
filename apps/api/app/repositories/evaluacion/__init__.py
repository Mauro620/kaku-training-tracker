from app.repositories.catalogo.tipo_test import listar as listar_tipos_test
from app.repositories.catalogo.tipo_test import (
    obtener_por_id as obtener_tipo_test_por_id,
)
from app.repositories.evaluacion import medida as _medida
from app.repositories.evaluacion import partido as _partido
from app.repositories.evaluacion import test_fisico as _test_fisico

crear_test_fisico = _test_fisico.crear
agregar_intentos = _test_fisico.agregar_intentos
contar_intentos = _test_fisico.contar_intentos
eliminar_intentos = _test_fisico.eliminar_intentos
obtener_test_fisico_por_id = _test_fisico.obtener_por_id
listar_tests_por_fecha = _test_fisico.listar_por_fecha
listar_tests_por_tipo = _test_fisico.listar_por_tipo
eliminar_test_fisico = _test_fisico.eliminar

upsert_medida = _medida.upsert
obtener_medida_por_fecha = _medida.obtener_por_fecha
obtener_medida_mas_reciente = _medida.obtener_mas_reciente
listar_medidas = _medida.listar

crear_partido = _partido.crear
obtener_partido_por_id = _partido.obtener_por_id
obtener_partido_por_sesion = _partido.obtener_por_sesion
listar_partidos = _partido.listar_por_usuario

__all__ = [
    "agregar_intentos",
    "contar_intentos",
    "crear_partido",
    "crear_test_fisico",
    "eliminar_intentos",
    "eliminar_test_fisico",
    "listar_medidas",
    "listar_partidos",
    "listar_tests_por_fecha",
    "listar_tests_por_tipo",
    "listar_tipos_test",
    "obtener_medida_mas_reciente",
    "obtener_medida_por_fecha",
    "obtener_partido_por_id",
    "obtener_partido_por_sesion",
    "obtener_test_fisico_por_id",
    "obtener_tipo_test_por_id",
    "upsert_medida",
]
