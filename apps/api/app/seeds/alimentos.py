"""Alimentos de la despensa. Valores por 100 g.

TRES COSAS QUE HAY QUE TENER PRESENTES:

1. Arroz, avena, lentejas y fríjoles están en SECO. Cocidos pesan entre 2,5 y
   3 veces más con los mismos macros. Es el error de medición más grande
   posible en esta tabla: pesar arroz cocido y cargarlo como seco triplica los
   carbohidratos del día.
2. El atún en lata es la ÚNICA excepción a la convención de crudo: el valor es
   del producto escurrido, listo para comer. Por eso va con
   `estado_pesaje = cocido`.
3. Jamón, pan y tostada varían mucho por marca. Los valores son de referencia
   y hay que reemplazarlos por los de la etiqueta real (ver
   `docs/PENDIENTES.md`).
"""

from decimal import Decimal

from app.models.enums import EstadoPesaje, GrupoAlimento

# nombre, grupo, kcal, proteína, carbohidrato, grasa, fibra, estado de pesaje
ALIMENTOS: tuple[
    tuple[
        str, GrupoAlimento, Decimal, Decimal, Decimal, Decimal, Decimal, EstadoPesaje
    ],
    ...,
] = (
    # ---------- Proteína animal ----------
    (
        "Huevo entero",
        GrupoAlimento.proteina_animal,
        Decimal("143"),
        Decimal("12.6"),
        Decimal("0.7"),
        Decimal("9.5"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Pechuga de pollo",
        GrupoAlimento.proteina_animal,
        Decimal("120"),
        Decimal("22.5"),
        Decimal("0.0"),
        Decimal("2.6"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Atún en lata en agua",
        GrupoAlimento.proteina_animal,
        Decimal("116"),
        Decimal("25.5"),
        Decimal("0.0"),
        Decimal("0.8"),
        Decimal("0.0"),
        # Escurrido, listo para comer: la excepción a la convención de crudo.
        EstadoPesaje.cocido,
    ),
    (
        "Tilapia",
        GrupoAlimento.proteina_animal,
        Decimal("96"),
        Decimal("20.1"),
        Decimal("0.0"),
        Decimal("1.7"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Carne de res magra",
        GrupoAlimento.proteina_animal,
        Decimal("143"),
        Decimal("21.5"),
        Decimal("0.0"),
        Decimal("5.8"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Pierna de cerdo magra",
        GrupoAlimento.proteina_animal,
        Decimal("143"),
        Decimal("21.0"),
        Decimal("0.0"),
        Decimal("6.0"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Cañón de cerdo",
        GrupoAlimento.proteina_animal,
        Decimal("120"),
        Decimal("22.0"),
        Decimal("0.0"),
        Decimal("3.5"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    # ---------- Procesado ----------
    (
        "Jamón de cerdo",
        GrupoAlimento.procesado,
        Decimal("145"),
        Decimal("18.0"),
        Decimal("1.5"),
        Decimal("7.5"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    # ---------- Lácteo ----------
    (
        "Leche entera",
        GrupoAlimento.lacteo,
        Decimal("61"),
        Decimal("3.2"),
        Decimal("4.8"),
        Decimal("3.3"),
        Decimal("0.0"),
        EstadoPesaje.crudo,
    ),
    # ---------- Cereal (EN SECO) ----------
    (
        "Avena en hojuelas",
        GrupoAlimento.cereal,
        Decimal("389"),
        Decimal("16.9"),
        Decimal("66.3"),
        Decimal("6.9"),
        Decimal("10.6"),
        EstadoPesaje.crudo,
    ),
    (
        "Arroz blanco",
        GrupoAlimento.cereal,
        Decimal("365"),
        Decimal("7.1"),
        Decimal("80.0"),
        Decimal("0.7"),
        Decimal("1.3"),
        EstadoPesaje.crudo,
    ),
    (
        "Pan integral",
        GrupoAlimento.cereal,
        Decimal("247"),
        Decimal("13.0"),
        Decimal("41.0"),
        Decimal("3.4"),
        Decimal("7.0"),
        EstadoPesaje.crudo,
    ),
    (
        "Tostada integral",
        GrupoAlimento.cereal,
        Decimal("400"),
        Decimal("12.0"),
        Decimal("70.0"),
        Decimal("6.0"),
        Decimal("8.0"),
        EstadoPesaje.crudo,
    ),
    # ---------- Leguminosa (EN SECO) ----------
    (
        "Lentejas secas",
        GrupoAlimento.leguminosa,
        Decimal("352"),
        Decimal("24.6"),
        Decimal("63.4"),
        Decimal("1.1"),
        Decimal("10.7"),
        EstadoPesaje.crudo,
    ),
    (
        "Fríjoles secos",
        GrupoAlimento.leguminosa,
        Decimal("333"),
        Decimal("21.6"),
        Decimal("60.0"),
        Decimal("1.2"),
        Decimal("15.2"),
        EstadoPesaje.crudo,
    ),
    # ---------- Tubérculo ----------
    (
        "Papa",
        GrupoAlimento.tuberculo,
        Decimal("77"),
        Decimal("2.0"),
        Decimal("17.5"),
        Decimal("0.1"),
        Decimal("2.2"),
        EstadoPesaje.crudo,
    ),
    (
        "Plátano verde",
        GrupoAlimento.tuberculo,
        Decimal("122"),
        Decimal("1.3"),
        Decimal("31.9"),
        Decimal("0.4"),
        Decimal("2.3"),
        EstadoPesaje.crudo,
    ),
    (
        "Plátano maduro",
        GrupoAlimento.tuberculo,
        Decimal("128"),
        Decimal("1.3"),
        Decimal("33.6"),
        Decimal("0.4"),
        Decimal("2.0"),
        EstadoPesaje.crudo,
    ),
    # ---------- Verdura (lo único que cuenta para pct_comidas_con_vegetal) ----
    (
        "Brócoli",
        GrupoAlimento.verdura,
        Decimal("34"),
        Decimal("2.8"),
        Decimal("6.6"),
        Decimal("0.4"),
        Decimal("2.6"),
        EstadoPesaje.crudo,
    ),
    (
        "Espinaca",
        GrupoAlimento.verdura,
        Decimal("23"),
        Decimal("2.9"),
        Decimal("3.6"),
        Decimal("0.4"),
        Decimal("2.2"),
        EstadoPesaje.crudo,
    ),
    (
        "Zanahoria",
        GrupoAlimento.verdura,
        Decimal("41"),
        Decimal("0.9"),
        Decimal("9.6"),
        Decimal("0.2"),
        Decimal("2.8"),
        EstadoPesaje.crudo,
    ),
    (
        "Tomate",
        GrupoAlimento.verdura,
        Decimal("18"),
        Decimal("0.9"),
        Decimal("3.9"),
        Decimal("0.2"),
        Decimal("1.2"),
        EstadoPesaje.crudo,
    ),
    # ---------- Fruta ----------
    (
        "Banano",
        GrupoAlimento.fruta,
        Decimal("89"),
        Decimal("1.1"),
        Decimal("22.8"),
        Decimal("0.3"),
        Decimal("2.6"),
        EstadoPesaje.crudo,
    ),
    # ---------- Grasa ----------
    (
        "Aguacate",
        GrupoAlimento.grasa,
        Decimal("160"),
        Decimal("2.0"),
        Decimal("8.5"),
        Decimal("14.7"),
        Decimal("6.7"),
        EstadoPesaje.crudo,
    ),
)

FUENTE = "ICBF"
