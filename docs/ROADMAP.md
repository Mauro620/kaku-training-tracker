# Roadmap de desarrollo

Nueve fases. Cada una tiene entregables, criterio de aceptación y una lista de
**no hacer** que es vinculante para los agentes.

Orden de trabajo acordado: **todos los modelos y schemas primero**; después
rebanadas verticales (API + servicio + front) que se prueban a mano al
terminar cada una.

---

## Fase 0 — Andamiaje

**Objetivo:** que el repo arranque, migre y responda, sin lógica de dominio.

**Entregables**
- Estructura del monorepo según `ARCHITECTURE.md`.
- `docker-compose.yml` con Postgres 16 y el API.
- `app/core/config.py` con `pydantic-settings`, y `.env.example` completo.
- Alembic configurado contra la metadata de SQLAlchemy, con `env.py` async.
- `GET /health` que verifica conexión a base de datos.
- `Makefile` con `up`, `migrate`, `seed`, `test`, `lint`.
- `ruff`, `mypy` estricto y `pytest` configurados y en verde.
- CI que corre lint y tests en cada push.

**Aceptación:** `make up && make migrate && make test` funciona en limpio, y
`/health` responde `200` con el estado de la base de datos.

**No hacer:** ningún modelo de dominio, ningún endpoint de negocio, nada de
frontend.

---

## Fase 1 — Modelo de datos completo

**Objetivo:** el esquema entero en código, sin una sola API.

**Entregables**
- Todos los modelos de SQLAlchemy 2.0 de `schema.dbml`, con sus relaciones,
  índices y restricciones `CHECK` (rangos de RPE, bienestar 1–5, intensidad
  0–10, `fin > inicio`).
- Columnas generadas con `sa.Computed(...)`: `carga_srpe`, `horas_sueno`,
  `hooper`.
- Tabla `parametro` de `ARCHITECTURE.md`.
- Schemas de Pydantic v2 (`Create`, `Update`, `Read`, con validadores de
  rango) **solo de las entidades que consumen las fases 3 y 4**: sueño,
  bienestar, hábitos, ciclo, semana de ciclo, plan de sesión, sesión, serie,
  molestia y los catálogos que esas usan. Nutrición y evaluación esperan a
  sus fases 6 y 7: generar 78 clases hoy es código muerto que hay que
  mantener mientras el esquema todavía se mueve.
- Migración inicial única, revisada a mano.
- Seeds: `usuario` (solo el nombre, desde `SEED_USUARIO_NOMBRE`; las
  credenciales son fase 2), `tipo_sesion` con su `demanda`, `zona_corporal`,
  `tipo_test`, `ejercicio` (los de la rutina actual), `habito` (creatina,
  magnesio, estiramiento, hidratación), `parametro` (tabla completa de
  `ARCHITECTURE.md`) y `alimento` con los ~40 de la despensa.
- Test que crea el esquema desde cero, siembra y verifica las restricciones.

**Aceptación:** `make migrate && make seed` deja la base lista y consultable;
un test confirma que las columnas generadas calculan bien y que los `CHECK`
rechazan valores fuera de rango.

**No hacer:** repositorios, servicios, endpoints, autenticación, frontend.

---

## Fase 2 — Autenticación mínima ✅

**Objetivo:** un usuario, sesión estable, sin construir un sistema de cuentas.

**Entregables**
- Login por contraseña con access JWT de 15 minutos y refresh token opaco
  rotativo de 30 días. Se prefirió access corto + refresh rotativo a un JWT
  de larga duración: el refresh existe justamente para que el access pueda
  ser breve sin friccionar al usuario, y limita la ventana de un token
  robado a 15 minutos en vez de meses.
- Dependencia `get_usuario_actual`.
- Credenciales del usuario único (email y password) desde variables de
  entorno, sembradas en una tabla `auth_usuario` **separada** de `usuario`
  (1:1 por PK=FK), no como columnas agregadas a `usuario`: la identidad de
  login es otro bounded context y no debía contaminar la tabla de dominio.

**Aceptación:** un endpoint protegido rechaza sin token y responde con él.
Cumplido — ver `apps/api/tests/test_auth.py`.

**No hacer:** registro público, recuperación de contraseña, roles, OAuth.

---

## Fase 3 — Rebanada vertical: cierre del día

Primera funcionalidad completa de punta a punta. Es la que sostiene la
filosofía de los 2 minutos.

**Entregables**
- Backend: repositorios, servicios y endpoints para `registro_sueno`,
  `registro_bienestar` y `habito_registro`. Upsert por `(usuario_id, fecha)`.
- Frontend: andamiaje de Next.js con las cuatro pestañas, PWA instalable, y
  la pantalla **Hoy** con el formulario de cierre del día.
- Cliente de API generado desde el OpenAPI.

**Aceptación:** registrar sueño, bienestar y hábitos desde el celular en menos
de 40 segundos, con los datos persistidos.

**No hacer:** offline, sesiones de entrenamiento, cálculo de Estado, gráficas.

---

## Fase 4 — Sesiones de entrenamiento

**Entregables**
- Backend: `ciclo`, `ciclo_semana`, `sesion_plan`, `serie_plan`, `sesion`,
  `serie`, `molestia`.
- Endpoint que devuelve el plan del día y otro que registra el resultado.
- Cálculo del delta plan contra real.
- Frontend: pestaña **Entreno** con plan, registro de resultado e historial.

**Aceptación:** planear una sesión, ejecutarla, registrarla y ver el delta.
`carga_srpe` se calcula sola.

**No hacer:** ACWR, monotonía, Estado. Solo captura.

---

## Fase 5 — Offline y sincronización

Aquí está la ingeniería difícil. Va después de que haya algo que sincronizar.

**Entregables**
- Esquema de Dexie espejo de las entidades de captura.
- Cola de salida con `idempotency_key`, reintento con retroceso exponencial
  y estados `pendiente`, `enviando`, `sincronizado`, `fallido`.
- Endpoints idempotentes: repetir un `idempotency_key` devuelve `200` con el
  recurso existente.
- Indicador de estado de sincronización en la interfaz.
- Test que envía el mismo evento tres veces y verifica una sola fila.

**Aceptación:** en modo avión se registra una sesión completa; al recuperar
red se sincroniza sola y sin duplicados.

**No hacer:** resolución de conflictos multiusuario. Hay un solo usuario.

---

## Fase 6 — Nutrición

**Entregables**
- Backend: `alimento`, `receta`, `receta_item`, `comida_log`, `comida_item`,
  `despensa`. Cálculo de macros por receta y por día.
- Endpoint de lista de mercado: `imprescindible = true AND en_stock = false`.
- Frontend: pestaña **Cocina** con registro por tap, biblioteca de recetas y
  despensa.

**Aceptación:** registrar el desayuno en un tap y ver los macros del día;
la lista de mercado se genera sola.

**No hacer:** escáner de códigos de barras, integración con APIs externas de
alimentos, metas diarias de macros con alertas.

---

## Fase 7 — Tests físicos y partidos

**Entregables**
- Backend: `test_fisico`, `test_intento`, `partido`, `medida_corporal`.
- Cálculo de `pct_decremento` y `pct_cambio` respetando `mejor_es_mayor`.
- Frontend: captura de test con cronómetro por intento y ficha de partido.

**Aceptación:** registrar un RSA de 6 sprints y ver el decremento; registrar
un partido y que su carga entre en el total de la semana.

**No hacer:** capa de métricas todavía.

---

## Fase 8 — Capa de métricas

Requiere al menos 28 días de datos reales. **No empezar antes.**

**Entregables**
- Proyecto dbt sobre Postgres con capas silver y gold.
- Marts: `mart_estado_diario`, `mart_carga_semanal`, `mart_nutricion_semanal`,
  `mart_progreso_ciclo`.
- Implementación exacta de las fórmulas de `REGLAS_NEGOCIO.md`, con sus casos
  de prueba como tests de dbt.
- Job nocturno programado.
- Endpoints de lectura sobre los marts.
- Frontend: pestaña **Progreso** y tarjeta de Estado con desglose de razones.

**Aceptación:** las fórmulas pasan sus casos de prueba; el Estado del día
coincide razonablemente con cómo se siente el usuario durante dos semanas.

**No hacer:** modelos predictivos ni machine learning. Con n=1 y 28 días no
hay nada que aprender.

---

## Fase 9 — Integraciones y cierre

**Entregables**
- Backfill único desde la base `Registro diario` de Notion.
- Ingesta de Apple Health o Health Connect para sueño, peso y frecuencia
  cardiaca en reposo.
- Notificaciones push para los cuatro momentos de registro.
- Exportación a CSV de todas las tablas.
- Ingesta del Excel de horarios como `dim_bloque_horario`.

**Aceptación:** el histórico de Notion aparece en la app y el sueño entra
solo.

**No hacer:** tocar el Excel de finanzas, ni siquiera en lectura.

---

## Criterio que gobierna todo

El criterio de éxito de las fases 0 a 5 no es que compile: son **14 días
seguidos de registro real**. Si eso no ocurre, las fases 6 en adelante se
posponen y se revisa la fricción del registro, no se agregan funciones.
