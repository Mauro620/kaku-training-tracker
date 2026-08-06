"""Ejercicios de la rutina actual.

`carga_lumbar` no es decorativo: permite filtrar alternativas seguras cuando la
molestia lumbar está activa. El codigo de tipo_sesion (4to campo, matchea
TIPOS_SESION en catalogos.py) es lo que le permite a la captura de series
mostrar solo los ejercicios del tipo elegido: `serie` es propio de fuerza,
pero el catalogo entero cubre los siete tipos.
"""

from app.models.enums import CargaLumbar

EJERCICIOS: tuple[tuple[str, str, CargaLumbar, str], ...] = (
    # ---------- Fuerza y potencia ----------
    ("Sentadilla explosiva", "rodilla_dominante", CargaLumbar.alta, "fuerza"),
    ("Hip thrust", "cadera_dominante", CargaLumbar.media, "fuerza"),
    ("Peso muerto rumano", "cadera_dominante", CargaLumbar.alta, "fuerza"),
    ("Salto vertical de contraste", "pliometria", CargaLumbar.baja, "fuerza"),
    ("Pallof press", "core_antirotacion", CargaLumbar.baja, "fuerza"),
    ("Plancha Copenhague", "core_lateral", CargaLumbar.baja, "fuerza"),
    ("Rotacional con balón", "core_rotacion", CargaLumbar.media, "fuerza"),
    ("Elevación de talón", "tobillo", CargaLumbar.baja, "fuerza"),
    ("Pogos", "pliometria", CargaLumbar.baja, "fuerza"),
    # ---------- Velocidad y salto ----------
    ("Sprint acelerativo 10-20 m", "sprint", CargaLumbar.baja, "velocidad_salto"),
    ("Test 505", "cambio_direccion", CargaLumbar.media, "velocidad_salto"),
    ("Corte a 45 grados", "cambio_direccion", CargaLumbar.media, "velocidad_salto"),
    ("Salto CMJ", "pliometria", CargaLumbar.baja, "velocidad_salto"),
    ("Broad jump", "pliometria", CargaLumbar.baja, "velocidad_salto"),
    ("Sprint resistido con banda", "sprint", CargaLumbar.media, "velocidad_salto"),
    # ---------- Resistencia ----------
    ("Fartlek", "aerobico", CargaLumbar.baja, "resistencia"),
    ("RSA 30 m", "sprint_repetido", CargaLumbar.baja, "resistencia"),
    ("Circuito con balón", "aerobico", CargaLumbar.baja, "resistencia"),
    # ---------- Balón: control y regate ----------
    ("Control con muro", "tecnica", CargaLumbar.baja, "balon_control"),
    ("Control orientado", "tecnica", CargaLumbar.baja, "balon_control"),
    ("Regate en conos", "tecnica", CargaLumbar.baja, "balon_control"),
    ("Conducción en zigzag", "tecnica", CargaLumbar.baja, "balon_control"),
    # ---------- Balón: distribución ----------
    (
        "Pase largo y cambio de orientación",
        "tecnica",
        CargaLumbar.baja,
        "balon_distribucion",
    ),
    ("Conducción y centro", "tecnica", CargaLumbar.baja, "balon_distribucion"),
    ("Recibir, girar y distribuir", "tecnica", CargaLumbar.baja, "balon_distribucion"),
    ("Tiro libre", "tecnica", CargaLumbar.baja, "balon_distribucion"),
    ("Penal", "tecnica", CargaLumbar.baja, "balon_distribucion"),
    # ---------- Recuperación ----------
    ("Movilidad completa", "movilidad", CargaLumbar.baja, "recuperacion"),
    ("Trote suave", "aerobico", CargaLumbar.baja, "recuperacion"),
)
