# Pendientes

Decisiones tomadas a conciencia que tienen fecha de vencimiento, y huecos
conocidos que todavía no bloquean nada. No es un backlog de features: es la
lista de cosas que sabemos que están a medias y por qué las dejamos así.

---

## `parametro` es global, sin `usuario_id`

**Estado:** aceptado para el usuario único.

Todas las demás tablas del dominio llevan `usuario_id`, con la justificación
explícita del DBML: "no migrar 20 tablas si mañana entra un compañero".
`parametro` rompe ese criterio a propósito, porque hoy no hay con quién
chocar.

**Cuándo deja de alcanzar:** el día que entre un segundo usuario. SPEC §5.1
dice que el Estado es "calibrable", así que dos atletas con umbrales
calibrados distintos se pisan entre sí. La migración es agregar `usuario_id`
nullable (NULL = valor por defecto del sistema) y cambiar la unicidad a
`(usuario_id, clave, vigente_desde)`.

---

## Nivel de Yo-Yo IR1 derivado, no almacenado

**Estado:** decidido. `test_intento.valor` guarda solo la distancia.

Falta escribir la tabla del protocolo Yo-Yo IR1 (distancia → nivel) en algún
lado del código. No hace falta hasta la fase 7.

---

## `registro_sueno.fecha` es un invariante de servicio

No se puede imponer con `CHECK` ni con columna generada: la conversión de
`timestamptz` a fecha local depende de la zona horaria, y esa conversión no
es `IMMUTABLE` en Postgres. El servicio que escribe sueño es el responsable
de que `fecha` sea la fecha local de `fin`.

**Riesgo:** un cliente mal calibrado puede escribir una fecha que no
corresponde al despertar, y nada lo detiene. Vale un test de servicio en la
fase 3.

---

## Valores de `alimento` dependientes de marca

Jamón de cerdo, pan integral y tostada integral varían mucho entre marcas.
Los valores sembrados son de referencia y hay que reemplazarlos por los de la
etiqueta real cuando se confirme cuál se compra.

---

## `SPEC.md` §2.1 describe el sueño como dos campos `time`

El DBML usa `inicio` y `fin` en `timestamptz`, que es lo correcto (cruzar
medianoche con dos campos `time` obliga a lógica condicional en cada
consulta). La tabla de SPEC §2.1 quedó con la redacción vieja porque describe
la *interfaz* de captura, no el almacenamiento. Si en algún momento confunde
a alguien, se reescribe.

---

## `estado_pesaje` admite `cocido` pero nada lo usa

REGLAS §12 obliga a sembrar todo en crudo. El valor `cocido` del enum existe
para que una fuente externa pueda declararse tal cual antes de convertirse,
pero hoy ninguna fila lo tiene. Si en seis meses sigue vacío, sacarlo.

**Excepción viva:** el atún en lata está sembrado con el valor del producto
escurrido, listo para comer. Es la única fila que no es crudo literal.
