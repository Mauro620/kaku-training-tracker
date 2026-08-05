# Arquitectura

## 1. Estructura del monorepo

```
.
├── AGENTS.md
├── Makefile
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── SPEC.md
│   ├── schema.dbml
│   ├── REGLAS_NEGOCIO.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── PENDIENTES.md
├── apps/
│   ├── api/                      # FastAPI
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   ├── alembic.ini
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/v1/routers/   # solo HTTP: validar, delegar, responder
│   │   │   ├── core/             # config, security, exceptions, params
│   │   │   ├── db/               # engine, session, base
│   │   │   ├── models/           # SQLAlchemy
│   │   │   ├── schemas/          # Pydantic
│   │   │   ├── repositories/     # único lugar con acceso a datos
│   │   │   ├── services/         # lógica de negocio, sin HTTP ni SQL
│   │   │   ├── seeds/
│   │   │   └── utils/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── web/                      # Next.js PWA
│       ├── app/
│       │   ├── (tabs)/hoy/
│       │   ├── (tabs)/entreno/
│       │   ├── (tabs)/cocina/
│       │   └── (tabs)/progreso/
│       ├── components/ui/        # shadcn
│       ├── lib/
│       │   ├── api/              # cliente generado desde OpenAPI
│       │   ├── db/               # Dexie: esquema local y cola de salida
│       │   └── sync/
│       └── package.json
├── packages/
│   └── contracts/                # tipos TS generados desde el OpenAPI
└── analytics/
    └── dbt/                      # capa de métricas (fase 7)
```

Subcarpetas por dominio dentro de `models/`, `schemas/`, `repositories/` y
`services/`: `entrenamiento/`, `bienestar/`, `nutricion/`, `evaluacion/`,
`catalogo/`.

---

## 2. Capas del backend

```
router  →  service  →  repository  →  modelo
```

| Capa | Sí | No |
|---|---|---|
| `router` | Validar entrada, invocar servicio, mapear a `XRead` | Lógica de negocio, consultas |
| `service` | Reglas, orquestación, transacciones | `HTTPException`, `select()` |
| `repository` | Consultas, persistencia | Reglas de negocio |
| `models` | Definición de tablas y relaciones | Lógica |

Regla de importaciones: un servicio nunca importa de `fastapi`, y un
repositorio nunca importa de `services`. Es verificable con un test de lint y
vale la pena tenerlo.

Esta es la diferencia deliberada frente a Paymi: allá los servicios hacen
consultas directas. Aquí `repositories/` existe para que las reglas se puedan
testear sin base de datos.

---

## 3. Parámetros de negocio

`nada hardcode` aplica también a los umbrales. Tabla adicional al DBML:

```sql
CREATE TABLE parametro (
  id           smallserial PRIMARY KEY,
  clave        varchar(60) NOT NULL,
  valor        numeric(10,4) NOT NULL,
  unidad       varchar(20),
  descripcion  text NOT NULL,
  vigente_desde date NOT NULL DEFAULT CURRENT_DATE,
  UNIQUE (clave, vigente_desde)
);
```

La unicidad es `(clave, vigente_desde)`, no `clave` sola: así un parámetro
puede tener varias versiones en el tiempo. **La lectura toma siempre la fila
con el mayor `vigente_desde <= CURRENT_DATE`.** Recalcular el histórico con
los umbrales de hoy destruiría la trazabilidad de por qué el Estado dio lo
que dio en su momento.

`parametro` es global, sin `usuario_id`. Con un solo usuario no hace
diferencia; ver `docs/PENDIENTES.md` para cuándo dejaría de alcanzar.

Claves iniciales a sembrar:

| Clave | Valor |
|---|---|
| `sueno_objetivo_horas` | 7.0 |
| `acwr_min_seguro` | 0.8 |
| `acwr_max_seguro` | 1.3 |
| `acwr_umbral_alerta` | 1.5 |
| `acwr_dias_agudo` | 7 |
| `acwr_dias_cronico` | 28 |
| `cmj_caida_alerta_pct` | 5.0 |
| `rsa_decremento_bueno_pct` | 5.0 |
| `rsa_decremento_alerta_pct` | 8.0 |
| `estado_banda_verde` | 75 |
| `estado_banda_amarilla` | 55 |
| `molestia_recurrencia_dias` | 14 |
| `molestia_recurrencia_conteo` | 3 |
| `proteina_g_por_kg` | 1.8 |
| `cerveza_horas_sin_alta_demanda` | 48 |
| `cerveza_acwr_max` | 1.4 |
| `cerveza_deuda_sueno_max` | 4 |
| `estado_penal_sueno_por_hora` | 2 |
| `estado_penal_sueno_tope` | 20 |
| `estado_penal_hooper_por_punto` | 3 |
| `estado_penal_hooper_tope` | 25 |
| `estado_penal_acwr_moderado` | 8 |
| `estado_penal_acwr_alto` | 15 |
| `estado_penal_molestia_por_punto` | 2 |
| `estado_penal_molestia_tope` | 20 |
| `estado_penal_cmj` | 15 |
| `hooper_base_ventana_dias` | 28 |
| `hooper_base_min_registros` | 14 |

Se leen mediante un `ParametroService` con caché en memoria e invalidación
al escribir. Ningún servicio recibe un umbral como literal.

---

## 4. Sincronización offline

El cliente es la fuente de eventos; el servidor es la fuente de verdad.

1. Toda escritura entra primero a Dexie con un `idempotency_key` (UUID v4
   generado en el cliente) y estado `pendiente`.
2. Un worker vacía la cola en orden FIFO cuando hay red.
3. El endpoint de sync es idempotente: si el `idempotency_key` ya existe,
   devuelve el recurso existente con `200`, no crea nada ni falla.
4. Al confirmar, el registro local pasa a `sincronizado`.
5. Para las tablas de un registro por día (`registro_sueno`,
   `registro_bienestar`, `medida_corporal`) la unicidad `(usuario_id, fecha)`
   hace de deduplicación natural: la operación es un upsert.

No hay resolución de conflictos compleja porque hay un solo usuario. Última
escritura gana, con el timestamp del cliente registrado para auditoría.

---

## 5. Contratos entre backend y frontend

El OpenAPI de FastAPI es el contrato. Los tipos de TypeScript se generan a
`packages/contracts` con `openapi-typescript` y **no se escriben a mano**. Si
el frontend necesita un campo que el contrato no tiene, el cambio empieza en
el backend.

---

## 6. Frontend

- Next.js App Router, cuatro rutas de pestaña más las de detalle.
- PWA con Serwist: manifest, service worker, instalable, arranque offline.
- shadcn/ui sobre Tailwind. Tema oscuro por defecto, tarjetas de esquinas
  redondeadas y un número grande por tarjeta, siguiendo el mockup de
  referencia.
- Recharts para las gráficas de tendencia y carga.
- Dexie para persistencia local, TanStack Query para lectura de servidor con
  `staleTime` alto: la app tiene que abrir con datos aunque no haya red.

---

## 7. Entornos

Tres archivos de configuración, ninguno con secretos en el repo:
`.env.example` (plantilla versionada), `.env.local` (desarrollo, ignorado),
variables del proveedor en producción.

`app/core/config.py` declara todo con `pydantic-settings` y falla al arrancar
si falta una variable obligatoria. Arrancar con configuración incompleta es
peor que no arrancar.
