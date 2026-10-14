# ruff: noqa: E501
# (frases en prosa: partirlas en varias lineas las vuelve ilegibles)
"""La frase de cada tarjeta de Progreso.

Funciones puras: reciben las cifras ya calculadas y devuelven texto. Viven
aparte del servicio para poder probar cada frase sin base de datos, y porque la
frase y el grafico tienen que salir de los mismos numeros.
"""

from collections.abc import Sequence

from app.schemas.metricas.progreso import (
    PruebaTendencia,
    SemanaComposicion,
    SemanaCumplimiento,
    SemanaRecuperacion,
)


def num(valor: float, decimales: int = 1) -> str:
    """Numero con coma decimal, sin ceros de relleno: 7.0 -> '7', 7.25 -> '7,3'."""
    texto = f"{valor:.{decimales}f}"
    # Solo se recortan ceros DECIMALES: "50" no puede quedar en "5".
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def cumplimiento(semanas: Sequence[SemanaCumplimiento]) -> str:
    con_plan = [s for s in semanas if s.planeadas > 0]
    if not con_plan:
        return (
            "Todavía no hay sesiones planeadas en un ciclo para medir el cumplimiento."
        )
    s = con_plan[-1]
    hechas = s.cumplido + s.movido
    texto = (
        f"En la semana {s.numero} ejecutaste {hechas} de {s.planeadas} sesiones "
        f"planeadas ({num(100 * hechas / s.planeadas, 0)} %)"
    )
    extras = []
    if s.movido:
        extras.append(f"{s.movido} movida{'s' if s.movido != 1 else ''} de día")
    if s.descartado:
        extras.append(f"{s.descartado} descartada{'s' if s.descartado != 1 else ''}")
    if s.pendiente:
        extras.append(f"{s.pendiente} pendiente{'s' if s.pendiente != 1 else ''}")
    return texto + (f"; {', '.join(extras)}." if extras else ".")


def rendimiento(pruebas: Sequence[PruebaTendencia], n_marcas: int) -> str:
    con_cambio = [
        p for p in pruebas if p.puntos and p.puntos[-1].pct_cambio_vs_base is not None
    ]
    if not con_cambio and not n_marcas:
        return "Todavía no hay pruebas ni ejercicios con marca para comparar."
    partes = []
    if con_cambio:
        mejoran = [
            p.nombre for p in con_cambio if (p.puntos[-1].pct_cambio_vs_base or 0) > 0
        ]
        partes.append(
            "Pruebas mejor que en la primera medición: "
            f"{len(mejoran)} de {len(con_cambio)}"
            + (f" ({', '.join(mejoran)})" if mejoran else "")
        )
    elif pruebas:
        partes.append(
            "Hay una sola medición por prueba: falta una segunda para comparar"
        )
    if n_marcas:
        partes.append(
            f"marca registrada en {n_marcas} ejercicio{'s' if n_marcas != 1 else ''}"
        )
    texto = "; ".join(partes)
    # capitalize() minusculizaria el resto ("Salto CMJ" -> "salto cmj").
    return texto[0].upper() + texto[1:] + "."


def recuperacion(semanas: Sequence[SemanaRecuperacion], sueno_objetivo_h: float) -> str:
    if not semanas:
        return "Todavía no hay datos de carga."
    ultima = semanas[-1]
    if ultima.acwr is None:
        base = (
            "Aún no se puede calcular el ACWR: hacen falta 28 días de historia "
            "desde tu primera sesión (o no hubo carga en ese periodo)"
        )
    else:
        valor = num(ultima.acwr, 2)
        base = {
            "baja": f"Tu carga reciente está por debajo de tu promedio (ACWR {valor}): hay margen para subir",
            "verde": f"Tu carga está en la zona segura (ACWR {valor})",
            "amarillo": f"Tu carga reciente sube por encima de tu promedio (ACWR {valor}): vigila cómo te sientes",
            "rojo": f"Tu carga reciente es mucho mayor que tu promedio (ACWR {valor}): considera bajarla",
        }[ultima.semaforo or "verde"]
    if ultima.sueno_prom_h is None:
        return base + "."
    dormido = num(ultima.sueno_prom_h)
    comparacion = (
        "por debajo de" if ultima.sueno_prom_h < sueno_objetivo_h else "dentro de"
    )
    return (
        f"{base}. Dormiste {dormido} h de promedio esta semana, "
        f"{comparacion} tu objetivo de {num(sueno_objetivo_h)} h."
    )


def composicion(
    semanas: Sequence[SemanaComposicion],
    cambio_peso_kg: float | None,
    cambio_cintura_cm: float | None,
    peso_objetivo_kg: float | None,
) -> str:
    if not semanas:
        return "Todavía no hay mediciones de peso."
    ultima = semanas[-1]
    if cambio_peso_kg is None:
        texto = f"Tu último peso es {num(ultima.peso_kg)} kg: falta una segunda medición para ver la tendencia"
    else:
        sentido = "bajaste" if cambio_peso_kg < 0 else "subiste"
        if cambio_peso_kg == 0:
            texto = f"Tu peso se mantiene en {num(ultima.peso_kg)} kg"
        else:
            texto = (
                f"En {len(semanas)} semanas con medición {sentido} "
                f"{num(abs(cambio_peso_kg))} kg (ahora {num(ultima.peso_kg)} kg)"
            )
    if cambio_cintura_cm:
        sentido = "bajó" if cambio_cintura_cm < 0 else "subió"
        texto += f"; la cintura {sentido} {num(abs(cambio_cintura_cm))} cm"
    if peso_objetivo_kg is not None:
        resto = ultima.peso_kg - peso_objetivo_kg
        texto += (
            f"; te faltan {num(resto)} kg para tu objetivo de {num(peso_objetivo_kg)} kg"
            if resto > 0
            else f"; ya estás en o por debajo de tu objetivo de {num(peso_objetivo_kg)} kg"
        )
    return texto + ". El peso solo no mide la grasa."
