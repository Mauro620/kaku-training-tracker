# Handshake: Banco de ejercicios y detalle de sesión (backend)

Contrato entre backend y frontend para el feature 2. **Lo que no está acá no existe.**

- Repo: `training_tracker`
- OpenAPI: `GET /openapi.json` del dev server.
- Tipos TypeScript: generar con `openapi-typescript` apuntando al OpenAPI. Salida sugerida: `packages/contracts/api.ts`.

---

## Convenciones globales

- **Auth**: todos los endpoints requieren `Authorization: Bearer <token>`. Los tokens los entrega `POST /api/v1/auth/login`.
- **Content-Type**: `application/json` en bodies.
- **IDs**: enteros (`int`) salvo `sesion.id` y `usuario.id`, que son `UUID`.
- **Fechas**: ISO-8601 `YYYY-MM-DD`.
- **Decimales**: se serializan como **string** (`"75.0"`, `"0.5"`) para evitar pérdida de precisión en JSON.
- **Errores**: cuerpo `{ "detail": string }`. Los códigos siguen la convención HTTP estándar.
- **Catálogos sembrados** (no se modifican en este feature): `GET /catalogos/tipos-sesion`, `GET /catalogos/zonas-corporales`, `GET /catalogos/tipos-test`.

---

## 1. `GET /api/v1/catalogos/ejercicios`

Lista los ejercicios del banco con búsqueda, filtros y orden. `usos` cuenta filas de `bloque` (no de `bloque_plan`); `ultima_vez` es la fecha del último uso (NULL si nunca se usó).

### Query params

| Nombre | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `q` | `string \| null` | no | — | Busca en `nombre` y `descripcion` (normalizado, ILIKE). Ignora acentos y mayúsculas. |
| `tipo_medicion` | `TipoMedicion \| null` | no | — | Filtra por tipo. Valores: `"carga" \| "distancia" \| "tiempo" \| "tecnica"`. |
| `tipo_sesion_id` | `int \| null` | no | — | Filtra por tipo de sesión asociado. |
| `activo` | `bool` | no | `true` | `true` lista activos, `false` lista archivados. |
| `orden` | `enum` | no | `"nombre"` | `"nombre"` (asc) \| `"uso"` (desc por `usos`) \| `"reciente"` (desc por `ultima_vez`, NULL al final). |

### Respuesta `200`

```ts
interface EjercicioListRead {
  items: EjercicioListItem[];
  total: number;
}

interface EjercicioListItem {
  id: number;
  nombre: string;
  patron: string | null;
  carga_lumbar: "alta" | "media" | "baja";
  tipo_sesion_id: number | null;
  tipo_medicion: "carga" | "distancia" | "tiempo" | "tecnica";
  descripcion: string | null;
  activo: boolean;
  usos: number;
  ultima_vez: string | null; // YYYY-MM-DD
}
```

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token o token inválido. |
| `422` | `tipo_medicion` o `orden` con valor fuera del enum. |

---

## 2. `GET /api/v1/catalogos/ejercicios/{id}`

Detalle completo: datos básicos + `historial` (top 5 ejecuciones, más recientes primero) + `posibles_duplicados` (mismo `tipo_medicion`, similitud ≥ 0.75, excluye el propio).

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `int` | id del ejercicio. |

### Respuesta `200`

```ts
interface EjercicioDetalleRead {
  id: number;
  nombre: string;
  patron: string | null;
  carga_lumbar: "alta" | "media" | "baja";
  tipo_sesion_id: number | null;
  tipo_medicion: "carga" | "distancia" | "tiempo" | "tecnica";
  descripcion: string | null;
  activo: boolean;
  historial: EjercicioHistorialItem[];
  posibles_duplicados: EjercicioPosibleDuplicado[];
}

interface EjercicioHistorialItem {
  sesion_id: string; // UUID
  fecha: string;     // YYYY-MM-DD
  bloque_id: number;
  orden: number;
  series: number | null;
  reps: number | null;
  peso_kg: string | null; // Decimal como string
}

interface EjercicioPosibleDuplicado {
  id: number;
  nombre: string;
  similitud: number; // 0..1, ordenado desc
}
```

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Ejercicio no existe (incluye "existe pero pertenece a otro usuario", indistinguible). |

---

## 3. `POST /api/v1/catalogos/ejercicios`

Crea un ejercicio. Único catálogo que el usuario puede ampliar.

### Body

```ts
interface EjercicioCreate {
  nombre: string;            // 1..80 chars, obligatorio
  tipo_medicion: "carga" | "distancia" | "tiempo" | "tecnica"; // obligatorio
  descripcion?: string | null;
  patron?: string | null;    // max 40 chars
  carga_lumbar?: "alta" | "media" | "baja" | null;
}
```

> Pydantic `extra="forbid"`: cualquier campo extra → `422`.

### Respuesta `200`

```ts
interface EjercicioRead {
  id: number;
  nombre: string;
  patron: string | null;
  carga_lumbar: "alta" | "media" | "baja";
  tipo_sesion_id: number | null;
  tipo_medicion: "carga" | "distancia" | "tiempo" | "tecnica";
  descripcion: string | null;
  activo: boolean;
}
```

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `409` | `nombre` normalizado duplicado contra otro ejercicio activo. |
| `422` | Body con campos extra, tipos incorrectos o `nombre` con longitud inválida. |

### Ejemplo

```bash
curl -X POST https://.../api/v1/catalogos/ejercicios \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Hip thrust","tipo_medicion":"carga","descripcion":"Extensión de cadera con barra","patron":"hinge","carga_lumbar":"media"}'
```

---

## 4. `PATCH /api/v1/catalogos/ejercicios/{id}`

Edita un ejercicio. **`tipo_medicion` no es editable**: invalidaría bloques históricos. Si llega → `422`.

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `int` | id del ejercicio. |

### Body

```ts
interface EjercicioUpdate {
  nombre?: string;           // 1..80 chars
  descripcion?: string | null; // string vacío "" se guarda como null
  patron?: string | null;    // max 40 chars
  carga_lumbar?: "alta" | "media" | "baja" | null;
  activo?: boolean;
}
```

> `extra="forbid"` → `422` si llega `tipo_medicion` u otro campo no permitido.

### Respuesta `200`

`EjercicioRead` (mismo shape que en §3).

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Ejercicio no existe. |
| `409` | `nombre` normalizado duplicado contra otro activo. |
| `422` | `tipo_medicion` u otro campo no permitido; longitud inválida. |

---

## 5. `POST /api/v1/catalogos/ejercicios/{id}/fusionar`

Fusiona el ejercicio **origen** (path) en el **destino** (body). Reasigna todos los `bloque` y `bloque_plan` del origen al destino y archiva el origen (`activo=false`). Una sola transacción.

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `int` | id del ejercicio **origen**. |

### Body

```ts
interface EjercicioFusionarCreate {
  destino_id: number; // id del ejercicio que se queda
}
```

### Respuesta `200`

```ts
interface FusionResultadoRead {
  origen_id: number;
  destino_id: number;
  bloques_reasignados: number;
  bloques_plan_reasignados: number;
}
```

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Origen o destino no existe. |
| `422` | `destino_id == id` (path). |
| `409` | `tipo_medicion` distinto entre origen y destino. |
| `409` | Destino archivado (`activo=false`). |

---

## 6. `DELETE /api/v1/catalogos/ejercicios/{id}`

Elimina físicamente un ejercicio. Solo procede si **no aparece en `bloque` ni en `bloque_plan`**. Si tiene uso, devuelve `409` con un mensaje accionable.

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `int` | id del ejercicio. |

### Respuesta

`204 No Content` (sin body).

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Ejercicio no existe. |
| `409` | Tiene uso en `bloque` o `bloque_plan`. El `detail` sugiere archivar (`PATCH` con `activo=false`) o fusionar. |

### Ejemplo de error

```json
{
  "detail": "No se puede eliminar: el ejercicio tiene 4 usos. Archivá (activo=false) o fusioná con otro."
}
```

---

## 7. `GET /api/v1/sesiones/{id}`

Detalle completo de una sesión. Si la sesión no tiene plan asociado (`sesion_plan_id = null`), `plan` y `delta` son `null` y `bloques_no_ejecutados` es `[]`.

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `string` | UUID de la sesión. |

### Respuesta `200`

```ts
interface SesionDetalleRead {
  id: string;               // UUID
  usuario_id: string;       // UUID
  sesion_plan_id: number | null;
  fecha: string;            // YYYY-MM-DD
  tipo_sesion: SesionTipoRead;
  duracion_min: number;
  rpe: number;
  nota: string | null;
  carga_srpe: number;
  registrado_en: string;    // ISO-8601 con microsegundos
  plan: PlanDetalleEnSesionRead | null;
  delta: SesionDeltaRead | null;
  bloques: BloqueDetalleRead[];
  bloques_no_ejecutados: BloqueNoEjecutadoRead[];
  molestias: MolestiaDetalleRead[];
}

interface SesionTipoRead {
  id: number;
  codigo: string;
  nombre: string;
}

interface SesionDeltaRead {
  duracion_min: number | null;
  rpe: number | null;
  carga_srpe: number | null;
}

interface PlanDetalleEnSesionRead {
  id: number;
  nombre: string | null;
  objetivo: string | null;
  nota: string | null;
  duracion_min_est: number | null;
  rpe_objetivo: number | null;
  estado: "pendiente" | "cumplido" | "movido" | "descartado";
  dia_sugerido: number | null;
  ciclo: PlanCicloEnSesionRead | null;
}

interface PlanCicloEnSesionRead {
  numero: number;
  objetivo: string;
  semana: number;
  fase: "readaptacion" | "carga" | "descarga";
}

interface BloqueDetalleRead {
  id: number;
  sesion_id: string;          // UUID
  orden: number;
  series: number | null;
  reps: number | null;
  distancia_m: string | null; // Decimal como string
  duracion_s: number | null;
  calidad: number | null;
  peso_kg: string | null;     // Decimal como string
  rpe: number | null;
  dolor_lumbar: boolean;
  nota: string | null;
  ejercicio: BloqueEjercicioEnDetalleRead;
  objetivo: BloqueObjetivoRead | null;
  delta: BloqueDeltaRead;
}

interface BloqueEjercicioEnDetalleRead {
  id: number;
  nombre: string;
  tipo_medicion: "carga" | "distancia" | "tiempo" | "tecnica";
  descripcion: string | null;
  carga_lumbar: "alta" | "media" | "baja";
}

interface BloqueObjetivoRead {
  id: number;
  orden: number;
  series: number | null;
  reps_min: number | null;
  reps_max: number | null;
  peso_objetivo_kg: string | null;
  distancia_objetivo_m: string | null;
  duracion_objetivo_s: number | null;
  nota: string | null;
}

interface BloqueDeltaRead {
  series: number | null;
  reps: number | null;
  peso_kg: string | null;     // Decimal como string
  distancia_m: string | null;
  duracion_s: number | null;
  // Todos NULL si no hay objetivo o el bloque no tiene bloque_plan.
}

interface BloqueNoEjecutadoRead {
  orden: number;
  ejercicio_id: number;
  ejercicio_nombre: string;
  objetivo: BloqueObjetivoRead;
}

interface MolestiaDetalleRead {
  zona: string;
  intensidad: number;
}
```

### Semántica del delta

- `bloque.reps` dentro de `[reps_min, reps_max]` → `delta.reps == 0`.
- `bloque.reps` por encima del rango → `delta.reps == reps - reps_max`.
- `bloque.reps` por debajo del rango → `delta.reps == reps - reps_min`.
- Sin objetivo o sin `bloque_plan` → todas las keys de `delta` son `null`.

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Sesión no existe o no pertenece al usuario (indistinguible). |

### Ejemplo

```bash
curl https://.../api/v1/sesiones/8c0e5f4a-1234-5678-90ab-cdef01234567 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. `GET /api/v1/planes/{id}`

Detalle de un plan de sesión con su ciclo anidado y sus bloques planeados (`orden` ASC). Pantalla previa a ejecutar.

### Path params

| Nombre | Tipo | Descripción |
|---|---|---|
| `id` | `int` | id del `sesion_plan`. |

### Respuesta `200`

```ts
interface PlanDetalleRead {
  id: number;
  usuario_id: string;         // UUID
  ciclo_semana_id: number | null;
  ciclo: PlanCicloEnPlanRead | null;
  fecha_prevista: string | null; // YYYY-MM-DD
  dia_sugerido: number | null;
  tipo_sesion_id: number;
  objetivo: string | null;
  duracion_min_est: number | null;
  rpe_objetivo: number | null;
  estado: "pendiente" | "cumplido" | "movido" | "descartado";
  clave_import: string | null;
  nombre: string | null;
  nota: string | null;
  bloques_planeados: BloquePlanDetalleRead[];
}

interface PlanCicloEnPlanRead {
  numero: number;
  semana: number;
  fase: "readaptacion" | "carga" | "descarga";
}

interface BloquePlanDetalleRead {
  id: number;
  sesion_plan_id: number;
  orden: number;
  series: number | null;
  reps_min: number | null;
  reps_max: number | null;
  peso_objetivo_kg: string | null;
  distancia_objetivo_m: string | null;
  duracion_objetivo_s: number | null;
  nota: string | null;
  ejercicio: BloqueEjercicioEnDetalleRead; // mismo shape que en §7
}
```

### Errores

| Código | Cuándo |
|---|---|
| `401` | Sin token. |
| `404` | Plan no existe o no pertenece al usuario (indistinguible). |

---

## Resumen de tipos TypeScript a generar

Con `openapi-typescript` apuntando a `/openapi.json`, el frontend obtiene los shapes exactos. Si vas a tipar a mano, este es el inventario:

**Banco de ejercicios**
- `EjercicioListRead`, `EjercicioListItem`
- `EjercicioRead`
- `EjercicioCreate`, `EjercicioUpdate`
- `EjercicioDetalleRead`, `EjercicioHistorialItem`, `EjercicioPosibleDuplicado`
- `EjercicioFusionarCreate`, `FusionResultadoRead`

**Detalle de sesión**
- `SesionDetalleRead`, `SesionTipoRead`, `SesionDeltaRead`
- `PlanDetalleEnSesionRead`, `PlanCicloEnSesionRead` *(renombrar para no chocar con `PlanCicloEnPlanRead`)*
- `BloqueDetalleRead`, `BloqueEjercicioEnDetalleRead`, `BloqueObjetivoRead`, `BloqueDeltaRead`
- `BloqueNoEjecutadoRead`, `MolestiaDetalleRead`

**Detalle de plan**
- `PlanDetalleRead`, `PlanCicloEnPlanRead`
- `BloquePlanDetalleRead`

> El OpenAPI emite `PlanCicloRead` para ambos casos (sesión y plan). En el cliente conviene renombrarlos a `PlanCicloEnSesionRead` y `PlanCicloEnPlanRead` porque tienen campos distintos.

---

## Orden recomendado de consumo en el frontend

1. Listado y detalle del banco (`GET /catalogos/ejercicios`, `GET /catalogos/ejercicios/{id}`) — base del selector.
2. Crear / editar / fusionar / eliminar del banco — acciones del admin del catálogo.
3. Detalle de plan (`GET /planes/{id}`) — pantalla previa a ejecutar.
4. Detalle de sesión (`GET /sesiones/{id}`) — pantalla post-entreno o de revisión.

Los demás endpoints (POST/PUT/DELETE de sesiones y planes, importador, etc.) **no se tocaron** en este feature; conservan su contrato previo en el OpenAPI.

---

**Fin del handshake.** Si algo no está documentado acá, no existe en este feature: preguntar al supervisor antes de inventar.
