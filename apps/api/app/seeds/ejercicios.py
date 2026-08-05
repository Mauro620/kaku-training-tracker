"""Ejercicios de la rutina actual.

`carga_lumbar` no es decorativo: permite filtrar alternativas seguras cuando la
molestia lumbar está activa.
"""

from app.models.enums import CargaLumbar

EJERCICIOS: tuple[tuple[str, str, CargaLumbar], ...] = (
    # ---------- Fuerza y potencia ----------
    ("Sentadilla explosiva", "rodilla_dominante", CargaLumbar.alta),
    ("Hip thrust", "cadera_dominante", CargaLumbar.media),
    ("Peso muerto rumano", "cadera_dominante", CargaLumbar.alta),
    ("Salto vertical de contraste", "pliometria", CargaLumbar.baja),
    ("Pallof press", "core_antirotacion", CargaLumbar.baja),
    ("Plancha Copenhague", "core_lateral", CargaLumbar.baja),
    ("Rotacional con balón", "core_rotacion", CargaLumbar.media),
    ("Elevación de talón", "tobillo", CargaLumbar.baja),
    ("Pogos", "pliometria", CargaLumbar.baja),
    # ---------- Velocidad y salto ----------
    ("Sprint acelerativo 10-20 m", "sprint", CargaLumbar.baja),
    ("Test 505", "cambio_direccion", CargaLumbar.media),
    ("Corte a 45 grados", "cambio_direccion", CargaLumbar.media),
    ("Salto CMJ", "pliometria", CargaLumbar.baja),
    ("Broad jump", "pliometria", CargaLumbar.baja),
    ("Sprint resistido con banda", "sprint", CargaLumbar.media),
    # ---------- Resistencia ----------
    ("Fartlek", "aerobico", CargaLumbar.baja),
    ("RSA 30 m", "sprint_repetido", CargaLumbar.baja),
    ("Circuito con balón", "aerobico", CargaLumbar.baja),
    # ---------- Balón: control y regate ----------
    ("Control con muro", "tecnica", CargaLumbar.baja),
    ("Control orientado", "tecnica", CargaLumbar.baja),
    ("Regate en conos", "tecnica", CargaLumbar.baja),
    ("Conducción en zigzag", "tecnica", CargaLumbar.baja),
    # ---------- Balón: distribución ----------
    ("Pase largo y cambio de orientación", "tecnica", CargaLumbar.baja),
    ("Conducción y centro", "tecnica", CargaLumbar.baja),
    ("Recibir, girar y distribuir", "tecnica", CargaLumbar.baja),
    ("Tiro libre", "tecnica", CargaLumbar.baja),
    ("Penal", "tecnica", CargaLumbar.baja),
    # ---------- Recuperación ----------
    ("Movilidad completa", "movilidad", CargaLumbar.baja),
    ("Trote suave", "aerobico", CargaLumbar.baja),
)
