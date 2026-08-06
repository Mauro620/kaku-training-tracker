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

## 12. Nutrición

Macros de una receta:

```
macro_receta = Σ (macro_alimento_por_100g × cantidad_g ÷ 100)
```

Para cada uno de kcal, proteína, carbohidrato, grasa y fibra.

Macros del día: suma de las recetas registradas más los `comida_item` sueltos.

Todos los alimentos se almacenan con `estado_pesaje = 'crudo'`. Si una fuente
da un valor cocido, se convierte antes de sembrarlo. Mezclar ambos estados
introduce un error cercano al 30% en carnes.

Indicadores semanales, que son los que ve el usuario:

```
pct_comidas_con_proteina = comidas con ≥ 20 g de proteína ÷ total × 100
pct_comidas_con_vegetal  = comidas con ≥ 1 alimento de grupo 'verdura' ÷ total × 100
```

"Vegetal" significa exactamente `alimento.grupo = 'verdura'`. Fruta,
tubérculo y leguminosa **no** cuentan para este indicador.

El objetivo diario de proteína se calcula como
`peso_kg × proteina_g_por_kg`, con el peso del `medida_corporal` más
reciente. Se muestra como referencia, **no como meta a perseguir**.

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

---

## 14. Redondeo y nulos

- Los cálculos internos usan `Decimal` o `float` sin redondear.
- El redondeo ocurre solo al serializar: 3 decimales para ACWR y monotonía,
  1 para horas y porcentajes, entero para el Estado.
- Un dato faltante es NULL y se propaga como NULL. **Nunca se sustituye por
  cero.** Un día sin registro de sueño no es un día de cero horas.
