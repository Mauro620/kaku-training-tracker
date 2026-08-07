from app.repositories.nutricion import alimento as _alimento
from app.repositories.nutricion import comida as _comida
from app.repositories.nutricion import despensa as _despensa
from app.repositories.nutricion import receta as _receta

listar_alimentos = _alimento.listar
listar_alimentos_por_ids = _alimento.listar_por_ids

crear_receta = _receta.crear
agregar_items_receta = _receta.agregar_items
eliminar_items_receta = _receta.eliminar_items
obtener_receta_por_id = _receta.obtener_por_id
listar_recetas_por_usuario = _receta.listar_por_usuario
actualizar_receta_cabecera = _receta.actualizar_cabecera
eliminar_receta = _receta.eliminar

crear_comida = _comida.crear
agregar_items_comida = _comida.agregar_items
contar_items_comida = _comida.contar_items
eliminar_items_de_comida = _comida.eliminar_items_de_comida
obtener_comida_por_id = _comida.obtener_por_id
listar_comidas_por_fecha = _comida.listar_por_fecha
eliminar_comida = _comida.eliminar

upsert_despensa = _despensa.upsert
obtener_despensa = _despensa.obtener
listar_despensa_por_usuario = _despensa.listar_por_usuario
lista_de_mercado = _despensa.lista_de_mercado

__all__ = [
    "actualizar_receta_cabecera",
    "agregar_items_comida",
    "agregar_items_receta",
    "contar_items_comida",
    "crear_comida",
    "crear_receta",
    "eliminar_comida",
    "eliminar_items_receta",
    "eliminar_receta",
    "lista_de_mercado",
    "listar_alimentos",
    "listar_alimentos_por_ids",
    "listar_comidas_por_fecha",
    "listar_despensa_por_usuario",
    "listar_recetas_por_usuario",
    "obtener_comida_por_id",
    "obtener_despensa",
    "obtener_receta_por_id",
    "upsert_despensa",
]
