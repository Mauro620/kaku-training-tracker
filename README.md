# Rendimiento

App de rendimiento personal para un futbolista universitario: registro diario
de entrenamiento, sueño, hábitos y nutrición, con una capa de métricas que
produce señales de carga, recuperación y progreso.

Monorepo: FastAPI + PostgreSQL en `apps/api`, Next.js PWA en `apps/web`.

**Filosofía rectora: el registro diario del usuario no puede superar los 2
minutos.** Cualquier propuesta que agregue fricción al registro se rechaza.

## Documentos

Son la fuente de verdad. Si el código los contradice, el código es un bug.

| Documento | Qué contiene |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Reglas para agentes que trabajan en el repo |
| [`docs/SPEC.md`](docs/SPEC.md) | Qué se mide y por qué |
| [`docs/schema.dbml`](docs/schema.dbml) | Modelo de datos |
| [`docs/REGLAS_NEGOCIO.md`](docs/REGLAS_NEGOCIO.md) | Fórmulas exactas y sus casos de prueba |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Capas y convenciones |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Fases, entregables y criterios de aceptación |
| [`docs/PENDIENTES.md`](docs/PENDIENTES.md) | Decisiones con fecha de vencimiento |

## Arranque

```bash
cp .env.example .env.local   # y completá POSTGRES_PASSWORD
make up                      # postgres 16 + api
make migrate
make seed
make test
```

Si ya tenés algo en los puertos 5432 u 8000, cambialos en `.env.local`:
`POSTGRES_PORT` y `API_PORT`. `docker-compose.yml` y los tests los leen de ahí,
así que no hay que tocar ningún archivo versionado.

## Estado

Fases 0 y 1 completas: andamiaje y modelo de datos. Sin endpoints de negocio
ni frontend todavía — ver `docs/ROADMAP.md`.
