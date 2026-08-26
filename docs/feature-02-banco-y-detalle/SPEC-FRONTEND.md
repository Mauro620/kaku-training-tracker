# SPEC Frontend — Banco de ejercicios y detalle de sesión

Destinatario: agente de frontend.
Punto de partida: `handshake.md` del supervisor (contratos reales de API).
Si `handshake.md` contradice este documento, gana `handshake.md` y hay que
reportar la diferencia.

Documentos que gobiernan: `AGENTS.md` §5, `docs/ARCHITECTURE.md` §6,
`docs/REGLAS_NEGOCIO.md`.

---

## 0. Qué se construye y por qué

**Banco de ejercicios** — Hoy el catálogo lo alimenta un LLM vía JSON, pero
no hay forma de verlo ni corregirlo. Un nombre malo o una descripción
equivocada quedan fijos para siempre y contaminan todo el histórico.

**Detalle de sesión** — `ejercicio.descripcion` y `bloque.nota` se agregaron
para que el plan sea autoexplicativo, y hoy no se ven en ninguna pantalla.
El dato existe y es invisible.

---

## 1. Principios de diseño (derivados de reglas, no de gusto)

Estos principios ya están implícitos en el sistema. El agente los aplica, no
los discute.

**1.1 Ningún número sin referencia.** Un valor solo no informa. `90 kg` no
dice nada; `90 kg · igual que el plan` o `90 kg · +5 vs la última` sí. Toda
cifra va con su objetivo, su delta o su comparación histórica.

**1.2 El presupuesto de 2 minutos manda.** Estas pantallas son de consulta y
mantenimiento, no de captura, así que pueden ser densas. Pero nada de lo que
se agregue acá puede sumar pasos al registro diario.

**1.3 Los estados vacíos se diseñan.** La app vive incompleta durante
semanas. Cada lista, gráfico y sección necesita su versión sin datos, con
una línea que explique qué falta. Nunca un contenedor en blanco.

**1.4 Las acciones destructivas no compiten con las frecuentes.** Archivar,
fusionar y eliminar van en menú secundario, nunca como botón de igual peso
que "Editar".

**1.5 Distinción permanente vs de esta vez.** `ejercicio.descripcion` es qué
es el ejercicio y cómo se ejecuta, siempre. `bloque.nota` es qué pasó esta
vez ("al 60-70%", "con la zurda"). Deben verse tipográficamente distintas y
no mezclarse nunca — es la regla que evita que el catálogo se llene de
duplicados.

**1.6 Móvil primero.** ~380 px de ancho. Áreas táctiles de 44 px mínimo. Sin
tablas horizontales: si hay que scrollear de lado, el diseño está mal.

---

## 2. Pantalla: Banco de ejercicios

Acceso: desde el header de Entreno y desde Ajustes.

### 2.1 Estructura

```
Header        "Ejercicios" · contador de activos
Buscador      persistente, con debounce de 300 ms
Filtros       chips: tipo de medición · patrón · archivados
Lista         agrupada, ordenable
```

### 2.2 La fila

Cada fila muestra: nombre, chip de tipo de medición, y una línea secundaria
con `usos` y `ultima_vez`. Un ejercicio nunca usado se marca visualmente
distinto (texto atenuado + "sin usar").

**Decisión de diseño:** ordenar por uso descendente por defecto, no
alfabético. Lo que más usas es lo que más vas a querer corregir, y el
alfabético entierra la información útil bajo ejercicios que tocaste una vez.

### 2.3 Detalle (hoja inferior, no pantalla nueva)

Se abre desde la fila o desde cualquier nombre de ejercicio en la app.

Contenido en este orden:
1. Nombre y chips de tipo de medición, patrón y carga lumbar.
2. Descripción. Si está vacía, un estado explícito que invite a escribirla
   —no un espacio en blanco.
3. Historial: últimas 5 ejecuciones, con fecha y valores según el tipo de
   medición. Es lo que responde "¿cuánto levanté la última vez?".
4. Posibles duplicados, **solo si los hay**, con acción de fusionar.
5. Menú de tres puntos: editar, archivar, fusionar, eliminar.

**Edición en el sitio, no en pantalla aparte.** Tocar la descripción la
vuelve editable, con guardado explícito. Es corrección puntual, no un
formulario.

**`tipo_medicion` se muestra pero no se edita.** Visualmente distinto de los
campos editables, con una nota corta al intentar tocarlo: cambiarlo
invalidaría el histórico.

### 2.4 Fusión de duplicados

Es el flujo más delicado de esta pantalla porque mueve datos históricos.

1. Selector del ejercicio destino, filtrado al mismo `tipo_medicion`.
2. **Vista previa obligatoria**: "Se moverán 9 bloques y 3 bloques de plan
   de *Pallof press (anti-rotacion)* a *Pallof press*. El primero quedará
   archivado."
3. Confirmación explícita.
4. Resultado con los conteos reales devueltos por la API.

Nunca fusionar con un solo tap. El usuario tiene que ver qué se mueve.

### 2.5 Estados vacíos

| Situación | Qué se muestra |
|---|---|
| Catálogo vacío | Explicación de que los ejercicios llegan por importación de plan, con acceso directo a importar |
| Búsqueda sin resultados | El término buscado + acción de crear ese ejercicio |
| Ejercicio sin descripción | Invitación a escribirla, no un vacío |
| Ejercicio sin historial | "Todavía no lo has ejecutado" |

---

## 3. Pantalla: Detalle de sesión

Acceso: desde el histórico de Entreno, desde el plan del día ya ejecutado, y
desde cualquier referencia a una sesión.

### 3.1 Estructura

```
Cabecera      tipo, nombre del plan, fecha, ciclo y semana
Resumen       duración · RPE · carga, cada uno con su delta
Nota del plan  destacada si existe
Bloques       lista, cada uno con real, objetivo y delta
No ejecutados  sección aparte si los hay
Molestias     si hay
Acciones      editar · duplicar · eliminar
```

### 3.2 Resumen con delta

Tres cifras, cada una con su comparación contra el plan. El delta se colorea
por dirección, **pero el color nunca es el único portador de significado**:
siempre lleva signo y valor.

Y una decisión importante: un RPE más alto que el planeado **no es rojo**.
Es información, no error. Reservá el color de alerta para lo que realmente
requiere acción —molestia registrada, o bloques no ejecutados.

### 3.3 La fila de bloque

Es el corazón de la pantalla. Cada bloque muestra:

- Nombre del ejercicio, tocable → abre la hoja de detalle (§2.3).
- `bloque.nota` si existe, en línea propia y con tipografía diferenciada de
  la descripción.
- Valores reales, según `tipo_medicion` y **solo los que apliquen**:
  - `carga` → series × reps @ peso
  - `distancia` → reps × metros
  - `tiempo` → series × segundos
  - `tecnica` → reps o segundos, más calidad
- Objetivo del plan al lado, en secundario.
- Delta solo cuando es distinto de cero. Un delta de 0 es ruido: si hiciste
  lo planeado, no hace falta decirlo.
- Marca de `dolor_lumbar` si está en true.

**Propuesta de diseño:** que los bloques que coinciden con el plan se vean
compactos y los que se desviaron se expandan un poco. La pantalla dirige
la atención sola hacia lo que cambió, que es lo único que hay que leer.

### 3.4 Bloques no ejecutados

Sección aparte, al final de la lista, con encabezado propio. Nunca
intercalados con los ejecutados: mezclarlos hace que la sesión parezca más
completa de lo que fue.

### 3.5 Estados

Sesión libre (sin plan): se ocultan las columnas de objetivo y delta por
completo, no se muestran vacías. La pantalla se ve más simple, que es lo
correcto.

---

## 4. Propuestas de mejora (fundamentadas)

Van más allá de lo pedido. El agente las implementa salvo que contradigan
`handshake.md`.

**4.1 Acceso al ejercicio desde la ejecución.** Durante una sesión, tocar el
nombre debe abrir la misma hoja de detalle con descripción e historial. Es
el momento donde más se necesita —"¿cómo era este ejercicio?", "¿cuánto puse
la última vez?"— y evita salir de la pantalla a mitad de sesión.

**4.2 Aviso de duplicados en la vista previa de importación.** El backend ya
devuelve `posibles_duplicados`. Mostrarlos ahí, antes de confirmar, ataca el
problema en el momento en que se origina en vez de después. Es más barato
prevenir un duplicado que fusionarlo.

**4.3 Filtro de "sin descripción" en el banco.** Convierte el mantenimiento
del catálogo en una tarea con final: se ve cuántos faltan y se van
completando. Sin ese filtro, nadie audita un catálogo de 60 ejercicios.

**4.4 Comparación con la vez anterior en el historial.** En vez de solo
listar las últimas 5 ejecuciones, marcar la variación entre consecutivas.
Es progreso por ejercicio, que es la razón por la que se registra bloque a
bloque, y hoy no se ve en ninguna parte.

**4.5 Búsqueda insensible a tildes.** El backend ya normaliza. El frontend
no debe romperlo con filtrado local sobre la lista ya cargada.

---

## 5. Técnica

- shadcn/ui sobre Tailwind, tema oscuro, tarjetas redondeadas, coherente con
  las pantallas existentes.
- TanStack Query para lectura. Invalidar el catálogo tras editar o fusionar.
- Tipos desde el OpenAPI, nunca escritos a mano.
- Optimistic update en la edición de descripción; **nunca** en la fusión, que
  mueve datos históricos y debe esperar confirmación del servidor.
- Estas pantallas son de consulta: no requieren funcionamiento offline. Sí
  necesitan estado de carga y de error visibles, sin romper la navegación.

---

## 6. Aceptación

1. Se puede buscar un ejercicio, abrir su detalle, corregir nombre y
   descripción, y el cambio se refleja en la sesión donde aparece.
2. Se puede fusionar un duplicado con vista previa, y su histórico queda
   bajo el ejercicio destino.
3. El detalle de sesión muestra, por bloque, la descripción del ejercicio y
   la nota de ese bloque.
4. El delta plan vs real es legible de un vistazo, sin depender del color.
5. Los bloques no ejecutados se ven separados de los ejecutados.
6. Toda lista y sección tiene su estado vacío diseñado.
7. Nada de esto agregó pasos al registro diario.