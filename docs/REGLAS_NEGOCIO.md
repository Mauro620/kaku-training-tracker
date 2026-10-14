# Reglas de negocio

Definiciones exactas. Un agente **no puede inventar, deducir ni aproximar**
ninguna de estas fórmulas. Si necesitas una que no está aquí, detente y
pregunta.

Cada regla incluye casos de prueba. Esos casos son el contrato: van a los
tests unitarios tal cual.

---

## 1. Carga de sesión (sRPE)

```
carga_srpe = rpe × duracion_min
```

Columna generada en `sesion`. `rpe` entre 1 y 10, `duracion_min` > 0.

**Casos**
| rpe | duracion_min | carga_srpe |
|---|---|---|
| 8 | 60 | 480 |
| 5 | 45 | 225 |

---

## 2. Carga diaria

Suma de `carga_srpe` de todas las sesiones de esa fecha. Un día sin sesiones
tiene carga 0 — y ese cero **cuenta** en los promedios. Omitirlo infla el
ACWR artificialmente.

---

## 3. ACWR

```
carga_aguda   = suma de carga diaria de los últimos 7 días (incluye hoy)
carga_cronica = promedio de las 4 ventanas semanales de los últimos 28 días
              = suma de carga diaria de los últimos 28 días ÷ 4
acwr          = carga_aguda ÷ carga_cronica
```

- Si hay menos de 28 días de historia, `acwr` es **NULL**. No se aproxima.
- Si `carga_cronica` es 0, `acwr` es NULL.
- Bandas leídas de `parametro`: seguro entre `acwr_min_seguro` y
  `acwr_max_seguro`, alerta por encima de `acwr_umbral_alerta`.

**Casos**
| carga 7d | carga 28d | acwr |
|---|---|---|
| 2000 | 7400 | 1.081 |
| 2400 | 6000 | 1.600 |
| 1000 | 0 | NULL |
| cualquiera, con 20 días de historia | — | NULL |

---

## 4. Monotonía y strain

Sobre los últimos 7 días de carga diaria, incluyendo los ceros:

```
monotonia = media(carga_diaria) ÷ desviacion_estandar_poblacional(carga_diaria)
strain    = suma(carga_diaria_7d) × monotonia
```

Si la desviación estándar es 0 (siete días idénticos), `monotonia` es NULL y
se marca la bandera `carga_invariante = true`. No se divide por cero ni se
sustituye por un valor arbitrario.

**Caso**
Cargas `[480, 0, 360, 240, 480, 0, 400]` → media 280.0, desviación
poblacional ≈ 192.428, monotonía ≈ 1.455, strain ≈ 2851.974.

---

## 5. Índice de Hooper

```
hooper = sueno_pobre + fatiga + dolor_muscular + estres
```

Cada ítem entre 1 y 5, con `CHECK` en base de datos. Rango 4–20.
La línea base es la **mediana** de los últimos `hooper_base_ventana_dias`
días con al menos `hooper_base_min_registros` registros; con menos, la línea
base es NULL y no se penaliza el Estado.

Convención de dirección: **1 es bueno, 5 es malo** en los cuatro ítems.
Es decir, `sueno_pobre = 1` significa "dormí muy bien". El campo se llama
`sueno_pobre` y no `sueno_calidad` justamente para que el nombre apunte en la
misma dirección que el valor: mantener los cuatro ítems alineados evita
invertir uno por error.

---

## 6. Horas de sueño

```
horas_sueno = EXTRACT(EPOCH FROM fin - inicio) / 3600.0
```

Columna generada en `registro_sueno`. La `fecha` del registro es la del
**despertar**. `fin` debe ser posterior a `inicio` (CHECK).

**Fecha del registro y hora de corte del día.** Un usuario que se acuesta
después de medianoche no debería ver la pantalla Hoy en blanco antes de
dormir. La regla es: si la hora local actual es anterior a
`parametro.dia_registro_hora_corte` (semilla: 4.0 h), el "día de registro"
sigue siendo el de calendario anterior; después del corte, pasa al día
nuevo. Esto vive en `lib/fecha.ts` del frontend y se aplica al construir
la fecha que se manda al API, no en el backend: el backend sigue aceptando
la fecha que el cliente le pasa, y la unicidad `(usuario_id, fecha)` actúa
como deduplicación natural sin lógica extra. Editar "antes del corte" ES
editar el día anterior.

```
deuda_sueno_7d = Σ max(0, sueno_objetivo_horas − horas_sueno_del_dia)
```

Sobre los últimos 7 días. Dormir de más no compensa: el `max(0, ...)` es
deliberado, no un descuido.

---

## 7. Decremento de RSA

Sobre los intentos de un `test_fisico` de tipo `rsa_30m`:

```
mejor          = min(tiempos)
n              = cantidad de intentos
pct_decremento = 100 × (suma(tiempos) ÷ (mejor × n)) − 100
```

Requiere al menos 4 intentos; con menos, NULL.

**Caso**
Tiempos `[4.20, 4.28, 4.35, 4.41, 4.52, 4.60]` → mejor 4.20, suma 26.36,
`pct_decremento` ≈ 4.603.

Interpretación (umbrales en `parametro`): por debajo de
`rsa_decremento_bueno_pct` es bueno; por encima de
`rsa_decremento_alerta_pct` es señal de déficit de recuperación.

---

## 8. Progreso en tests

```
si tipo_test.mejor_es_mayor:
    pct_cambio = 100 × (valor_actual − valor_base) ÷ valor_base
si no:
    pct_cambio = 100 × (valor_base − valor_actual) ÷ valor_base
```

Positivo siempre significa mejora. `valor_base` es el mejor resultado del
primer test registrado de ese tipo. "Mejor" depende también de
`mejor_es_mayor`: mínimo para sprint, máximo para CMJ.

---

## 9. Estado del día

Heurística calibrable. Todas las penalizaciones y topes salen de `parametro`;
los valores de esta tabla son la semilla.

```
estado = 100
estado -= min(estado_penal_sueno_tope,
              estado_penal_sueno_por_hora × deuda_sueno_7d)
estado -= min(estado_penal_hooper_tope,
              estado_penal_hooper_por_punto × max(0, hooper_hoy − hooper_base))
estado -= estado_penal_acwr_moderado  si acwr_max_seguro < acwr <= acwr_umbral_alerta
estado -= estado_penal_acwr_alto      si acwr > acwr_umbral_alerta
estado -= min(estado_penal_molestia_tope,
              estado_penal_molestia_por_punto × intensidad_molestia_hoy)
estado -= estado_penal_cmj  si cmj_actual cayó más de cmj_caida_alerta_pct vs base
estado = max(0, min(100, estado))
```

Ninguna de estas constantes se escribe en el código: todas salen de
`parametro`. Los valores sembrados son 2/20, 3/25, 8, 15, 2/20 y 15
respectivamente.

Los factores con dato faltante **no penalizan** (ACWR nulo, línea base de
Hooper nula, sin CMJ reciente). Nunca se sustituye un faltante por cero.

Bandas: `>= estado_banda_verde` carga · `>= estado_banda_amarilla` moderado ·
por debajo, recuperación.

La respuesta del endpoint incluye siempre el desglose de penalizaciones
aplicadas. La app muestra razones, no un número solo.

---

## 10. Señal de descarga

Se activa con **cualquiera** de las tres:

1. RPE ≥ 9 en las últimas 3 sesiones de tipo fuerza, sin que el peso máximo
   por ejercicio haya subido respecto a las 3 anteriores.
2. Último test de velocidad o salto con `pct_cambio` ≤ 0 frente al anterior.
3. Molestia en la misma zona en `molestia_recurrencia_conteo` días distintos
   dentro de `molestia_recurrencia_dias`.

---

## 11. Semáforo de cerveza

Verde solo si se cumplen las cuatro:

```
deuda_sueno_7d <= cerveza_deuda_sueno_max
ninguna sesion_plan de demanda alta ni partido en las próximas
    cerveza_horas_sin_alta_demanda horas
acwr es NULL o acwr <= cerveza_acwr_max
no está activa la señal de molestia recurrente
```

`cerveza_acwr_max` es un umbral propio (1.4), distinto de `acwr_max_seguro`
(1.3) y de `acwr_umbral_alerta` (1.5). No los confundas.

Devuelve la lista de condiciones con su estado. Nunca devuelve solo un
booleano: el valor está en las razones.

---

## 12. (retirada)

El módulo de Cocina se eliminó. La sección conserva su número para no romper
las referencias cruzadas; ya no define ninguna fórmula.

---

## 13. Cumplimiento de ciclo y espaciado

### 13.1 Rango de fechas de una semana

```
semana_inicio = ciclo.fecha_inicio + (ciclo_semana.numero − 1) × 7
semana_fin    = semana_inicio + 6
```

No es una columna: se deriva de `ciclo.fecha_inicio` y `ciclo_semana.numero`
en el momento de calcular. Guardarla aparte sería una segunda fuente de
verdad que puede divergir si `fecha_inicio` cambia.

### 13.2 Cumplimiento

Para cada fila de `ciclo_semana_composicion` (un `tipo_sesion_id` con su
`cantidad_objetivo`):

```
hecho = cantidad de `sesion` reales de ese tipo_sesion_id
        con fecha entre semana_inicio y semana_fin (inclusive)
cumplimiento = hecho, objetivo (cantidad_objetivo), y hecho ≥ objetivo
```

No se compara contra fecha exacta ni contra `sesion_plan.dia_sugerido`: el
día es sugerencia, no compromiso (§13.3). Un parcial cambiado de día no
genera un tipo de sesión "incumplido" mientras la cantidad de la semana se
cumpla.

### 13.3 Espaciado al sugerir día

Umbrales en `parametro`, no en código:

```
fuerza_separacion_min_horas   = 48
partido_ventana_previa_horas  = 24
```

**Separación entre sesiones de fuerza.** Al sugerir un día para una sesión
de tipo `fuerza`, ninguna otra sesión de fuerza (real, o planificada con
`dia_sugerido` dentro del mismo ciclo) puede caer a menos de
`fuerza_separacion_min_horas` de la fecha candidata. Como no hay hora del
día en el modelo (`sesion.fecha` y `dia_sugerido` son granularidad de día),
la distancia se aproxima a días completos:

```
distancia_minima_dias = ceil(fuerza_separacion_min_horas / 24)
```

Con la semilla (48h), `distancia_minima_dias = 2`: fuerza el lunes y fuerza
el miércoles cumple: fuerza el lunes y el martes, no.

**Ventana previa a un partido.** Al sugerir un día para una sesión de tipo
`partido`, ninguna sesión de demanda `alta` (real o planificada) puede caer
en las `partido_ventana_previa_horas` inmediatamente anteriores. Misma
aproximación a días completos que arriba. Es unidireccional: protege al
partido, no exige lo mismo entre dos sesiones de fuerza entre sí (eso ya lo
cubre la regla anterior).

Ninguna de las dos reglas se evalúa si `dia_sugerido` es `NULL`: un plan sin
día sugerido no compromete nada, no hay fecha candidata que validar.

`activacion` es demanda **baja** deliberadamente: una sesión de priming no
cuenta como día de alta demanda en la ventana previa a un partido ni activa
la regla de fuerza.

---

## 14. Redondeo y nulos

- Los cálculos internos usan `Decimal` o `float` sin redondear.
- El redondeo ocurre solo al serializar: 3 decimales para ACWR y monotonía,
  1 para horas y porcentajes, entero para el Estado.
- Un dato faltante es NULL y se propaga como NULL. **Nunca se sustituye por
  cero.** Un día sin registro de sueño no es un día de cero horas.

---

## 15. Medición de bloque por tipo de ejercicio

`bloque` (antes `serie`) registra una unidad de trabajo dentro de una sesión
o un plan. "N series × M reps" no describe un sprint de 20 m ni un control
técnico: cada `ejercicio` declara su `tipo_medicion`, y eso determina qué
campos acepta el bloque. La validación vive en el service (un `CHECK` de
Postgres no puede consultar otra tabla).

| `tipo_medicion` | Campos permitidos | Ejemplo |
|---|---|---|
| `carga` | `series`, `reps`, `peso_kg` | Sentadilla explosiva: 4×6 @ 80kg |
| `distancia` | `reps`, `distancia_m` | Sprint acelerativo: 6 reps de 20m |
| `tiempo` | `series` (opcional), `duracion_s` | Plancha Copenhague: 3×30s |
| `tecnica` | `reps` o `duracion_s`, + `calidad` (1-5) | Control con muro: 20 reps, calidad 4 |

Todos los `tipo_medicion` aceptan `rpe` y `dolor_lumbar` (el real; el
objetivo en `bloque_plan` no tiene ni `dolor_lumbar` ni `calidad`, ver
`docs/schema.dbml`). Un campo fuera de la lista permitida para el
`tipo_medicion` del `ejercicio_id` del bloque es un
`InvarianteDeNegocioError` (422), no un `CHECK` de tabla.

**Nota de bloque vs. descripción de ejercicio.** Son dos cosas distintas y
no se mezclan:

- `ejercicio.descripcion` → **PERMANENTE**: qué es y cómo se ejecuta.
  Vive una sola vez en el catálogo.
- `bloque_plan.nota` / `bloque.nota` → **DE ESTA VEZ**: "al 60-70%", "con
  la zurda", "remo si no salen las dominadas". Vive colgada del bloque.

Lo que está terminantemente prohibido es empaquetar la nota en el nombre
del ejercicio ("Regate en conos al 60-70% (salida controlada)"): eso es un
duplicado disfrazado, y es exactamente lo que la deduplicación difusa del
importador (PLAN_IMPORT §6.1) está pensada para prevenir.

**Catálogo de ejercicio, caso especial**: a diferencia de `tipo_sesion` o
`zona_corporal`, `ejercicio` es el único catálogo que el usuario puede
ampliar (`POST /catalogos/ejercicios`). El universo de ejercicios de una
rutina real es abierto; los demás catálogos son taxonomías fijas del
negocio.

---

## 16. Delta plan vs real y forma del detalle

Las definiciones de esta sección son las que materializan el delta
plan-vs-real y el detalle de sesión que el SPEC del feature 2 (banco +
detalle) introdujo como parte nueva del dominio. Conviven con §1-§15 y no
las reemplazan: lo que ya estaba (carga, ACWR, Hooper, etc.) sigue igual.

### 16.1 Delta de bloque (real − objetivo)

Para cada `bloque` ejecutado que tenga un `bloque_plan` emparejado:

```
delta_campo = valor_real − valor_objetivo
```

Se calcula para `series`, `reps`, `peso_kg`, `distancia_m`, `duracion_s`.
**Si el objetivo es NULL, el delta es NULL** — nunca 0. Un faltante no se
sustituye por cero (mismo principio que §14).

Para rangos (`reps_min` / `reps_max`):

```
si reps_min <= reps_real <= reps_max   → delta = 0
si reps_real  > reps_max              → delta = reps_real − reps_max
si reps_real  < reps_min              → delta = reps_real − reps_min
```

El delta se mide contra el **límite más cercano**: dentro del rango, 0.

**Casos cubiertos por los tests** (referencia cruzada):

| Test (`tests/test_delta_bloque.py`) | Caso |
|---|---|
| `test_delta_bloque_carga` | 3×8@80 contra 3×8@90 → delta.peso −10 |
| `test_delta_reps_dentro_de_rango` | 7 reps contra rango 6-8 → 0 |
| `test_delta_reps_sobre_rango` | 10 reps contra rango 6-8 → +2 |
| `test_delta_reps_bajo_rango` | 5 reps contra rango 6-8 → −1 |
| `test_delta_objetivo_nulo` | todos los objetivos NULL → todos los deltas NULL |

### 16.2 Emparejamiento de bloques

Un `bloque` se empareja con su `bloque_plan` por la tupla
`(sesion_plan_id, orden)`. Consecuencias:

- **Bloque extra sin plan.** El usuario agregó un ejercicio que no estaba
  en el plan. No hay `bloque_plan` para esa tupla → su delta es NULL (todos
  los campos), su `objetivo` es NULL en el detalle. Test:
  `test_sesion_detalle_bloque_extra_sin_plan` y
  `test_sesion_detalle_delta_bloque_sin_plan`.
- **Bloque del plan no ejecutado.** El usuario omitió un ejercicio del
  plan. La sesión real no tiene `bloque` para esa tupla → entra en
  `bloques_no_ejecutados` del detalle con el objetivo del `bloque_plan`.
  Test: `test_sesion_detalle_bloques_no_ejecutados` (plan con 5 bloques,
  ejecuta 3 → 2 en la lista, ordenados por su `orden`).

### 16.3 Delta de sesión

A nivel de cabecera de sesión:

```
delta_duracion = duracion_min_real − duracion_min_est
delta_rpe      = rpe_real − rpe_objetivo
delta_carga    = carga_srpe_real − (duracion_min_est × rpe_objetivo)
```

`delta_carga` se calcula contra la **multiplicación** de los dos parámetros
del plan, no contra un campo directo: la planilla solo lleva
`duracion_min_est` y `rpe_objetivo` por separado. Si falta cualquiera de
los dos, `delta_carga` es NULL. Tests:
`test_sesion_detalle_delta_sesion_duracion`,
`test_sesion_detalle_delta_sesion_rpe`,
`test_sesion_detalle_delta_sesion_carga` (495 real contra 55×7=385 → +110).

Si la sesión es libre (sin `sesion_plan_id`): `plan = null`, `delta = null`
y `bloques_no_ejecutados = []`. Los bloques siguen apareciendo con
`objetivo = null` y delta todo NULL. Test:
`test_sesion_detalle_libre_plan_null`.

### 16.4 Fusión de ejercicios

Fusionar ejercicio `A` en `B` (mismo `tipo_medicion`, en otro caso 409):

1. Reasignar todos los `bloque.ejercicio_id = A` a `B`.
2. Reasignar todos los `bloque_plan.ejercicio_id = A` a `B`.
3. Marcar `A.activo = false`.
4. `A` no se borra: queda archivado para que el histórico siga trazable.

Precondiciones:

- `A.tipo_medicion == B.tipo_medicion` (si no, 409:
  `ConflicDeNegocioError`).
- `B.activo = true` (destino archivado, 409).
- `A.id != B.id` (auto-fusión, 422).

Tests: `test_fusion_reasigna_bloques` (conteos correctos),
`test_fusion_tipo_distinto_falla` (carga en tiempo → 409).

### 16.5 Umbral de round-trips en `GET /sesiones/{id}`

`GET /sesiones/{id}` dispara **9 queries** como techo, no 3 como proponía
la primera versión del SPEC. El conteo exacto con el shape completo del
SPEC §3.7 (sesión con plan + bloques + ciclo + molestias) es:

| # | Query | Por qué |
|---|---|---|
| 1 | Sesión + `tipo_sesion` + `sesion_plan` (cuando existe) | `joinedload` para FKs 1:1 |
| 2 | `sesion.bloques` | `selectinload` (1 batch, sin N+1) |
| 3 | `bloque.ejercicio` de cada bloque | `selectinload` anidado |
| 4 | `sesion_plan.bloques_planeados` | `selectinload` anidado al plan |
| 5 | `bloque_plan.ejercicio` de cada bloque planeado | `selectinload` anidado |
| 6 | `sesion_plan.ciclo_semana` | `selectinload` anidado al plan |
| 7 | `ciclo_semana.ciclo` | `selectinload` anidado a la semana |
| 8 | Molestias del día | 1 query |
| 9 | `zona` de cada molestia | `selectinload` anidado |

9 SELECTs totales, todos con batch-loading. Cualquier subida por encima
de 9 sería un N+1 nuevo (acceso por fila en vez de por colección), no un
costo del shape.

**Decisión del usuario.** El SPEC §4.2 proponía "máximo 3". El design
elevó el techo a 9 con documentación explícita: la combinación de las 4
colecciones (bloques, bloques_planeados, ciclo_semana+ciclo, molestias+
zonas) más la query principal + tipo_sesion + sesion_plan llega a 9 sin
N+1. Combinar `bloque.ejercicio` con `bloque_plan.ejercicio` exigiría un
JOIN o subquery manual sobre la misma tabla `ejercicio`, cosa que el
patrón `selectinload` anidado ya hace por separado sin riesgo de
duplicación. AGENTS §3.1 prohíbe desnormalizar el modelo para bajar el
conteo.

**Test de regresión:** `test_sesion_detalle_no_supera_9_queries`
(`tests/test_detalle_sesion.py`). Si en una iteración futura hace falta
cargar más colecciones (por ejemplo, `partido` cuando se agregue al
detalle), el umbral debe subir en consecuencia.

**Forma del detalle.** La forma que serializa este endpoint es
`SesionDetalleRead` (schemas/entrenamiento/sesion.py) con:

- Cabecera de sesión (id, fecha, duracion_min, rpe, carga_srpe, nota,
  registrado_en).
- `tipo_sesion` anidado (subset de `TipoSesionRead`: id, codigo, nombre).
- `plan` opcional (`PlanDetalleEnSesionRead`): ciclo (numero, semana,
  fase, objetivo) + objetivos + estado + rpe_objetivo + dia_sugerido.
  Sin `bloques_planeados` propios: ya están en `bloques_no_ejecutados`.
- `delta` opcional (`SesionDeltaRead`): duracion_min, rpe, carga_srpe,
  NULL si falta el objetivo.
- `bloques`: cada uno con ejercicio anidado + objetivo (subset de
  `BloquePlanRead`) + delta (subset con la diferencia real − objetivo).
- `bloques_no_ejecutados`: bloques del plan que la sesión no ejecutó, con
  su `objetivo` para que el usuario sepa qué se saltó.
- `molestias`: zona (string con el nombre, no el id) + intensidad.

La pantalla previa a ejecutar (`GET /planes/{id}`) reutiliza
`PlanDetalleRead` (schemas/entrenamiento/plan.py) con la cabecera
completa del plan + `ciclo` anidado + `bloques_planeados` (cada uno con su
ejercicio). Es la vista "antes de hacer" del mismo dominio que el detalle
de sesión expone como "después de hacer".
