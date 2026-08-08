"""Umbrales de negocio. La tabla completa de ARCHITECTURE.md §3.

Ningún servicio recibe uno de estos como literal. Si aparece un número mágico
dentro de una función, la clave que falta se agrega acá.
"""

from decimal import Decimal

PARAMETROS: tuple[tuple[str, Decimal, str | None, str], ...] = (
    # ---------- Sueño ----------
    ("sueno_objetivo_horas", Decimal("7.0"), "h", "Objetivo diario de sueño"),
    (
        "dia_registro_hora_corte",
        Decimal("4"),
        "h",
        "Antes de esta hora el registro del día sigue siendo el de ayer "
        "(alguien que se acuesta después de medianoche no debería ver la "
        "pantalla Hoy en blanco antes de dormir)",
    ),
    # ---------- Hidratacion ----------
    (
        "hidratacion_objetivo_ml",
        Decimal("3000"),
        "ml",
        "Objetivo diario de agua (4 termos de 750 ml). El usuario tiene "
        "rangos personales en usuario.agua_objetivo_ml_min/max, pero aca "
        "va un valor global de referencia para la UI de Hoy.",
    ),
    # ---------- ACWR (REGLAS_NEGOCIO §3) ----------
    ("acwr_min_seguro", Decimal("0.8"), None, "Piso de la zona segura de ACWR"),
    ("acwr_max_seguro", Decimal("1.3"), None, "Techo de la zona segura de ACWR"),
    ("acwr_umbral_alerta", Decimal("1.5"), None, "ACWR por encima del cual hay alerta"),
    ("acwr_dias_agudo", Decimal("7"), "dias", "Ventana de carga aguda"),
    ("acwr_dias_cronico", Decimal("28"), "dias", "Ventana de carga crónica"),
    # ---------- Tests físicos ----------
    (
        "cmj_caida_alerta_pct",
        Decimal("5.0"),
        "pct",
        "Caída de CMJ contra base que penaliza el Estado",
    ),
    (
        "rsa_decremento_bueno_pct",
        Decimal("5.0"),
        "pct",
        "Decremento de RSA por debajo del cual el resultado es bueno",
    ),
    (
        "rsa_decremento_alerta_pct",
        Decimal("8.0"),
        "pct",
        "Decremento de RSA por encima del cual hay déficit de recuperación",
    ),
    # ---------- Estado del día: bandas (REGLAS_NEGOCIO §9) ----------
    ("estado_banda_verde", Decimal("75"), "puntos", "Estado mínimo para cargar duro"),
    (
        "estado_banda_amarilla",
        Decimal("55"),
        "puntos",
        "Estado mínimo para entrenar moderado; por debajo, recuperación",
    ),
    # ---------- Estado del día: penalizaciones ----------
    (
        "estado_penal_sueno_por_hora",
        Decimal("2"),
        "puntos",
        "Penalización por cada hora de deuda de sueño de 7 días",
    ),
    (
        "estado_penal_sueno_tope",
        Decimal("20"),
        "puntos",
        "Tope de la penalización por deuda de sueño",
    ),
    (
        "estado_penal_hooper_por_punto",
        Decimal("3"),
        "puntos",
        "Penalización por cada punto de Hooper sobre la línea base",
    ),
    (
        "estado_penal_hooper_tope",
        Decimal("25"),
        "puntos",
        "Tope de la penalización por Hooper",
    ),
    (
        "estado_penal_acwr_moderado",
        Decimal("8"),
        "puntos",
        "Penalización con ACWR entre acwr_max_seguro y acwr_umbral_alerta",
    ),
    (
        "estado_penal_acwr_alto",
        Decimal("15"),
        "puntos",
        "Penalización con ACWR por encima de acwr_umbral_alerta",
    ),
    (
        "estado_penal_molestia_por_punto",
        Decimal("2"),
        "puntos",
        "Penalización por cada punto de intensidad de molestia de hoy",
    ),
    (
        "estado_penal_molestia_tope",
        Decimal("20"),
        "puntos",
        "Tope de la penalización por molestia",
    ),
    (
        "estado_penal_cmj",
        Decimal("15"),
        "puntos",
        "Penalización cuando el CMJ cayó más de cmj_caida_alerta_pct",
    ),
    # ---------- Línea base de Hooper (REGLAS_NEGOCIO §5) ----------
    (
        "hooper_base_ventana_dias",
        Decimal("28"),
        "dias",
        "Ventana para la mediana que hace de línea base de Hooper",
    ),
    (
        "hooper_base_min_registros",
        Decimal("14"),
        "registros",
        "Registros mínimos en la ventana; con menos, la línea base es NULL",
    ),
    # ---------- Molestia recurrente (REGLAS_NEGOCIO §10.3) ----------
    (
        "molestia_recurrencia_dias",
        Decimal("14"),
        "dias",
        "Ventana en la que se cuenta la recurrencia de molestia por zona",
    ),
    (
        "molestia_recurrencia_conteo",
        Decimal("3"),
        "dias",
        "Días distintos con molestia en la zona que activan la señal",
    ),
    # ---------- Nutrición ----------
    (
        "proteina_g_por_kg",
        Decimal("1.8"),
        "g/kg",
        "Referencia de proteína diaria por kg de peso. No es una meta a perseguir",
    ),
    # ---------- Semáforo de cerveza (REGLAS_NEGOCIO §11) ----------
    (
        "cerveza_horas_sin_alta_demanda",
        Decimal("48"),
        "h",
        "Horas sin sesión de alta demanda ni partido que exige el verde",
    ),
    (
        "cerveza_acwr_max",
        Decimal("1.4"),
        None,
        "ACWR máximo para el verde. Umbral propio, distinto de acwr_max_seguro "
        "(1.3) y de acwr_umbral_alerta (1.5)",
    ),
    (
        "cerveza_deuda_sueno_max",
        Decimal("4"),
        "h",
        "Deuda de sueño de 7 días máxima para el verde",
    ),
    # ---------- Espaciado de plan (REGLAS_NEGOCIO §13.3) ----------
    (
        "fuerza_separacion_min_horas",
        Decimal("48"),
        "h",
        "Separación mínima entre dos sesiones de fuerza al sugerir día",
    ),
    (
        "partido_ventana_previa_horas",
        Decimal("24"),
        "h",
        "Horas previas a un partido sin sesión de demanda alta",
    ),
)
