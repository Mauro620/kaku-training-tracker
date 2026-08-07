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

---

## `usuario.agua_objetivo_ml_min` y `_max` son personales, no viven en `parametro`

La meta diaria de hidratación (ej. 2.5–3 L) es **personal** y por eso vive
en `usuario`, no en la tabla `parametro` global. Mismo patrón que
`usuario.peso_objetivo_kg`. Esto rompe a propósito el principio de
"umbrales calibrables en `parametro`": la diferencia es que un rango de
meta individual no es una constante de fórmula compartida — dos atletas
del mismo sistema podrían tener metas distintas y ninguna tiene razón de
ganar. Si más adelante la meta de hidratación pasa a depender de peso o
clima, se mueve a una `parametro` con `usuario_id` (no rompe nada: ya
está prevista esa migración, ver entrada anterior).

---

## El hábito `hidratacion` se desactivó pero no se borró

`Habito.activo = false` para la fila sembrada de "hidratacion". La
hidratación pasó a ser un registro por cantidad (en litros) en
`registro_hidratacion`, no un check booleano. Los registros históricos
del hábito (`habito_registro` con `valor = true/false` para fechas
anteriores) siguen existiendo y son legítimos: el usuario marcó lo que
correspondía al modelo viejo. Borrarlos sería falsificar historia.

**Cuándo dejarlo de lado:** cuando la pantalla Hoy deje de mostrar el
hábito desactivado y nadie lo busque. En la práctica eso ya pasó (la
checklist de hábitos no incluye `activo = false`), así que esta nota
es por si alguien mira la base y se pregunta por qué hay un hábito
desactivado.

---

## `serie` se renombró a `bloque` en Fase 4

El modelo de `serie` era "N series × M reps" y no describía trabajo no-fuerza
(sprints a distancia, controles tecnicos). En la ultima entrega de Fase 4
se renombro la tabla a `bloque` via `ALTER TABLE ... RENAME` (no drop+create:
la data se preserva), y se sumo `tipo_medicion` (`carga` | `distancia` |
`tiempo` | `tecnica`) en `ejercicio` para determinar que campos acepta
cada bloque.

**Por qué quedó asi:** ya estaban migradas 7 sesiones de prueba al
momento del rename, y la migracion `a09181f1ca0e` preserva los datos.
Busquedas en codigo viejo que digan `serie` (en commits previos, en
documentacion desactualizada, en chats) no van a matchear nada en la
base. Si alguien lee docs viejos y busca `serie.rpe` por ejemplo, tiene
que migrar mentalmente a `bloque.rpe`.

**Cuando dejar de lado:** cuando los commits previos a Fase 4 queden
fuera del historial activo (release de v1.0). Mientras tanto, esta
nota documenta que el rename es intencional.

## `ejercicio.tipo_sesion_id` ahora es nullable

Antes de Fase 4: `ejercicio.tipo_sesion_id` era NOT NULL y se usaba para
filtrar el selector ("solo ejercicios de fuerza cuando el tipo de sesion
es fuerza"). Con la llegada de `tipo_medicion`, ese filtro dejo de tener
sentido: la categoria "fuerza" ya no se fija por el tipo de sesion sino
por el `tipo_medicion` del ejercicio individual.

**Estado:** la columna sigue ahi como nullable (no se borro para no romper
referencias en el seed y en busquedas historicas), pero la UI ya no la
expone ni la usa. Si en algun momento se decide que tampoco sirve como
categorizacion de referencia, se migra a una tabla aparte de tags.
