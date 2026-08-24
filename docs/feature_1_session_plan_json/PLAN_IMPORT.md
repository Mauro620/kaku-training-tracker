# Importación de plan semanal por JSON

Este documento define el formato que Kaku acepta para cargar la planificación
de una semana completa, y cómo cada campo aterriza en el esquema relacional.

Es también el documento que el usuario le pasa a un LLM para que genere el
plan: pegarlo junto con "planeame la semana 2 del ciclo 1" debería producir
un JSON válido.

---

## 1. Por qué existe

Planear es trabajo de escritorio. Registrar es trabajo de campo. Hoy la app
obliga a hacer lo primero en la cancha: buscar el ejercicio, crearlo si no
existe, elegir tipo de medición, llenar campos.

Con importación, el domingo se carga la semana entera y en el campo solo se
confirman números sobre filas que ya existen.

---

## 2. Cambios de esquema necesarios

El esquema actual ya cubre casi todo (`bloque_plan` tiene los campos
objetivo, `ejercicio.tipo_medicion` existe). Faltan dos cosas.

### 2.1 Estado del plan

```sql
CREATE TYPE estado_sesion_plan AS ENUM
  ('pendiente', 'cumplido', 'movido', 'descartado');

ALTER TABLE sesion_plan
  ADD COLUMN estado estado_sesion_plan NOT NULL DEFAULT 'pendiente';
```

| Estado | Significado |
|---|---|
| `pendiente` | Todavía no se ejecutó |
| `cumplido` | Se ejecutó; existe una `sesion` que lo referencia |
| `movido` | Se ejecutó otro día de la misma semana. Sigue contando para el cumplimiento |
| `descartado` | No se va a hacer. No cuenta como incumplimiento si el usuario lo declara |

`movido` y `cumplido` se resuelven solos: si existe una `sesion` con ese
`sesion_plan_id` y su `fecha` cae en un `dia_semana` distinto al
`dia_sugerido`, es `movido`. No lo elige el usuario.

### 2.2 Clave de importación (idempotencia)

```sql
ALTER TABLE sesion_plan ADD COLUMN clave_import varchar(80);
CREATE UNIQUE INDEX ix_sesion_plan_clave_import
  ON sesion_plan (ciclo_semana_id, clave_import)
  WHERE clave_import IS NOT NULL;
```

`clave_import` la genera el importador como
`{dia_sugerido}-{tipo_sesion_codigo}` (ej. `2-balon_distribucion`).
Reimportar la misma semana **reemplaza** los planes con la misma clave en
lugar de duplicarlos.

**Los planes en estado `cumplido` o `movido` nunca se reemplazan.** Si el
JSON trae una sesión cuyo plan ya se ejecutó, el importador la ignora y lo
reporta como advertencia. El histórico es intocable.

---

## 3. Mapeo JSON → esquema

| Campo JSON | Tabla | Columna |
|---|---|---|
| `ciclo.numero` | `ciclo` | `numero` (busca o crea) |
| `ciclo.objetivo` | `ciclo` | `objetivo` |
| `ciclo.fecha_inicio` | `ciclo` | `fecha_inicio` |
| `ciclo.semanas` | `ciclo` | `semanas` |
| `semana.numero` | `ciclo_semana` | `numero` |
| `semana.fase` | `ciclo_semana` | `fase` |
| `semana.rpe_objetivo` | `ciclo_semana` | `rpe_objetivo_min` / `max` |
| `semana.volumen_pct` | `ciclo_semana` | `volumen_pct` |
| — derivado — | `ciclo_semana_composicion` | se calcula contando sesiones por tipo |
| `sesion.dia` | `sesion_plan` | `dia_sugerido` (0=lunes … 6=domingo) |
| `sesion.tipo` | `sesion_plan` | `tipo_sesion_id` (por `codigo`) |
| `sesion.objetivo` | `sesion_plan` | `objetivo` |
| `sesion.duracion_min` | `sesion_plan` | `duracion_min_est` |
| `sesion.rpe_objetivo` | `sesion_plan` | `rpe_objetivo` |
| `bloque.ejercicio` | `ejercicio` | `nombre` (busca o crea) |
| `bloque.tipo_medicion` | `ejercicio` | `tipo_medicion` (solo al crear) |
| `bloque.series` | `bloque_plan` | `series` |
| `bloque.reps` / `reps_min`,`reps_max` | `bloque_plan` | `reps_min` / `reps_max` |
| `bloque.peso_kg` | `bloque_plan` | `peso_objetivo_kg` |
| `bloque.distancia_m` | `bloque_plan` | `distancia_objetivo_m` |
| `bloque.duracion_s` | `bloque_plan` | `duracion_objetivo_s` |

**La composición semanal no se declara, se deriva.** Si el JSON trae 2
sesiones de `fuerza` y 1 de `resistencia`, eso *es* la composición. Declararla
aparte abre la puerta a que no coincida con las sesiones.

---

## 4. Campos por tipo de medición

Cada `ejercicio` declara su `tipo_medicion`, y eso determina qué campos
acepta su bloque. Enviar un campo que no aplica es un error de validación,
no algo que se ignora en silencio.

| `tipo_medicion` | Campos válidos en el bloque |
|---|---|
| `carga` | `series`, `reps` o `reps_min`+`reps_max`, `peso_kg` |
| `distancia` | `reps`, `distancia_m` |
| `tiempo` | `duracion_s` |
| `tecnica` | `reps` o `duracion_s` |

`calidad` no existe en el plan a propósito: es una medida de ejecución, no
algo que se planifique.

---

## 5. Códigos válidos

**`sesion.tipo`** — `fuerza`, `velocidad_salto`, `resistencia`,
`balon_control`, `balon_distribucion`, `recuperacion`, `partido`.

**`semana.fase`** — `readaptacion`, `carga`, `descarga`.

**`bloque.tipo_medicion`** — `carga`, `distancia`, `tiempo`, `tecnica`.

**`sesion.dia`** — entero 0–6, donde 0 es lunes.

---

## 6. Reglas de validación

El importador rechaza el JSON entero si:

- Un `tipo` o `fase` no está en el catálogo.
- `semana.numero` excede `ciclo.semanas`.
- Un bloque trae campos que no corresponden a su `tipo_medicion`.
- Un ejercicio existente aparece con un `tipo_medicion` distinto al que ya
  tiene. **Nunca se sobrescribe un ejercicio existente**: cambiar su tipo
  invalidaría los bloques históricos.
- Dos sesiones comparten `dia` y `tipo` dentro de la misma semana.

Devuelve advertencias sin bloquear si:

- Dos sesiones de `fuerza` quedan a menos de 48 h (`fuerza_separacion_min_horas`).
- Una sesión de demanda alta cae en las 24 h previas a un `partido`
  (`partido_ventana_previa_horas`).
- Un plan ya ejecutado sería reemplazado (se conserva el original).
- Se crearon ejercicios nuevos (lista de cuáles).

---

## 7. Respuesta del endpoint

```json
{
  "ciclo_id": 1,
  "ciclo_semana_id": 2,
  "sesiones_creadas": 6,
  "sesiones_reemplazadas": 1,
  "sesiones_omitidas": 0,
  "ejercicios_creados": ["Pase largo diagonal"],
  "advertencias": [
    "Fuerza el martes y el miércoles: 24 h de separación, se recomiendan 48."
  ]
}
```

---

## 8. Ejemplo completo

Ver `plan-ejemplo.json` en esta misma carpeta. Es una semana real de
Kaku: 7 sesiones, los cuatro tipos de medición, y ejercicios que ya
existen en el catálogo.
