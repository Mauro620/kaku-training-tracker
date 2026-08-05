# AGENTS.md

Instrucciones para agentes que trabajan en este repositorio.
**Léelas completas antes de escribir código.**

---

## 1. Qué es este proyecto

App de rendimiento personal para un futbolista universitario: registro diario
de entrenamiento, sueño, hábitos y nutrición, con una capa de métricas que
produce señales de carga, recuperación y progreso.

Monorepo. Backend FastAPI, frontend Next.js (PWA), PostgreSQL.

**Filosofía rectora: el registro diario del usuario no puede superar los 2
minutos.** Cualquier propuesta que agregue fricción al registro se rechaza,
sin importar cuán valioso parezca el dato.

---

## 2. Orden de lectura

1. `docs/SPEC.md` — qué se mide y por qué. La fuente de verdad del producto.
2. `docs/schema.dbml` — modelo de datos. La fuente de verdad del esquema.
3. `docs/REGLAS_NEGOCIO.md` — fórmulas exactas. **No inventes ninguna.**
4. `docs/ARCHITECTURE.md` — estructura, capas y convenciones.
5. `docs/ROADMAP.md` — fases, entregables y criterios de aceptación.

Si algo en el código contradice estos documentos, el documento gana y el
código es un bug.

---

## 3. Reglas duras

### 3.1 Nada hardcodeado

- Configuración de entorno → `pydantic-settings`, declarada en
  `app/core/config.py`, documentada en `.env.example`.
- Catálogos (tipos de sesión, ejercicios, alimentos, zonas corporales, tipos
  de test) → tablas sembradas en `app/seeds/`.
- Umbrales y constantes de negocio (bandas de ACWR, objetivo de sueño,
  penalizaciones del Estado) → tabla `parametro`, leída en runtime, cacheada
  por proceso.
- Los RPE objetivo **no** son parámetros globales: varían por fase del ciclo
  y viven en `ciclo_semana.rpe_objetivo_min/max`, como dice el DBML.
- **Ningún número mágico en el código de servicios.** Si escribes `1.3` o
  `7.0` dentro de una función, está mal.

### 3.2 Migraciones

- Todo cambio de modelo lleva una migración de Alembic en el mismo commit.
- Migraciones generadas con `--autogenerate` **siempre se revisan a mano**
  antes de aplicarse. Autogenerate no detecta renombres ni columnas generadas.
- Una cabeza de migración. Si aparecen dos, se resuelve antes de seguir.
- Las columnas generadas (`carga_srpe`, `horas_sueno`, `hooper`) se escriben a
  mano en la migración con `sa.Computed(...)`.

### 3.3 No inventar dominio

Las fórmulas de carga, ACWR, monotonía, Hooper, decremento de RSA y Estado
están en `docs/REGLAS_NEGOCIO.md` con su definición exacta. Si necesitas una
métrica que no está ahí, **detente y pregunta**. No la deduzcas.

### 3.4 Alcance

Cada fase de `docs/ROADMAP.md` tiene una sección "No hacer en esta fase".
Es vinculante. Si detectas que algo de una fase posterior haría falta,
anótalo y pregunta; no lo construyas por adelantado.

### 3.5 Tests

- Servicios y reglas de negocio: test unitario obligatorio.
- Endpoints: test de integración del camino feliz más los errores declarados.
- Las fórmulas de `REGLAS_NEGOCIO.md` llevan test con los casos de ejemplo
  que el documento incluye. Esos casos son el contrato.
- No se cierra una tarea con tests en rojo o saltados.

---

## 4. Flujo por tarea

1. Lee la fase correspondiente en `ROADMAP.md`.
2. Si hay ambigüedad, **pregunta antes de codificar**. Una pregunta cuesta
   menos que una implementación equivocada.
3. Implementa una rebanada vertical completa: modelo → schema → repositorio →
   servicio → endpoint → test.
4. Corre linters, tipos y tests.
5. Reporta: qué se hizo, qué archivos, qué decisiones tomaste que no estaban
   en la especificación, y qué quedó pendiente.

Un commit por unidad coherente. Mensajes en imperativo y en español.

---

## 5. Convenciones de código

### Backend

- Python 3.11+, tipado estricto. `ruff` para lint y formato, `mypy` en modo
  estricto sobre `app/services` y `app/repositories`.
- SQLAlchemy 2.0, estilo declarativo con `Mapped[...]` y `mapped_column(...)`.
  Nada de la sintaxis legacy.
- Async de punta a punta: `asyncpg`, `AsyncSession`, endpoints `async def`.
- Pydantic v2. Schemas separados por intención: `XCreate`, `XUpdate`, `XRead`.
  Nunca se expone un modelo de SQLAlchemy directamente.
- Nombres de tablas, columnas y campos del dominio **en español**, igual que
  el DBML. Nombres de infraestructura (clases base, utilidades, decoradores)
  en inglés. No traduzcas el DBML.
- Errores: excepciones de dominio propias en `app/core/exceptions.py`,
  traducidas a HTTP en un manejador central. Los servicios nunca importan
  `HTTPException`.

### Frontend

- Next.js App Router, TypeScript estricto.
- Tailwind + shadcn/ui. Componentes copiados al repo, no como dependencia.
- TanStack Query para estado de servidor. Zustand solo para estado local de UI.
- react-hook-form + zod en formularios. Los schemas de zod se derivan de los
  tipos generados del OpenAPI, no se escriben dos veces.
- Sin `localStorage` para datos de dominio: la persistencia offline es Dexie.

---

## 6. Comandos

```bash
make up            # levanta postgres y el api en docker
make migrate       # aplica migraciones
make seed          # siembra catálogos y parámetros
make test          # tests de backend
make lint          # ruff + mypy
pnpm --filter web dev
```

---

## 7. Cuándo detenerse y preguntar

- Falta una fórmula o un umbral que no está en `REGLAS_NEGOCIO.md`.
- El esquema del DBML no cubre un caso que la tarea necesita.
- Una tarea implica tocar algo listado en "No hacer en esta fase".
- Hay que elegir entre dos diseños y ninguno es obviamente mejor.

Preguntar no es fallar. Adivinar sí.
