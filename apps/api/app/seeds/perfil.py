"""Perfil inicial del atleta.

A diferencia del resto de los seeds, este NO se actualiza al re-sembrar: el
perfil es un dato que el usuario edita desde la app, y pisarlo con la semilla
borraria sus cambios. Se inserta una sola vez (ON CONFLICT DO NOTHING).
"""

from decimal import Decimal
from typing import Any

PERFIL: dict[str, Any] = {
    "posicion": "Extremo izquierdo",
    "pie_dominante": "derecho (trabajando la zurda)",
    "rol_tactico": (
        "1v1 por banda, centro y pase atrás. "
        "'Oxigenar': cuando el juego está en el extremo derecho, cerrarse al "
        "medio como opción de pase entre líneas. "
        "Bajar a apoyar al lateral izquierdo cuando está presionado."
    ),
    "talla_cm": Decimal("178.0"),
    "peso_kg": Decimal("80.00"),
    "lesiones_activas": [],
    "objetivos": [
        "Retomar regularidad sin lesionarme",
        "Fuerza y potencia funcional para fútbol",
        "Técnica y toma de decisiones del rol",
        "Repetición de esfuerzos de alta intensidad",
        "Bajar a ~11 % de grasa",
    ],
    "eventos_fijos": [
        {
            "dia": dia,
            "hora": "21:00",
            "tipo_sesion": "partido",
            "nombre": "Entreno de equipo",
            "duracion_min": 90,
        }
        for dia in (0, 2)
    ],
    "ventanas": [
        {"dia": 0, "inicio": "09:00", "fin": "10:30", "lugares": ["Gimnasio"]},
        {
            "dia": 1,
            "inicio": "15:30",
            "fin": "17:30",
            "lugares": ["Cancha El Dorado"],
        },
        {
            "dia": 2,
            "inicio": "09:45",
            "fin": "10:30",
            "lugares": ["Cancha pequeña con muros"],
        },
        {"dia": 3, "inicio": "11:00", "fin": "12:30", "lugares": ["Gimnasio"]},
        {
            "dia": 4,
            "inicio": "09:00",
            "fin": "10:30",
            "lugares": ["Gimnasio", "Pista de atletismo"],
        },
        {
            "dia": 5,
            "inicio": "07:45",
            "fin": "09:15",
            "lugares": ["Gimnasio", "Zona de calistenia"],
        },
    ],
    # El domingo no tiene ventana: es descanso.
    "lugares": [
        {"nombre": "Gimnasio", "equipamiento": []},
        {
            "nombre": "Cancha El Dorado",
            "equipamiento": ["cancha grande", "pista de atletismo", "conos"],
        },
        {"nombre": "Cancha pequeña con muros", "equipamiento": ["muros"]},
        {"nombre": "Pista de atletismo", "equipamiento": ["pista de atletismo"]},
        {"nombre": "Zona de calistenia", "equipamiento": []},
    ],
}
