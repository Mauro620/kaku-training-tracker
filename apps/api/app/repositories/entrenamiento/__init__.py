from app.repositories.catalogo.ejercicio import crear as crear_ejercicio
from app.repositories.catalogo.ejercicio import listar as listar_ejercicios
from app.repositories.catalogo.ejercicio import (
    listar_por_ids as listar_ejercicios_por_ids,
)
from app.repositories.catalogo.tipo_sesion import listar as listar_tipos_sesion
from app.repositories.catalogo.zona_corporal import listar as listar_zonas_corporales
from app.repositories.entrenamiento import ciclo as _ciclo
from app.repositories.entrenamiento import ciclo_semana as _ciclo_semana
from app.repositories.entrenamiento import composicion as _composicion
from app.repositories.entrenamiento import plan as _plan
from app.repositories.entrenamiento.bloque import crear as crear_bloque
from app.repositories.entrenamiento.bloque import (
    eliminar_por_sesion as eliminar_bloques_de_sesion,
)
from app.repositories.entrenamiento.bloque_plan import crear as crear_bloque_plan
from app.repositories.entrenamiento.bloque_plan import (
    eliminar_por_sesion_plan as eliminar_bloques_de_plan,
)
from app.repositories.entrenamiento.sesion import (
    actualizar as actualizar_sesion,
)
from app.repositories.entrenamiento.sesion import (
    contar_por_tipo_en_rango as contar_sesiones_por_tipo_en_rango,
)
from app.repositories.entrenamiento.sesion import (
    crear as crear_sesion,
)
from app.repositories.entrenamiento.sesion import (
    desvincular_de_plan as desvincular_sesiones_de_plan,
)
from app.repositories.entrenamiento.sesion import (
    eliminar as eliminar_sesion,
)
from app.repositories.entrenamiento.sesion import (
    listar_fechas_de_demanda_en_rango,
    listar_fechas_por_tipo_en_rango,
)
from app.repositories.entrenamiento.sesion import (
    listar_por_fecha as listar_sesiones_por_fecha,
)
from app.repositories.entrenamiento.sesion import (
    obtener_por_id as obtener_sesion_por_id,
)

crear_ciclo = _ciclo.crear
obtener_ciclo_por_id = _ciclo.obtener_por_id
listar_ciclos_por_usuario = _ciclo.listar_por_usuario
cerrar_ciclo = _ciclo.cerrar

crear_ciclo_semana = _ciclo_semana.crear
obtener_ciclo_semana_por_id = _ciclo_semana.obtener_por_id
listar_ciclo_semanas_por_ciclo = _ciclo_semana.listar_por_ciclo
actualizar_ciclo_semana = _ciclo_semana.actualizar
eliminar_ciclo_semana = _ciclo_semana.eliminar

reemplazar_composicion = _composicion.reemplazar
listar_composicion_por_semana = _composicion.listar_por_semana
eliminar_composicion_de_semana = _composicion.eliminar_por_semana

crear_sesion_plan = _plan.crear
obtener_sesion_plan_por_id = _plan.obtener_por_id
listar_planes_por_ciclo_y_tipos = _plan.listar_por_ciclo_y_tipos
listar_planes_candidatos_de_fecha = _plan.listar_candidatos_de_fecha
listar_planes_por_ciclo_semana = _plan.listar_por_ciclo_semana
eliminar_sesion_plan = _plan.eliminar

__all__ = [
    "actualizar_ciclo_semana",
    "actualizar_sesion",
    "cerrar_ciclo",
    "contar_sesiones_por_tipo_en_rango",
    "crear_bloque",
    "crear_bloque_plan",
    "crear_ciclo",
    "crear_ciclo_semana",
    "crear_ejercicio",
    "crear_sesion",
    "crear_sesion_plan",
    "desvincular_sesiones_de_plan",
    "eliminar_bloques_de_plan",
    "eliminar_bloques_de_sesion",
    "eliminar_ciclo_semana",
    "eliminar_composicion_de_semana",
    "eliminar_sesion",
    "eliminar_sesion_plan",
    "listar_ciclo_semanas_por_ciclo",
    "listar_ciclos_por_usuario",
    "listar_composicion_por_semana",
    "listar_ejercicios",
    "listar_ejercicios_por_ids",
    "listar_fechas_de_demanda_en_rango",
    "listar_fechas_por_tipo_en_rango",
    "listar_planes_candidatos_de_fecha",
    "listar_planes_por_ciclo_semana",
    "listar_planes_por_ciclo_y_tipos",
    "listar_sesiones_por_fecha",
    "listar_tipos_sesion",
    "listar_zonas_corporales",
    "obtener_ciclo_por_id",
    "obtener_ciclo_semana_por_id",
    "obtener_sesion_plan_por_id",
    "obtener_sesion_por_id",
    "reemplazar_composicion",
]
