"""El test más aburrido del repo. Existe para que `make test` tenga algo que
correr desde el primer commit y el pipeline no nazca en rojo."""


def test_el_paquete_importa() -> None:
    import app

    assert app is not None
