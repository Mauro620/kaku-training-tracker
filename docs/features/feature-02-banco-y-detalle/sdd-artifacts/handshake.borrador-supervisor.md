# Handshake: Banco de ejercicios y detalle de sesión (backend)

> Estado del backend al cierre del feature 2. Es el contrato entre backend
> y frontend. **Lo que no está acá no existe.**

- **Repo**: `/home/mcorreace/Projects/training_tracker`
- **Rama**: `feature/be-banco-detalle` (22 commits sobre `main`)
- **Versión del backend al cierre**: `apps/api/alembic/versions/f1a2b3c4d5e6_agregar_activo_a_ejercicio.py` (down_revision `e4a7b93c218d`).
- **OpenAPI**: `GET /openapi.json` en el dev server.
- **Tipos a generar**: con `openapi-typescript` apuntando al OpenAPI, salida en `packages/contracts`.

---

## 1. Endpoints implementados

> Convenciones: todos requieren `Authorization: Bearer <token>`. Los tokens
> los entrega `POST /api/v1/auth/login`. Los ids internos son `int` salvo
> `sesion.id` y `usuario.id` que son `UUID`. Las fechas en formato ISO-8601
> (`YYYY-MM-DD`). Los decimales son strings (`"75.0"`, `"0.5"`) para
> evitar pérdida de precisión en JSON.

### `GET /api/v1/catalogos/ejercicios`
- **Descripción**: Lista los ejercicios del catálogo con búsqueda, filtros y orden. Precomputa `usos` (cantidad de filas en `bloque` con este ejercicio) y `ultima_vez` (fecha del último uso) en una sola query.
- **Query params**:
  - `q` (opcional, `string`): se normaliza (sin acentos, minúsculas, colapsa espacios) y se busca con `ILIKE` en `nombre` y `descripcion`. El matching es por substring, no full-text.
  - `tipo_medicion` (opcional, enum): `carga` | `distancia` | `tiempo` | `tecnica`.
  - `tipo_sesion_id` (opcional, `int`): filtra por el tipo de sesión asociado.
  - `activo` (default `true`, `bool`): si `true` excluye archivados; `false` lista solo los archivados.
  - `orden` (default `nombre`, enum): `nombre` (alfabético) | `uso` (descendente por `usos`) | `reciente` (descendente por `ultima_vez`, NULL al final).
- **Respuesta exitosa** (200): `EjercicioListRead` con `items: EjercicioListItem[]` y `total: int`. `total` es la cantidad de items en la respuesta (sin paginación todavía: el universo es chico).
- **Códigos de error**:
  - `401` sin token.
  - `422` si `tipo_medicion` o `orden` no son valores válidos del enum.

### `GET /api/v1/catalogos/ejercicios/{id}`
- **Descripción**: Detalle completo de un ejercicio: datos básicos + las últimas 5 ejecuciones (`historial`, ordenado por fecha desc) + candidatos a duplicado (`posibles_duplicados`, calculados en el service con `rapidfuzz.fuzz.token_set_ratio >= 0.75` sobre el nombre normalizado, mismo `tipo_medicion`, excluyendo el propio).
- **Path params**:
  - `id` (int): id del ejercicio.
- **Respuesta exitosa** (200): `EjercicioDetalleRead`.
- **Códigos de error**:
  - `401` sin token.
  - `404` si el ejercicio no existe (incluye "existe pero es de otro usuario" — el backend no distingue, evita filtración de existencia).

### `POST /api/v1/catalogos/ejercicios`
- **Descripción**: Crea un ejercicio nuevo. Es el único catálogo que el usuario puede ampliar (los demás se siembran).
- **Body** (`EjercicioCreate`):
  - `nombre` (string, 1–80 chars): **obligatorio**.
  - `tipo_medicion` (enum: `carga` | `distancia` | `tiempo` | `tecnica`): **obligatorio**.
  - `descripcion` (string | null): opcional.
  - `patron` (string, max 40 chars): opcional (default `null`).
  - `carga_lumbar` (enum: `alta` | `media` | `baja`): opcional (default `null`).
  - **No se acepta** ningún otro campo (Pydantic `extra="forbid"`).
- **Respuesta exitosa** (200, no 201): `EjercicioRead`.
- **Códigos de error**:
  - `401` sin token.
  - `409` si el `nombre` normalizado (sin acentos, minúsculas, colapsado) coincide con otro ejercicio activo.

### `PATCH /api/v1/catalogos/ejercicios/{id}`
- **Descripción**: Edita un ejercicio. `tipo_medicion` **no es editable** porque cambiarlo invalidaría bloques históricos (REGLAS_NEGOCIO §15).
- **Body** (`EjercicioUpdate`, todos los campos opcionales):
  - `nombre` (string, 1–80): si se manda, se valida duplicado contra otros activos.
  - `descripcion` (string | null): string vacío `""` se traduce a `null` en el service.
  - `patron` (string, max 40): opcional.
  - `carga_lumbar` (enum): opcional.
  - `activo` (bool): opcional.
  - **No se acepta** ningún otro campo (Pydantic `extra="forbid"`); en particular `tipo_medicion` devuelve 422 si llega.
- **Respuesta exitosa** (200): `EjercicioRead`.
- **Códigos de error**:
  - `401` sin token.
  - `404` si el ejercicio no existe.
  - `422` si el body trae `tipo_medicion` u otro campo no permitido.
  - `409` si el `nombre` normalizado choca con otro activo.

### `POST /api/v1/catalogos/ejercicios/{id}/fusionar`
- **Descripción**: Fusiona el ejercicio `origen` (en el path) en el `destino` (en el body). Reasigna todos los bloques reales (`bloque.ejercicio_id`) y planeados (`bloque_plan.ejercicio_id`) al destino, y archiva el origen (`activo=false`). Es **una sola transacción**: si algo falla, no se aplica nada.
- **Path params**:
  - `id` (int): id del ejercicio **origen**.
- **Body** (`EjercicioFusionarCreate`):
  - `destino_id` (int): id del ejercicio que se queda. **Obligatorio**.
- **Respuesta exitosa** (200): `FusionResultadoRead` con los conteos por tabla:
  - `origen_id`, `destino_id`, `bloques_reasignados`, `bloques_plan_reasignados`.
- **Códigos de error**:
  - `401` sin token.
  - `404` si el origen o el destino no existen.
  - `422` si `destino_id == id` (path) — no se puede fusionar consigo mismo.
  - `409` si los tipos de medición son distintos (no se pueden fusionar ejercicios de naturalezas diferentes).
  - `409` si el destino está archivado (`activo=false`) — archivar el destino no tiene sentido semántico.

### `DELETE /api/v1/catalogos/ejercicios/{id}`
- **Descripción**: Elimina físicamente un ejercicio. Solo procede si `uso == 0` (sin bloques reales) **y** sin `bloque_plan` referenciándolo. Si tiene uso, devuelve 409 con un mensaje que sugiere archivar (`PATCH` con `activo=false`) o fusionar.
- **Path params**:
  - `id` (int): id del ejercicio.
- **Respuesta exitosa** (204): sin body.
- **Códigos de error**:
  - `401` sin token.
  - `404` si el ejercicio no existe.
  - `409` si tiene uso o aparece en `bloque_plan`. El mensaje es accionable: dice "archivá el ejercicio" o "fusioná con otro".

### `GET /api/v1/sesiones/{id}`
- **Descripción**: Detalle completo de una sesión (cabecera + tipo_sesion anidado + plan con ciclo + delta de sesión + bloques con ejercicio/objetivo/delta + bloques_no_ejecutados + molestias con zona.nombre). **9 round-trips** a la base (ver §6 desviación 1). Si la sesión no tiene plan asociado (`sesion_plan_id = null`), devuelve `plan: null`, `delta: null`, `bloques_no_ejecutados: []`.
- **Path params**:
  - `id` (UUID): id de la sesión.
- **Respuesta exitosa** (200): `SesionDetalleRead`.
- **Códigos de error**:
  - `401` sin token.
  - `404` si la sesión no existe o no es del usuario actual.

### `GET /api/v1/planes/{id}`
- **Descripción**: Detalle de un plan de sesión con su ciclo (`ciclo_semana → ciclo`) anidado y sus bloques planeados (`bloque_plan` con `ejercicio` anidado) ordenados por `orden` ASC. Es la pantalla previa a ejecutar.
- **Path params**:
  - `id` (int): id del `sesion_plan`.
- **Respuesta exitosa** (200): `PlanDetalleRead`.
- **Códigos de error**:
  - `401` sin token.
  - `404` si el plan no existe o no es del usuario actual.

> Endpoints **fuera de scope de este feature** (existen pero no los modificó
> feature 2; el supervisor no debe pedir cambios acá):
> `GET /catalogos/tipos-sesion`, `GET /catalogos/zonas-corporales`,
> `GET /catalogos/tipos-test`, `POST /sesiones`, `GET /sesiones`,
> `GET /sesiones/ultimas`, `PUT /sesiones/{id}`, `DELETE /sesiones/{id}`,
> `POST /planes`, `GET /planes`, `POST /planes/importar`,
> `GET /planes/importar/export/{recurso}`, `PATCH /planes/{id}/descartar`.
> Sus contratos están en el OpenAPI del repo y siguen vigentes; no se
> tocaron en este PR.

---

## 2. Tipos TypeScript a generar desde el OpenAPI

Los tipos se generan con `openapi-typescript` apuntando al OpenAPI del FastAPI. Salida típica en `packages/contracts/api.ts`. Lista de shapes que el frontend va a necesitar:

**Banco de ejercicios (R6/R7):**
- `EjercicioListRead` — `{ items: EjercicioListItem[]; total: number }`
- `EjercicioListItem` — fila del listado, con `usos` y `ultima_vez` precomputados
- `EjercicioRead` — un ejercicio completo (usado en POST/PATCH)
- `EjercicioCreate` — body de POST
- `EjercicioUpdate` — body de PATCH (con `extra="forbid"`)
- `EjercicioDetalleRead` — detalle con `historial` y `posibles_duplicados`
- `EjercicioHistorialItem` — fila de `EjercicioDetalleRead.historial`
- `EjercicioPosibleDuplicado` — fila de `EjercicioDetalleRead.posibles_duplicados`
- `EjercicioFusionarCreate` — body de POST /fusionar
- `FusionResultadoRead` — respuesta de POST /fusionar

**Detalle de sesión (R8):**
- `SesionDetalleRead` — el detalle completo
- `SesionTipoRead` — subset de `TipoSesionRead` anidado en `SesionDetalleRead.tipo_sesion`
- `SesionDeltaRead` — `{ duracion_min: number|null; rpe: number|null; carga_srpe: number|null }`
- `BloqueDetalleRead` — bloque real con ejercicio + objetivo + delta
- `BloqueEjercicioEnDetalleRead` — subset de `EjercicioRead` anidado en cada bloque
- `BloqueObjetivoRead` — subset de `BloquePlanRead` anidado en bloques y no_ejecutados
- `BloqueDeltaRead` — 5 keys: `{ series, reps, peso_kg, distancia_m, duracion_s }`, todas `number|string|null`
- `BloqueNoEjecutadoRead` — `{ orden, ejercicio_id, ejercicio_nombre, objetivo }`
- `PlanDetalleEnSesionRead` — plan anidado en el detalle de sesión (con `PlanCicloRead` propio)
- `PlanCicloRead` (en `sesion.py`) — `{ numero, objetivo, semana, fase }`. **Caveat**: el OpenAPI lo emite con este nombre aunque haya otro `PlanCicloRead` en `plan.py`. Si el cliente usa `openapi-typescript`, va a tener un solo `PlanCicloRead` con la unión — usar el contrato del endpoint que consume cada vista, no el nombre del schema.
- `MolestiaDetalleRead` — `{ zona: string; intensidad: number }`

**Detalle de plan (R9):**
- `PlanDetalleRead` — el detalle completo del plan
- `BloquePlanDetalleRead` — bloque planeado con ejercicio anidado (mismo `BloqueEjercicioEnDetalleRead` que en sesión)

> Enum strings (todos en minúsculas, exactamente como están en Postgres):
> - `TipoMedicion`: `"carga" | "distancia" | "tiempo" | "tecnica"`
> - `CargaLumbar`: `"alta" | "media" | "baja"`
> - `FaseCiclo`: `"readaptacion" | "carga" | "descarga"`
> - `EstadoSesionPlan`: `"pendiente" | "cumplido" | "movido" | "descartado"`

---

## 3. Códigos de error por endpoint

| Endpoint | Código | Cuándo |
|---|---|---|
| `GET /catalogos/ejercicios` | 401 | Sin token. |
| `GET /catalogos/ejercicios` | 422 | `tipo_medicion` o `orden` con valor inválido. |
| `GET /catalogos/ejercicios/{id}` | 401 | Sin token. |
| `GET /catalogos/ejercicios/{id}` | 404 | Ejercicio no existe (o pertenece a otro usuario, indistinguible). |
| `POST /catalogos/ejercicios` | 401 | Sin token. |
| `POST /catalogos/ejercicios` | 409 | `nombre` normalizado duplicado contra otro ejercicio activo. |
| `POST /catalogos/ejercicios` | 422 | Body con campos extra (Pydantic `extra="forbid"`) o tipos incorrectos. |
| `PATCH /catalogos/ejercicios/{id}` | 401 | Sin token. |
| `PATCH /catalogos/ejercicios/{id}` | 404 | Ejercicio no existe. |
| `PATCH /catalogos/ejercicios/{id}` | 422 | Body trae `tipo_medicion` u otro campo no permitido. |
| `PATCH /catalogos/ejercicios/{id}` | 409 | `nombre` normalizado duplicado contra otro activo. |
| `POST /catalogos/ejercicios/{id}/fusionar` | 401 | Sin token. |
| `POST /catalogos/ejercicios/{id}/fusionar` | 404 | Origen o destino no existen. |
| `POST /catalogos/ejercicios/{id}/fusionar` | 422 | `destino_id == id` (path). |
| `POST /catalogos/ejercicios/{id}/fusionar` | 409 | Tipos de medición distintos entre origen y destino. |
| `POST /catalogos/ejercicios/{id}/fusionar` | 409 | Destino inactivo (`activo=false`). |
| `DELETE /catalogos/ejercicios/{id}` | 401 | Sin token. |
| `DELETE /catalogos/ejercicios/{id}` | 404 | Ejercicio no existe. |
| `DELETE /catalogos/ejercicios/{id}` | 409 | Con uso en `bloque` o `bloque_plan`. El mensaje sugiere archivar (`PATCH` con `activo=false`) o fusionar. |
| `GET /sesiones/{id}` | 401 | Sin token. |
| `GET /sesiones/{id}` | 404 | Sesión no existe o no pertenece al usuario (indistinguible). |
| `GET /planes/{id}` | 401 | Sin token. |
| `GET /planes/{id}` | 404 | Plan no existe o no pertenece al usuario (indistinguible). |

---

## 4. Migración aplicada

- **Archivo**: `apps/api/alembic/versions/f1a2b3c4d5e6_agregar_activo_a_ejercicio.py`.
- **Cambia**: `ALTER TABLE ejercicio ADD COLUMN activo boolean NOT NULL DEFAULT true`.
- **Down_revision**: `e4a7b93c218d`.
- **Comportamiento**: filas existentes quedan con `activo=true` por el `server_default`. Sin migración de datos.
- **Cuidado — caveat para merge**: la rama tiene **2 heads de alembic** (`24d0c867b11e` y `f1a2b3c4d5e6`). El head `24d` es anterior al feature 2 (PR `38f54e6`). Antes de mergear a `main`, resolver con una migración merge vacía (hija de ambos, `upgrade`/`downgrade` no-ops). Sin esto, `alembic upgrade head` falla con "Multiple head revisions are present".

---

## 5. Salida de `make lint` y `make test`

### `make lint`

```
$ uv run ruff check .                → All checks passed!
$ uv run ruff format --check .       → 184 files already formatted
$ uv run mypy app/services app/repositories → Success: no issues found in 60 source files
```

### `make test` (workaround)

**Importante**: `make test` directo no funciona en este entorno porque `.env.local` tiene una línea rota (newline separando `rend` e `imiento`). El DB docker se inicializó con `POSTGRES_USER=rend`; pydantic-settings lee "rendimiento" del `.env.local` y muere con `InvalidPasswordError`.

Workaround para correr la suite completa:

```bash
cd apps/api
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=rendimiento \
POSTGRES_USER=rend POSTGRES_PASSWORD=rendimiento JWT_SECRET_KEY=test \
uv run pytest
```

Tests del feature ejecutados individualmente (los 7 archivos del feature, en cualquier orden):

```bash
cd apps/api
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=rendimiento \
POSTGRES_USER=rend POSTGRES_PASSWORD=rendimiento JWT_SECRET_KEY=test \
uv run pytest \
  tests/test_banco_ejercicios.py \
  tests/test_detalle_sesion.py \
  tests/test_detalle_plan.py \
  tests/test_delta_bloque.py \
  tests/test_normalizacion.py \
  tests/test_andamiaje.py \
  tests/test_esquema.py
```

Resultado: **157 passed, 0 failed, 0 skipped** (en ~11s).

Distribución de tests:
- `test_banco_ejercicios.py` — 66
- `test_detalle_sesion.py` — 29 (incluye `test_sesion_detalle_no_supera_9_queries`)
- `test_detalle_plan.py` — 11
- `test_delta_bloque.py` — 12
- `test_normalizacion.py` — 10
- `test_andamiaje.py` — 4
- `test_esquema.py` — 25

Tests pre-existentes en rojo ajenos al feature: **8** (3 en `test_ciclos.py` que asumían el shape anterior de `GET /catalogos/ejercicios`, 1 en `test_cierre_del_dia.py`, 4 en `test_importacion_plan.py` por `plan-ejemplo.json` faltante). **No son blocker del feature** y no tocan el código nuevo.

---

## 6. Desviaciones respecto de la spec

1. **Umbral N+1 de `GET /sesiones/{id}` quedó en 9, no en 3 (spec original) ni en 8 (design).** Decisión del usuario. Las 4 colecciones 1:N (bloques, bloques_planeados, ciclo_semana, ciclo) más la query principal + tipo_sesion + sesion_plan + molestias + zonas llegan a 9 sin N+1. AGENTS §3.1 prohíbe desnormalizar para bajar el conteo. Documentado en `docs/REGLAS_NEGOCIO.md §16.5`. Test de regresión en `tests/test_detalle_sesion.py::test_sesion_detalle_no_supera_9_queries`.

2. **Similitud usa `rapidfuzz.fuzz.token_set_ratio` en vez de `difflib.SequenceMatcher`.** Pivot documentado: "Pallof press (anti-rotacion)" vs "Pallof press" daba 0.60 con difflib (bajo el umbral 0.75). rapidfuzz pasa. Dependencia nueva: `rapidfuzz>=3.10` (registrada en `apps/api/pyproject.toml`). Firma `_similitud_normalizada` intacta.

3. **Dos `PlanCicloRead` distintos** (uno en `schemas/entrenamiento/plan.py`, otro en `schemas/entrenamiento/sesion.py`). Vistas intencionalmente distintas del mismo dominio. Documentado en los docstrings de cada uno. **Si el front genera tipos con `openapi-typescript`, va a tener un solo `PlanCicloRead` con la unión de campos**: el supervisor debe nombrarlos distinto en el cliente (ej. `PlanCicloEnDetallePlan` vs `PlanCicloEnDetalleSesion`) o anotar el contrato del endpoint que consume cada vista.

4. **`GET /sesiones/{id}` cambia de `SesionRead` a `SesionDetalleRead`.** El frontend no consume este endpoint aún (Fase 6 no empezó), por lo que el cambio de contrato no rompe consumidores en producción. El supervisor debe consumir el shape `SesionDetalleRead` desde el primer PR de frontend que lo use.

5. **Bug pre-existente del conftest con `asyncio.run`.** La suite grande de tests tira `ConnectionRefused` entre tests del mismo archivo. Tests individuales y por archivo andan. No es del feature; workaround documentado arriba (correr por archivo).

6. **`.env.local` malformado** (línea con newline separando `rend` e `imiento`). Workaround: exportar las env vars con `POSTGRES_USER=rend`. Pre-existente al feature 2.

7. **2 heads de alembic en la rama** (`24d0c867b11e` y `f1a2b3c4d5e6`). Pre-existente al feature 2 (otro PR anterior dejó el head `24d`). Resolver antes de merge a `main` con una migración merge vacía.

---

## 7. Lo que quedó sin hacer

- **ACWR, Estado, monotonía, Hooper**: Fase 8. Confirmado fuera de scope.
- **UI / frontend**: este handshake es el contrato que el supervisor usa para arrancar al agente de frontend.
- **Progresión automática**: no tocado.
- **Tests pre-existentes en rojo (8)**: requieren un PR de limpieza aparte. No bloquean este feature.
- **Resolución de 2 heads de alembic**: pre-merge a `main`, crear migración merge vacía.
- **Bug del conftest y de `.env.local`**: pre-existentes, documentados, no resueltos en este feature.

---

## 8. Contratos de los endpoints (shapes)

Ejemplos de respuesta JSON para los 8 endpoints. Los ejemplos usan datos realistas tomados del seed y de los tests. Para producción, regenerar los tipos con `openapi-typescript` contra el OpenAPI servido por el dev server.

### `GET /catalogos/ejercicios`

```json
{
  "items": [
    {
      "id": 1,
      "nombre": "Sentadilla trasera",
      "patron": "squat",
      "carga_lumbar": "alta",
      "tipo_sesion_id": 1,
      "tipo_medicion": "carga",
      "descripcion": "Sentadilla con barra en trapecios, profundidad hasta paralelo.",
      "activo": true,
      "usos": 12,
      "ultima_vez": "2026-08-22"
    },
    {
      "id": 2,
      "nombre": "Estiramiento de isquiotibiales",
      "patron": null,
      "carga_lumbar": "baja",
      "tipo_sesion_id": 3,
      "tipo_medicion": "tecnica",
      "descripcion": "30 segundos por pierna, mantener la cadera neutra.",
      "activo": true,
      "usos": 5,
      "ultima_vez": "2026-08-19"
    }
  ],
  "total": 2
}
```

> `total` cuenta los items de la respuesta. Sin paginación (universo chico). `activo: false` aparece solo si el cliente pasa `?activo=false`.

### `GET /catalogos/ejercicios/{id}`

```json
{
  "id": 1,
  "nombre": "Sentadilla trasera",
  "patron": "squat",
  "carga_lumbar": "alta",
  "tipo_sesion_id": 1,
  "tipo_medicion": "carga",
  "descripcion": "Sentadilla con barra en trapecios, profundidad hasta paralelo.",
  "activo": true,
  "historial": [
    {
      "sesion_id": "8c0e5f4a-1234-5678-90ab-cdef01234567",
      "fecha": "2026-08-22",
      "bloque_id": 412,
      "orden": 2,
      "series": 4,
      "reps": 6,
      "peso_kg": "92.5"
    },
    {
      "sesion_id": "7b9f3a21-9876-5432-10fe-dcba98765432",
      "fecha": "2026-08-15",
      "bloque_id": 389,
      "orden": 1,
      "series": 5,
      "reps": 5,
      "peso_kg": "90.0"
    }
  ],
  "posibles_duplicados": [
    {
      "id": 14,
      "nombre": "Sentadilla back",
      "similitud": 0.78
    }
  ]
}
```

> `historial` viene **top 5**, ordenado por `fecha` desc. `posibles_duplicados` son candidatos con mismo `tipo_medicion` y similitud ≥ 0.75 (rapidfuzz, sobre nombres normalizados).

### `POST /catalogos/ejercicios`

Request:

```json
{
  "nombre": "Hip thrust",
  "tipo_medicion": "carga",
  "descripcion": "Extensión de cadera con barra desde el suelo.",
  "patron": "hinge",
  "carga_lumbar": "media"
}
```

Response (200):

```json
{
  "id": 28,
  "nombre": "Hip thrust",
  "patron": "hinge",
  "carga_lumbar": "media",
  "tipo_sesion_id": null,
  "tipo_medicion": "carga",
  "descripcion": "Extensión de cadera con barra desde el suelo.",
  "activo": true
}
```

### `PATCH /catalogos/ejercicios/{id}`

Request (cambia descripción y carga_lumbar, deja el resto):

```json
{
  "descripcion": "Extensión de cadera con barra, bench a la altura de los omóplatos.",
  "carga_lumbar": "alta"
}
```

Response (200): mismo shape que `EjercicioRead` de arriba.

### `POST /catalogos/ejercicios/{id}/fusionar`

Request (fusiona el ejercicio 14 "Sentadilla back" en el 1 "Sentadilla trasera"):

```json
{
  "destino_id": 1
}
```

Response (200):

```json
{
  "origen_id": 14,
  "destino_id": 1,
  "bloques_reasignados": 3,
  "bloques_plan_reasignados": 1
}
```

> Después de la fusión, el origen (id 14) queda con `activo=false`. Las filas de `bloque` y `bloque_plan` ahora apuntan a `destino_id=1`. Una sola transacción: si algo falla, no se aplica nada.

### `DELETE /catalogos/ejercicios/{id}`

Response: 204 sin body (éxito) o 409 con mensaje accionable si tiene uso:

```json
{
  "detail": "ejercicio 14 tiene 3 bloques y 1 bloque_plan; archivá o fusioná antes de eliminar"
}
```

### `GET /sesiones/{id}`

> El caso completo: sesión con plan y ciclo, un bloque ejecutado, un bloque planeado no ejecutado, una molestia del día.

```json
{
  "id": "8c0e5f4a-1234-5678-90ab-cdef01234567",
  "usuario_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "sesion_plan_id": 42,
  "fecha": "2026-08-05",
  "tipo_sesion": {
    "id": 1,
    "codigo": "fuerza",
    "nombre": "Fuerza"
  },
  "duracion_min": 55,
  "rpe": 9,
  "nota": "buena sesion",
  "carga_srpe": 495,
  "registrado_en": "2026-08-05T19:32:18.123456",
  "plan": {
    "id": 42,
    "nombre": "Fuerza full-body",
    "objetivo": "fuerza full-body",
    "nota": "nota del plan",
    "duracion_min_est": 50,
    "rpe_objetivo": 7,
    "estado": "cumplido",
    "dia_sugerido": 2,
    "ciclo": {
      "numero": 1,
      "objetivo": "base",
      "semana": 1,
      "fase": "carga"
    }
  },
  "delta": {
    "duracion_min": 5,
    "rpe": 2,
    "carga_srpe": 145
  },
  "bloques": [
    {
      "id": 412,
      "sesion_id": "8c0e5f4a-1234-5678-90ab-cdef01234567",
      "orden": 1,
      "series": 3,
      "reps": 7,
      "distancia_m": null,
      "duracion_s": null,
      "calidad": null,
      "peso_kg": "75.0",
      "rpe": 9,
      "dolor_lumbar": false,
      "nota": null,
      "ejercicio": {
        "id": 1,
        "nombre": "Sentadilla trasera",
        "tipo_medicion": "carga",
        "descripcion": "Sentadilla con barra en trapecios, profundidad hasta paralelo.",
        "carga_lumbar": "alta"
      },
      "objetivo": {
        "id": 87,
        "orden": 1,
        "series": 3,
        "reps_min": 6,
        "reps_max": 8,
        "peso_objetivo_kg": "80.0",
        "distancia_objetivo_m": null,
        "duracion_objetivo_s": null,
        "nota": null
      },
      "delta": {
        "series": 0,
        "reps": 0,
        "peso_kg": "-5.0",
        "distancia_m": null,
        "duracion_s": null
      }
    }
  ],
  "bloques_no_ejecutados": [
    {
      "orden": 2,
      "ejercicio_id": 1,
      "ejercicio_nombre": "Sentadilla trasera",
      "objetivo": {
        "id": 88,
        "orden": 2,
        "series": 3,
        "reps_min": 8,
        "reps_max": 10,
        "peso_objetivo_kg": "70.0",
        "distancia_objetivo_m": null,
        "duracion_objetivo_s": null,
        "nota": null
      }
    }
  ],
  "molestias": [
    {
      "zona": "lumbar",
      "intensidad": 3
    }
  ]
}
```

> Caso alternativo — sesión **libre** (sin plan):
> `sesion_plan_id: null`, `plan: null`, `delta: null`, `bloques_no_ejecutados: []`. El resto se llena igual.
>
> Para los `delta`:
> - `bloque.reps` dentro de `[reps_min, reps_max]` → `delta.reps == 0`.
> - `bloque.reps` por encima del rango → `delta.reps == reps - reps_max`.
> - `bloque.reps` por debajo del rango → `delta.reps == reps - reps_min`.
> - `objetivo == null` → todas las keys de `delta` son `null`.
> - Bloque real sin contraparte en `bloque_plan` → todas las keys de `delta` son `null`.

### `GET /planes/{id}`

> Caso: plan con ciclo anidado y bloques planeados con ejercicio.

```json
{
  "id": 42,
  "usuario_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "ciclo_semana_id": 7,
  "ciclo": {
    "numero": 1,
    "semana": 1,
    "fase": "carga"
  },
  "fecha_prevista": "2026-08-05",
  "dia_sugerido": 2,
  "tipo_sesion_id": 1,
  "objetivo": "fuerza full-body",
  "duracion_min_est": 50,
  "rpe_objetivo": 7,
  "estado": "cumplido",
  "clave_import": null,
  "nombre": "Fuerza full-body",
  "nota": "nota del plan",
  "bloques_planeados": [
    {
      "id": 87,
      "sesion_plan_id": 42,
      "orden": 1,
      "series": 3,
      "reps_min": 6,
      "reps_max": 8,
      "peso_objetivo_kg": "80.0",
      "distancia_objetivo_m": null,
      "duracion_objetivo_s": null,
      "nota": null,
      "ejercicio": {
        "id": 1,
        "nombre": "Sentadilla trasera",
        "tipo_medicion": "carga",
        "descripcion": "Sentadilla con barra en trapecios, profundidad hasta paralelo.",
        "carga_lumbar": "alta"
      }
    },
    {
      "id": 88,
      "sesion_plan_id": 42,
      "orden": 2,
      "series": 3,
      "reps_min": 8,
      "reps_max": 10,
      "peso_objetivo_kg": "70.0",
      "distancia_objetivo_m": null,
      "duracion_objetivo_s": null,
      "nota": null,
      "ejercicio": {
        "id": 1,
        "nombre": "Sentadilla trasera",
        "tipo_medicion": "carga",
        "descripcion": "Sentadilla con barra en trapecios, profundidad hasta paralelo.",
        "carga_lumbar": "alta"
      }
    }
  ]
}
```

> Si el plan fue creado a mano (sin ciclo), `ciclo_semana_id: null` y `ciclo: null`.
> `bloques_planeados` ya viene ordenado por `orden` ASC (no necesita sort en el cliente).

---

## 9. Cómo arrancar el agente de frontend

El supervisor le pasa al agente de frontend:

1. **El OpenAPI** del backend en dev (`GET /openapi.json`).
2. **Este handshake** (`handshake.md`) — única fuente de verdad sobre los 8 endpoints.
3. **El caveat del merge**: la rama `feature/be-banco-detalle` tiene 2 heads de alembic. Si el supervisor va a mergear a `main`, primero crea una migración merge vacía. Mientras el agente de frontend trabaja, no necesita tocar alembic — solo consumir los endpoints y regenerar tipos con `openapi-typescript`.

Orden recomendado de consumo en el frontend:

1. Listar y detalle del banco (`GET /catalogos/ejercicios`, `GET /catalogos/ejercicios/{id}`) — base del selector.
2. Crear / editar / fusionar / eliminar del banco — acciones del admin del catálogo.
3. Detalle de plan (`GET /planes/{id}`) — pantalla previa a ejecutar.
4. Detalle de sesión (`GET /sesiones/{id}`) — pantalla post-entreno o de revisión.

Los demás endpoints (POST/PUT/DELETE de sesiones y planes, importador) no se tocaron en este feature y conservan su contrato previo.

---

**Fin del handshake.** Si algo no está documentado acá, no existe en este feature: preguntar al supervisor antes de inventar.
