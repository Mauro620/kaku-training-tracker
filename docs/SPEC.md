# Especificación — App de rendimiento personal

Sistema de registro y análisis para futbolista universitario en preparación.
Regla rectora: **el registro diario nunca supera los 2 minutos**, repartidos en
micro-momentos. Si un campo no cambia una decisión, no existe.

---

## 1. Presupuesto de tiempo diario

No es un formulario de 2 minutos. Son cuatro momentos cortos:

| Momento | Duración | Qué se registra |
|---|---|---|
| Al despertar | 30 s | Sueño + bienestar (4 sliders) |
| Post-sesión | 40 s | Duración, RPE, molestia, nota |
| Después de comer | 30 s | 3 taps sobre recetas guardadas |
| Antes de dormir | 20 s | Checklist de hábitos |

Cualquier feature que rompa este presupuesto se rechaza, sin importar cuán
interesante sea el dato.

---

## 2. Métricas que se registran

### 2.1 Diarias (obligatorias)

| Campo | Tipo | Notas |
|---|---|---|
| `hora_acostarse` | time | Autocompletable desde Health |
| `hora_despertar` | time | `horas_sueno` se deriva, no se pide |
| `celular_fuera` | bool | Vive en `registro_sueno`, no es un hábito |
| `sueno_pobre` | 1–5 | Bienestar. 1 es bueno, 5 es malo |
| `fatiga` | 1–5 | Bienestar |
| `dolor_muscular` | 1–5 | Bienestar |
| `estres` | 1–5 | Bienestar |

Los cuatro ítems de bienestar forman el índice de Hooper. Es la medida más
sensible a cambios de carga que existe y cuesta 10 segundos.

### 2.2 Por sesión (0 a N por día)

| Campo | Tipo | Notas |
|---|---|---|
| `tipo_sesion` | enum | Fuerza · Velocidad+Salto · Resistencia · Balón control · Balón distribución · Recuperación · Partido |
| `duracion_min` | int | |
| `rpe` | 1–10 | Preguntar ~30 min después de terminar, no al instante |
| `nota` | text | Opcional |

Por serie, solo en sesiones de fuerza:
`ejercicio`, `series`, `reps`, `peso_kg`, `rpe`, `dolor_lumbar` (bool).

`carga_srpe = rpe × duracion_min` — derivada, nunca se captura.

### 2.3 Molestia (solo si existe)

`zona` (enum), `intensidad` 0–10. Si no hay molestia, no hay fila. No se
pregunta todos los días.

### 2.4 Hábitos (checklist dinámico)

Tabla, no columnas. Agregar un hábito es un INSERT, no una migración.

```
habito           (id, nombre, activo, orden)
habito_registro  (fecha, habito_id, valor)
```

Semilla: creatina, magnesio, estiramiento, hidratación.

"Celular fuera" **no** es un hábito: es `registro_sueno.celular_fuera`, que se
llena en el mismo formulario del despertar. Tenerlo en los dos lados es el
mismo hecho en dos filas que van a divergir.

### 2.5 Nutrición

Se registra la **receta**, no los ingredientes. Cada comida recurrente se
calibra una vez; después registrar es un tap.

```
alimento     (id, nombre, grupo, estado_pesaje, kcal, proteina, carbo, grasa, fibra)
receta       (id, nombre, momento)
receta_item  (receta_id, alimento_id, cantidad)
comida_log   (fecha, momento, receta_id)
despensa     (alimento_id, imprescindible)
```

`estado_pesaje` es crudo o cocido. Convención del proyecto: **siempre crudo**.
Mezclar los dos introduce un error de ~30% en carnes.

Universo cerrado: ~40 alimentos, los de tu despensa. Fuente para alimentos
locales: Tabla de Composición de Alimentos Colombianos (ICBF).

### 2.6 Periódicas

| Métrica | Frecuencia |
|---|---|
| Peso corporal (ayunas, misma hora) | Semanal |
| CMJ | Semanal |
| Sprint 10 m, broad jump | Cada 4 semanas |
| RSA 6×30 m (% decremento) | Cada 4 semanas |
| Yo-Yo IR1 (distancia) | Cada 4 semanas |
| Partido: minutos, goles, asistencias, recuperaciones, RPE | Por partido |

```
test_fisico  (fecha, tipo, superficie, condiciones)
test_intento (test_id, numero, valor)
```

Un solo modelo de intento para todos los tests: RSA son 6, CMJ es el mejor de
3, Yo-Yo es 1. En Yo-Yo IR1 `valor` es la distancia; **el nivel se deriva de
la distancia** con la tabla del protocolo, no se captura.

`pct_decremento = 100 × (suma_tiempos ÷ (mejor × n)) − 100`
Bueno < 5%. Problema > 8%.

---

## 3. Lo que NO se registra

Volumen total levantado · 1RM estimado · calorías al gramo · pasos · macros
diarios perseguidos como meta · cualquier campo que no alimente una decisión.

---

## 4. Conclusiones por horizonte

### Cada día

- **Estado (0–100)** → entrenar duro, moderado o recuperar.
- **¿Comí proteína y carbos?** Semáforo, no suma.
- **¿Molestia hoy?** Si aparece, se marca el patrón.

### Cada semana

- **ACWR** = carga 7 d ÷ promedio semanal de 28 d. Zona 0.8–1.3.
- **Monotonía** = media diaria ÷ desviación estándar. Alta = todos los días
  iguales, señal de riesgo aunque la carga total sea normal.
- **Deuda de sueño** acumulada contra objetivo de 7 h.
- **Adherencia**: sesiones planeadas vs hechas, por tipo.
- **% de comidas con proteína / con vegetal.**
- **Frecuencia de molestia**: cuántos de los últimos 7 días.

### Cada mes (= fin de ciclo)

- **¿La fuerza transfirió?** Sprint, CMJ y broad jump contra la línea base.
  Si la fuerza sube y estos no, hay que meter más pliometría y velocidad.
- **¿Mejoró la resistencia?** Yo-Yo y % de decremento contra el ciclo anterior.
- **Correlación sueño × RPE**: ¿a la misma carga, tu RPE sube cuando dormiste
  menos de 7 h? Con n=1 esto es ruidoso hasta los ~60 días; trátalo como
  hipótesis, no como hallazgo.
- **RPE de partido vs minutos jugados** → déficit aeróbico medido en contexto real.
- Decisión de carga para el ciclo siguiente.

---

## 5. Utilidades reales

### 5.1 Estado del día

Heurística, calibrable. Empieza en 100 y penaliza:

| Factor | Penalización |
|---|---|
| Deuda de sueño 7 d | −2 por hora, tope −20 |
| Hooper sobre línea base | −3 por punto, tope −25 |
| ACWR 1.3–1.5 | −8 |
| ACWR > 1.5 | −15 |
| Molestia hoy | −2 × intensidad, tope −20 |
| CMJ caído > 5% vs base | −15 |

Bandas: ≥ 75 carga · 55–74 moderado · < 55 recuperación.
Siempre se muestran las razones, nunca solo el número.

### 5.2 Señal de descarga

Se dispara con cualquiera de las tres, que ya están en el dashboard de Notion:
RPE 9–10 en tres sesiones seguidas sin que suban los pesos · métricas de
velocidad o salto estancadas o cayendo · molestia recurrente.

### 5.3 Semáforo de cerveza

No es un premio por esfuerzo, es un cálculo de costo. Verde solo si:
sin deuda de sueño significativa · sin sesión de alta demanda ni partido en
48 h · ACWR ≤ 1.4 · sin molestia recurrente. Devuelve las razones, no un
veredicto.

### 5.4 Alerta de lumbar

Si la molestia lumbar aparece 3+ veces en 14 días, la app no sugiere ejercicios:
sugiere fisioterapeuta y muestra el historial para llevarlo a consulta.

---

## 6. Ingeniería de datos

### 6.1 Capas

**Bronze** — eventos crudos tal como llegaron del dispositivo, inmutables, con
`idempotency_key` y `client_timestamp`. Nada se borra ni se corrige aquí.

**Silver** — hechos normalizados y deduplicados. Es donde vive el esquema
estrella.

```
dim_fecha · dim_tipo_sesion · dim_ejercicio · dim_alimento · dim_habito
fact_sesion · fact_serie · fact_sueno · fact_bienestar · fact_habito
fact_comida · fact_molestia · fact_partido · fact_test
```

**Gold** — marts que consume la app. Una tabla por pantalla, no por entidad:
`mart_estado_diario`, `mart_carga_semanal`, `mart_nutricion_semanal`,
`mart_progreso_ciclo`.

### 6.2 Transformación

dbt sobre Postgres, corriendo cada noche (cron o GitHub Actions). Tests de dbt
sobre lo que importa: RPE entre 1 y 10, duración positiva, no más de una fila
de sueño por fecha, ACWR nulo si hay menos de 28 días de historia.

Ventanas móviles con funciones de ventana de SQL, no en Python:

```sql
avg(carga_srpe) over (order by fecha rows between 27 preceding and current row)
```

### 6.3 Sincronización

Offline-first no es opcional: se registra en el gimnasio, en la cancha y en la
cama. IndexedDB (Dexie) + cola de salida + endpoint de sync con
`idempotency_key` por evento. Última escritura gana; los conflictos reales son
casi inexistentes con un solo usuario.

### 6.4 Ingesta externa

- Apple Health / Health Connect → sueño, peso, frecuencia cardiaca en reposo.
- Backfill único desde la base `Registro diario` de Notion vía API.
- Excel de horarios → `dim_bloque_horario`, solo lectura.
- Excel de finanzas → **no se toca**.

### 6.5 Salida

Exportación a CSV siempre disponible. Los datos son tuyos y tienen que poder
salir sin la app.

---

## 7. Navegación

Cuatro pestañas. Ninguna más.

### Hoy
Estado con sus razones · registro rápido según el momento del día · próxima
sesión · semáforo de cerveza. Es la pantalla que se abre por defecto y la
única que se usa a diario.

### Entreno
Ciclo actual con su fase y semana · plan de la sesión (objetivo, duración,
series, reps, peso esperado) · registro del resultado real · historial ·
el delta entre plan y real, que es donde está la señal de fatiga.

### Cocina
Registro de comidas por tap sobre recetas · biblioteca de recetas con sus
macros calculados · despensa con lista de imprescindibles y lo que falta ·
resumen semanal de composición.

### Progreso
Carga de 4 semanas con ACWR y monotonía · tendencias de sueño y bienestar ·
tests físicos contra línea base · registro de partidos · fin de ciclo.

---

## 8. Orden de construcción

| Fase | Contenido | Criterio de salida |
|---|---|---|
| v0 | Pestaña Hoy: sueño, bienestar, hábitos, sesión. Offline + sync. | 14 días seguidos de registro |
| v1 | Lectura: historial, carga semanal. Backfill de Notion. | 28 días cargados |
| v2 | Marts en dbt, ACWR, Estado, señales. Pestaña Progreso. | Las señales coinciden con cómo te sientes |
| v3 | Cocina completa, tests físicos, Health, notificaciones. | — |

El ACWR necesita 28 días de historia para significar algo. Construir la capa
de métricas antes de tener datos es construir sobre una tabla vacía.

---

## 9. Advertencias

- Las fórmulas de esta especificación son heurísticas de la literatura de
  ciencias del deporte, no verdades sobre tu cuerpo. Se calibran con tus datos.
- Cronometrar 30 m a mano tiene ~0.2 s de error sobre sprints de ~4 s: 5% de
  ruido, del mismo tamaño que la señal. Usa siempre el mismo método, la misma
  persona y la misma superficie, y lee la tendencia, no el valor.
- El módulo de nutrición sirve para conocer tus comidas durante dos o tres
  semanas y después dejar de sumar. Si el conteo se vuelve el objetivo, el
  módulo falló.
- La molestia se registra para tener historial, no para autodiagnosticarse.
