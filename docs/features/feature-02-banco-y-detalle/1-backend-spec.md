# SPEC Backend — Banco de ejercicios y detalle de sesión

Destinatario: agente de backend.
Metodología: **TDD estricto**. Cada endpoint empieza por sus tests en rojo.
Al terminar, el agente supervisor lee el código, corre los tests y produce
`handshake.md` para el agente de frontend.

Documentos que gobiernan: `AGENTS.md`, `docs/ARCHITECTURE.md`,
`docs/REGLAS_NEGOCIO.md`, `docs/schema.dbml`. Si algo acá los contradice,
ellos ganan y hay que reportarlo.

---

## 0. Contexto

Dos huecos detectados en uso real:

1. No hay forma de ver ni editar el catálogo de ejercicios. Cuando la
   importación por JSON crea un ejercicio con nombre o descripción malos, no
   se puede corregir sin entrar a la base de datos.
2. No se puede abrir el detalle de una sesión. Eso hace invisibles
   `ejercicio.descripcion` y `bloque.nota`, que son justamente los campos que
   se agregaron para que el plan sea autoexplicativo.

---

## 1. Cambio de esquema

Uno solo:

```sql
ALTER TABLE ejercicio ADD COLUMN activo boolean NOT NULL DEFAULT true;
```

Los ejercicios **nunca se borran** si tienen uso: archivar es `activo=false`.
Borrar deja huérfanos los bloques históricos y destruye el progreso por
ejercicio, que es la razón de existir del registro por bloques.

Verificá antes contra `schema.dbml` que existan `ejercicio.descripcion`,
`bloque.nota` y `bloque_plan.nota`. Si falta alguna, agregala en la misma
migración.

---

## 2. Reglas de negocio nuevas

Agregar a `REGLAS_NEGOCIO.md` como §14.

### 2.1 Delta plan vs real

Para cada bloque ejecutado que tenga un `bloque_plan` asociado:

```
delta_campo = valor_real − valor_objetivo
```

Se calcula para `series`, `reps`, `peso_kg`, `distancia_m`, `duracion_s`.
Si el objetivo es NULL, el delta es NULL (no se asume cero).
Para rangos (`reps_min`/`reps_max`), el delta se mide contra el límite más
cercano: dentro del rango, delta 0.

A nivel de sesión:

```
delta_duracion = duracion_min_real − duracion_min_est
delta_rpe      = rpe_real − rpe_objetivo
delta_carga    = carga_srpe_real − (duracion_min_est × rpe_objetivo)
```

**El delta se calcula en el backend, no en el frontend.** Es una regla de
negocio y la fase 8 va a necesitar la misma definición en dbt.

### 2.2 Emparejamiento de bloques

Un `bloque` se empareja con su `bloque_plan` por `(sesion_plan_id, orden)`.
Si el usuario agregó bloques extra, no tienen plan y su delta es NULL.
Si omitió bloques del plan, se reportan como `no_ejecutados`.

### 2.3 Fusión de ejercicios

Fusionar A en B:
1. Reasignar todos los `bloque` y `bloque_plan` de A hacia B.
2. Marcar A como `activo = false`.
3. Nunca se borra A: el registro queda para trazabilidad.

Solo se permite si `A.tipo_medicion == B.tipo_medicion`. Fusionar tipos
distintos produciría bloques con campos que no corresponden a su ejercicio.

---

## 3. Endpoints

Todos bajo `/api/v1`, autenticados, y respetando las capas de
`ARCHITECTURE.md` §2: el router no consulta, el service no importa `fastapi`,
el repositorio no tiene reglas.

### 3.1 `GET /catalogos/ejercicios`

Query params: `q` (busca en nombre y descripción), `tipo_medicion`,
`tipo_sesion_id`, `activo` (default `true`), `orden` (`nombre` | `uso` |
`reciente`).

```json
{
  "items": [
    {
      "id": 12,
      "nombre": "Hip thrust",
      "tipo_medicion": "carga",
      "patron": "cadera_dominante",
      "carga_lumbar": "media",
      "descripcion": "…",
      "activo": true,
      "usos": 14,
      "ultima_vez": "2026-08-22"
    }
  ],
  "total": 47
}
```

`usos` cuenta filas de `bloque`, no de `bloque_plan`: mide lo ejecutado, no
lo planeado.

### 3.2 `GET /catalogos/ejercicios/{id}`

Igual que arriba más:

```json
{
  "historial": [
    { "fecha": "2026-08-22", "sesion_id": "…", "series": 3, "reps": 8,
      "peso_kg": 90, "rpe": 8, "nota": "…" }
  ],
  "posibles_duplicados": [ { "id": 31, "nombre": "Hip thrust barra", "similitud": 0.82 } ]
}
```

`historial`: últimas 5 ejecuciones, más recientes primero.
`posibles_duplicados`: mismo `tipo_medicion`, similitud normalizada ≥ 0.75.

### 3.3 `PATCH /catalogos/ejercicios/{id}`

Editables: `nombre`, `descripcion`, `patron`, `carga_lumbar`, `activo`.
**`tipo_medicion` NO es editable**: invalidaría los bloques históricos.
Si llega en el body → `422` con mensaje explícito.
Nombre duplicado (normalizado) contra otro activo → `409`.

### 3.4 `POST /catalogos/ejercicios`

Crear a mano. Mismos campos, `tipo_medicion` obligatorio.

### 3.5 `POST /catalogos/ejercicios/{id}/fusionar`

Body: `{ "destino_id": 12 }`. Aplica §2.3.

```json
{ "bloques_reasignados": 9, "bloques_plan_reasignados": 3, "origen_archivado": true }
```

Errores: `tipo_medicion` distinto → `409`. `destino_id == id` → `422`.
Destino inactivo → `409`.

### 3.6 `DELETE /catalogos/ejercicios/{id}`

Solo si `usos == 0` y no aparece en ningún `bloque_plan`. Si no, `409` con
mensaje sugiriendo archivar o fusionar.

### 3.7 `GET /sesiones/{id}`

El endpoint central de este trabajo.

```json
{
  "id": "…",
  "fecha": "2026-08-24",
  "tipo_sesion": { "id": 1, "codigo": "fuerza", "nombre": "Fuerza y potencia" },
  "duracion_min": 55,
  "rpe": 9,
  "carga_srpe": 495,
  "nota": "…",
  "plan": {
    "id": 8,
    "nombre": "Full-body y core",
    "objetivo": "…",
    "nota": "…",
    "duracion_min_est": 55,
    "rpe_objetivo": 7,
    "estado": "cumplido",
    "dia_sugerido": 3,
    "ciclo": { "numero": 2, "semana": 1, "fase": "readaptacion" }
  },
  "delta": { "duracion": 0, "rpe": 2, "carga": 110 },
  "bloques": [
    {
      "id": 101,
      "orden": 1,
      "ejercicio": {
        "id": 12, "nombre": "Hip thrust", "tipo_medicion": "carga",
        "descripcion": "…", "carga_lumbar": "media"
      },
      "nota": "…",
      "real":     { "series": 3, "reps": 8, "peso_kg": 90, "rpe": 8, "dolor_lumbar": false },
      "objetivo": { "series": 3, "reps_min": 6, "reps_max": 8, "peso_objetivo_kg": 90 },
      "delta":    { "series": 0, "reps": 0, "peso_kg": 0 }
    }
  ],
  "bloques_no_ejecutados": [
    { "orden": 7, "ejercicio": { "id": 40, "nombre": "Bird-dog" },
      "objetivo": { "series": 3, "reps": 8 } }
  ],
  "molestias": [ { "zona": "isquiotibiales", "intensidad": 4 } ]
}
```

Notas de implementación: una sola query con `selectinload` para evitar N+1.
`plan`, `delta` y `bloques_no_ejecutados` son `null` o vacíos si la sesión fue
libre.

### 3.8 `GET /planes/{id}`

Misma forma, pero solo la parte de plan: sus `bloque_plan` con el ejercicio
anidado (nombre, descripción, tipo de medición) y la nota de cada bloque.
Alimenta la pantalla previa a ejecutar.

---

## 4. Tests (TDD — se escriben primero)

Contra Postgres real, nunca SQLite: hay columnas generadas, enums nativos y
`EXTRACT(EPOCH …)`.

### 4.1 Unitarios de servicio

| Test | Verifica |
|---|---|
| `test_delta_bloque_carga` | 3×8@80 contra objetivo 3×8@90 → delta peso −10 |
| `test_delta_reps_dentro_de_rango` | 7 reps contra rango 6–8 → delta 0 |
| `test_delta_reps_sobre_rango` | 10 reps contra rango 6–8 → delta +2 |
| `test_delta_objetivo_nulo` | objetivo NULL → delta NULL, nunca 0 |
| `test_delta_sesion_sin_plan` | sesión libre → `plan` y `delta` en null |
| `test_bloques_no_ejecutados` | plan con 5, ejecutados 3 → 2 en la lista |
| `test_bloque_extra_sin_plan` | bloque sin `bloque_plan` → delta NULL |
| `test_similitud_normalizada` | "Pallof press (anti-rotacion)" ≈ "Pallof press" ≥ 0.75 |
| `test_similitud_ignora_tildes` | "Elevacion de talon" ≈ "Elevación de talón" |
| `test_fusion_reasigna_bloques` | conteos correctos, origen archivado |
| `test_fusion_tipo_distinto_falla` | `carga` en `tiempo` → 409 |

### 4.2 Integración de endpoints

Para cada uno: camino feliz, `404` con id inexistente, `401` sin token.
Además:

- `PATCH` con `tipo_medicion` → `422`.
- `PATCH` con nombre duplicado normalizado → `409`.
- `DELETE` de ejercicio con uso → `409`.
- `DELETE` de ejercicio sin uso → `204`.
- `GET /sesiones/{id}` de sesión con plan → trae `plan`, `delta` y objetivos.
- `GET /sesiones/{id}` de sesión libre → `plan: null`, sin romper.
- `GET /catalogos/ejercicios?q=` con acento y sin acento → mismos resultados.
- Conteo de queries en `GET /sesiones/{id}`: máximo 3. Es un test de
  regresión contra N+1, y hay que escribirlo.

---

## 5. Lo que NO entra

- Cálculo de ACWR, monotonía o Estado. Fase 8.
- Progresión automática de cargas entre ciclos.
- Cualquier UI.
- Modificar el importador de JSON.

---

## 6. Contrato para `handshake.md`

El supervisor debe dejar, como mínimo:

- Endpoints implementados con su ruta, método y forma exacta de respuesta.
- Códigos de error por endpoint y en qué caso se disparan.
- Nombre y ubicación de los tipos TypeScript generados desde el OpenAPI.
- Migración aplicada y su revisión.
- Salida de `make lint` y `make test`.
- Desviaciones respecto de esta especificación, con su justificación.
- Lo que quedó sin hacer.