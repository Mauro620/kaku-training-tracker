"""Catálogos base. Agregar una fila es un seed, nunca una migración."""

from app.models.enums import Demanda

# `demanda` es lo que consulta el semáforo de cerveza: "ninguna sesion_plan de
# demanda alta ni partido en las próximas N horas" (REGLAS_NEGOCIO §11).
TIPOS_SESION: tuple[tuple[str, str, Demanda], ...] = (
    ("fuerza", "Fuerza y potencia", Demanda.alta),
    ("velocidad_salto", "Velocidad y salto", Demanda.alta),
    ("resistencia", "Resistencia de juego", Demanda.media),
    ("balon_control", "Balón: control y regate", Demanda.media),
    ("balon_distribucion", "Balón: distribución", Demanda.media),
    ("recuperacion", "Recuperación activa", Demanda.baja),
    ("partido", "Partido", Demanda.alta),
)

ZONAS_CORPORALES: tuple[str, ...] = (
    "lumbar",
    "cervical",
    "dorsal",
    "hombro",
    "cadera",
    "isquiotibiales",
    "cuadriceps",
    "aductores",
    "ingle",
    "rodilla",
    "gemelo",
    "tobillo",
    "pie",
)

# `mejor_es_mayor` evita el bug clásico: en sprint_10m menos es mejor, en cmj
# más es mejor. Sin este campo el cálculo de mejora se invierte en la mitad de
# los tests (REGLAS_NEGOCIO §8).
TIPOS_TEST: tuple[tuple[str, str, str, bool], ...] = (
    ("cmj", "Salto CMJ", "cm", True),
    ("sprint_10m", "Sprint 10 m", "s", False),
    ("broad_jump", "Salto horizontal", "cm", True),
    ("rsa_30m", "RSA 6x30 m", "s", False),
    ("yoyo_ir1", "Yo-Yo IR1", "m", True),
)

# "Celular fuera" NO está acá: vive en registro_sueno.celular_fuera y se llena
# en el mismo formulario del despertar. Tenerlo en los dos lados sería el mismo
# hecho en dos filas que van a divergir.
HABITOS: tuple[str, ...] = (
    "creatina",
    "magnesio",
    "estiramiento",
    "hidratacion",
)
