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

---

## JWT vive en `localStorage`, no en cookie httpOnly

**Estado:** aceptado en Fase 5, deuda para una fase de seguridad.

`apps/web/lib/auth.ts` guarda el JWT en `localStorage`. AGENTS §5 dice
"Sin localStorage para datos de dominio", pero el token es auth, no
dominio. Aun asi, queda expuesto a XSS: un script malicioso puede
robarlo. La defensa correcta es cookie httpOnly + CSRF token (SameSite
Strict cubre la mayoria del riesgo sin CSRF explicito, pero hay que
auditarlo).

**Cuando se mueve:** cuando entren autenticacion con sesiones largas o
se decida que el riesgo de XSS ya no es aceptable. Fase 5 priorizo
rapidez de implementacion (no hubo cambio de sesion, mismo flujo de
login). No es bloqueante porque la app es de un solo usuario.

---

## `idempotency_key` en `habito_registro` rompe la decision original del DBML

**Estado:** revertido en Fase 5.

Antes de Fase 5 el DBML decia: "PK compuesta `(habito_id, fecha)`: un
habito tiene como maximo un registro por dia. Esa PK es tambien la
deduplicacion natural de la cola de sync, por eso no lleva
`idempotency_key`". Esa decision era coherente con la idea de que la
PK simple bastaba como unicidad para la cola. En Fase 5 se decidio que
**toda mutacion del cliente lleva `idempotency_key`**, incluso cuando
la unicidad natural ya identifica el recurso. Razones:

- Simetria: las 5 mutaciones de captura tienen el mismo flujo de cola.
- El cliente offline genera una key por intento (RFC 7240): si la red
  falla, reintenta con la misma key sin ambiguedad.
- El `idempotency_key` queda como **metadata** del recurso, no como
  segunda unicidad. Nullable para admitir backfill (Fase 9, Notion).

**Cuando deja de aplicar:** si en algun momento se decide que la
politica "una key por intento del cliente" no escala (ej. backend
con rate limiting por key), se vuelve a la decision original.

---

## Hidratacion: idempotencia con `SELECT` previo, no atomica

**Estado:** aceptado en Fase 5, race condition documentada.

`registro_hidratacion` hace `SELECT WHERE idempotency_key = ?` y si
no encuentra, `INSERT ... ON CONFLICT (usuario_id, fecha) DO NOTHING`
y despues, si no creo nada, `UPDATE ... SET ml_totales = ml_totales +
cantidad_ml, idempotency_key = ?` (mismo patron de 3 pasos que
Sueno/Habito: guarda la key en cada paso, no solo en el primer tap del
dia — bug encontrado y corregido el 2026-08-07, antes la key solo
quedaba en el primer tap y un reintento de cualquier tap posterior
sumaba de nuevo). Dos POSTs simultaneos con la misma key pueden pasar
el SELECT previo y sumar dos veces: la cola de Fase 5 reintenta con
delays (1s, 2s, ...), no concurrencia, asi que el riesgo es bajo. La
forma atomica exigiria
una tabla de eventos `hidratacion_tap (idempotency_key pk, ...)` y
calcular `ml_totales = SUM(cantidad_ml)` por fecha. Eso cambia el
modelo (y entra en conflicto con el SPEC §2.4 que dice "cada tap
suma al total del dia" sin modelo de evento explicito).

**Cuando dejar de lado:** si la cola pasa a reintentar en paralelo o
si se detecta doble suma en produccion, se introduce la tabla de
eventos. Mientras tanto, el patron actual es simple y suficiente.

---

## `ComidasList` muestra `Receta #N` en vez del nombre

**Estado:** aceptado en Fase 6, gap chico.

El frontend lista las comidas del dia con `receta_id` crudo cuando la
comida viene de una receta: falta el join contra `receta` en el
service (o resolver el nombre client-side con la lista de recetas ya
cargada por `useRecetas`). No bloquea nada, es cosmetico.

**Cuando dejar de lado:** la proxima vez que se toque `ComidasList` o
`services/nutricion/comida.py`.

---

## Migracion Dexie v1→v2 (Fase 6) sin validar en navegador real

**Estado:** aceptado en Fase 6.

`db/dexie.ts` agrego `version(2)` con la tabla `comida` sin perder la
`version(1)` de Fase 5. La migracion de Dexie (agregar una tabla nueva
en una version posterior) esta documentada como no-destructiva, pero
solo se probo con tests de Node (`outbox.test.ts`), no con IndexedDB
real en un navegador que ya tuviera datos de la version 1.

**Cuando dejar de lado:** antes de confiar en la cola offline con
usuarios reales que ya tengan la app instalada (hoy es un solo
usuario en dev, el riesgo es bajo).

---

## Objetivo diario de proteína (REGLAS_NEGOCIO §12) no expuesto todavía

**Estado:** pendiente, dependencia recien disponible en Fase 7.

REGLAS_NEGOCIO §12 define `objetivo_proteina_g = peso_kg × proteina_g_por_kg`
usando el peso del `medida_corporal` más reciente. En Fase 6
(`services/nutricion/`) `medida_corporal` todavía no existía como
repo/servicio, así que el endpoint de macros del día no lo calcula.
Fase 7 agregó `evaluacion/medida.py` con
`obtener_medida_mas_reciente`, así que la dependencia ya está lista.

**Cuándo hacerlo:** la próxima vez que se toque `services/nutricion/comida.py`
o `MacrosCard` del frontend: sumar `objetivo_proteina_g` a
`ResultadoMacrosRead` (o a un endpoint separado) usando
`repo_evaluacion.obtener_medida_mas_reciente` + `parametro.proteina_g_por_kg`.
Se muestra como referencia, no como meta a perseguir (dice la regla).
