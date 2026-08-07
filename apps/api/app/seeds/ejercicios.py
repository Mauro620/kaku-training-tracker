"""Ejercicios de la rutina actual.

`carga_lumbar` no es decorativo: permite filtrar alternativas seguras cuando la
molestia lumbar está activa. El codigo de tipo_sesion (4to campo, matchea
TIPOS_SESION en catalogos.py) es categorizacion de referencia, ya no filtra
el selector de la captura (eso lo hace tipo_medicion, REGLAS_NEGOCIO §15).
tipo_medicion (5to campo) determina que campos acepta cada bloque de este
ejercicio: carga, distancia, tiempo o tecnica.
"""

from app.models.enums import CargaLumbar, TipoMedicion

EJERCICIOS: tuple[tuple[str, str, CargaLumbar, str, TipoMedicion], ...] = (
    # ---------- Fuerza y potencia ----------
    (
        "Sentadilla explosiva",
        "rodilla_dominante",
        CargaLumbar.alta,
        "fuerza",
        TipoMedicion.carga,
    ),
    ("Hip thrust", "cadera_dominante", CargaLumbar.media, "fuerza", TipoMedicion.carga),
    (
        "Peso muerto rumano",
        "cadera_dominante",
        CargaLumbar.alta,
        "fuerza",
        TipoMedicion.carga,
    ),
    (
        "Salto vertical de contraste",
        "pliometria",
        CargaLumbar.baja,
        "fuerza",
        TipoMedicion.carga,
    ),
    (
        "Pallof press",
        "core_antirotacion",
        CargaLumbar.baja,
        "fuerza",
        TipoMedicion.carga,
    ),
    (
        "Plancha Copenhague",
        "core_lateral",
        CargaLumbar.baja,
        "fuerza",
        TipoMedicion.tiempo,
    ),
    (
        "Rotacional con balón",
        "core_rotacion",
        CargaLumbar.media,
        "fuerza",
        TipoMedicion.carga,
    ),
    ("Elevación de talón", "tobillo", CargaLumbar.baja, "fuerza", TipoMedicion.carga),
    ("Pogos", "pliometria", CargaLumbar.baja, "fuerza", TipoMedicion.tecnica),
    # ---------- Velocidad y salto ----------
    (
        "Sprint acelerativo 10-20 m",
        "sprint",
        CargaLumbar.baja,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    (
        "Test 505",
        "cambio_direccion",
        CargaLumbar.media,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    (
        "Corte a 45 grados",
        "cambio_direccion",
        CargaLumbar.media,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    (
        "Salto CMJ",
        "pliometria",
        CargaLumbar.baja,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    (
        "Broad jump",
        "pliometria",
        CargaLumbar.baja,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    (
        "Sprint resistido con banda",
        "sprint",
        CargaLumbar.media,
        "velocidad_salto",
        TipoMedicion.distancia,
    ),
    # ---------- Resistencia ----------
    ("Fartlek", "aerobico", CargaLumbar.baja, "resistencia", TipoMedicion.tiempo),
    (
        "RSA 30 m",
        "sprint_repetido",
        CargaLumbar.baja,
        "resistencia",
        TipoMedicion.distancia,
    ),
    (
        "Circuito con balón",
        "aerobico",
        CargaLumbar.baja,
        "resistencia",
        TipoMedicion.tecnica,
    ),
    # ---------- Balón: control y regate ----------
    (
        "Control con muro",
        "tecnica",
        CargaLumbar.baja,
        "balon_control",
        TipoMedicion.tecnica,
    ),
    (
        "Control orientado",
        "tecnica",
        CargaLumbar.baja,
        "balon_control",
        TipoMedicion.tecnica,
    ),
    (
        "Regate en conos",
        "tecnica",
        CargaLumbar.baja,
        "balon_control",
        TipoMedicion.tecnica,
    ),
    (
        "Conducción en zigzag",
        "tecnica",
        CargaLumbar.baja,
        "balon_control",
        TipoMedicion.tecnica,
    ),
    # ---------- Balón: distribución ----------
    (
        "Pase largo y cambio de orientación",
        "tecnica",
        CargaLumbar.baja,
        "balon_distribucion",
        TipoMedicion.distancia,
    ),
    (
        "Conducción y centro",
        "tecnica",
        CargaLumbar.baja,
        "balon_distribucion",
        TipoMedicion.tecnica,
    ),
    (
        "Recibir, girar y distribuir",
        "tecnica",
        CargaLumbar.baja,
        "balon_distribucion",
        TipoMedicion.tecnica,
    ),
    (
        "Tiro libre",
        "tecnica",
        CargaLumbar.baja,
        "balon_distribucion",
        TipoMedicion.tecnica,
    ),
    ("Penal", "tecnica", CargaLumbar.baja, "balon_distribucion", TipoMedicion.tecnica),
    # ---------- Recuperación ----------
    (
        "Movilidad completa",
        "movilidad",
        CargaLumbar.baja,
        "recuperacion",
        TipoMedicion.tiempo,
    ),
    ("Trote suave", "aerobico", CargaLumbar.baja, "recuperacion", TipoMedicion.tiempo),
)
