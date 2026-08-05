Documento de especificación de interfaz, diseño visual y catálogo de componentes UI/UX para la aplicación **Training Tracker PWA**.  
**1. Identidad Visual y Sistema de Diseño**
**1.1 Filosofía de Diseño**
El sistema utiliza una estética **Neo-Flat Minimalista en Modo Oscuro Absoluto (Dark Mode)** inspirada en interfaces nativas de alto rendimiento. Se fundamenta en una estructura modular basada en el patrón **Bento Box UI**, donde la jerarquía visual se establece mediante capas de elevación con grises tonales, bordes suaves y espacios negativos limpios, eliminando líneas divisorias duras.  
**1.2 Paleta de Colores**

- **Fondo Base (Canvas):** `#09090B` (Negro absoluto/casi negro)
- **Superficie Primaria (Contenedor Bento / Tarjeta):** `#18181B` (Gris oscuro profundo)
- **Superficie Secundaria (Campos de entrada / Botones inactivos / Modales):** `#27272A` (Gris medio)
- **Borde Suave (Subtle Border):** `#27272A` o `rgba(255, 255, 255, 0.08)`
- **Texto Primario:** `#FFFFFF` (Blanco puro para métricas, títulos y datos principales)
- **Texto Secundario:** `#A1A1AA` (Gris tenue para etiquetas, unidades y metadatos)
- **Acento Activo / Selección Primaria:** `#FFFFFF` (Blanco brillante con texto en negro)
- **Acentos Funcionales (Semáforos / Estados):**
  - *Positivo / Carga / Aprobado:* `#22C55E` (Verde esmeralda) / `#FFFFFF`
  - *Alerta / Moderado:* `#EAB308` (Amarillo ámbar)
  - *Peligro / Penalización:* `#EF4444` (Rojo carmesí)
  - *Indicador Especial / Foco:* `#A855F7` (Púrpura neón tenue)

**1.3 Tipografía**

- **Tipografía de Sistema:** Sans-serif moderna de proporciones geométricas con excelente legibilidad en pantallas móviles (ej. Inter, SF Pro Display / Text).
- **Pesos Tipográficos:**
  - *Heavy / Bold:* Usado exclusivamente en números grandes de métricas primarias y títulos principales (`h1`, `h2`).
  - *Medium / Regular:* Usado en etiquetas de tarjetas, botones y textos secundarios.
- **Escala de Tamaños:**
  - *Métrica Gigante:* `36px`–`48px` (Font-weight: 700)
  - *Título de Tarjeta / Header:* `18px`–`22px` (Font-weight: 600)
  - *Cuerpo / Botón:* `14px`–`16px` (Font-weight: 500)
  - *Etiqueta / Metadato:* `11px`–`13px` (Font-weight: 400, Tracking amplio)

**1.4 Geometría y Elevación**

- **Radio de Borde (Border Radius):**
  - *Contenedores Bento (Tarjetas):* `24px` o `30px` (Extremadamente redondeados).
  - *Botones, Píldoras e Inputs:* `9999px` (Fully rounded / Pill shape) o `16px`.
  - *Modales / Popovers:* `20px`.
- **Sombras y Elevación:**
  - Sin sombras de proyección difusas (*box-shadow: none* o sombra ambiental ultra sutil). La profundidad se logra únicamente mediante el contraste de color de fondo (`#09090B` -> `#18181B` -> `#27272A`).

**2. Layouts y Estructura Global**
**2.1 Shell de la Aplicación (PWA)**

- **Barra de Estado del Sistema:** Integrada dinámicamente con el fondo `#09090B`.
- **Header Superior:** Título de la pestaña actual alineado a la izquierda en tipografía `Bold` de gran tamaño. Esquina superior derecha reservada para acciones globales organizadas en botones circulares con fondo `#27272A` e iconos lineales minimalistas.
- **Área de Contenido:** Grid modular de una o dos columnas con scroll vertical continuo sin barra de desplazamiento visible (*scrollbar-hidden*).
- **Barra de Navegación Inferior (Bottom Navigation Bar):**
  - Flotante o adosada al borde inferior con efecto de desenfoque de fondo (*backdrop blur*).
  - Contiene únicamente los 4 accesos directos por iconos lineales minimalistas.  
  - El icono activo se destaca en color blanco puro; los inactivos permanecen en gris tenue.

**3. Catálogo de Componentes UI Reutilizables**
**3.1 Componentes de Estructura y Visualización**
**`BentoCard` (Contenedor Base)**

- **Estructura:** Caja contenedora con fondo `#18181B`, borde suave de `1px` en `#27272A` y esquinas redondeadas a `24px`.
- **Variantes de Tamaño:**
  - *Full Width (100%):* Ocupa el ancho completo de la retícula (usado para calendarios, tendencias y registros de bloques complejos).
  - *Half Width (50%):* Ocupa la mitad del ancho en filas de dos columnas (usado para métricas individuales como peso o tarjetas de sesión directa).
- **Header de Tarjeta:**
  - Izquierda: Icono representativo o identificador secundario.
  - Derecha: Botón opcional de ajustes/filtro circular pequeño en gris `#27272A`.

**`MetricDisplay` (Visualizador de Datos Relevantes)**

- **Estructura:** Bloque de presentación de métrica principal.
- **Elementos Visuales:**
  - Número principal en tipografía de gran tamaño y peso `Bold` en color blanco.
  - Unidad de medida (ej. `lbs`, `kg`, `min`, `RPE`) alineada en la línea de base o superior en color gris tenue.
  - Subtexto / Etiqueta indicadora en la parte inferior con fecha o estado relativo en gris tenue.

**`CircularProgressRing` (Anillo de Progreso)**

- **Estructura:** Indicador gráfico circular de un solo trazo.
- **Elementos Visuales:**
  - Pista de fondo en gris `#27272A`.
  - Línea de progreso activa en blanco brillante o color de estado.
  - Contenido central: Número o identificador de fase/orden en tipografía `Bold`.

**`CalendarHeatmapGrid` (Matriz de Asistencia/Carga)**

- **Estructura:** Visualizador matricial de puntos para meses/semanas.
- **Elementos Visuales:**
  - Cabeceras de meses en texto tenue alineadas horizontalmente.
  - Puntos (dots) redondeados que representan días individuales.
  - Estados del punto: Inactivo (Gris oscuro `#27272A`), Activo/Completado (Punto blanco brillante `#FFFFFF`).

**`BarChartMinimal` (Gráfico de Barras Tonal)**

- **Estructura:** Gráfico de frecuencias e intensidades.
- **Elementos Visuales:**
  - Barras verticales delgadas con bordes superiores redondeados.
  - Barra inactiva/normal en gris `#27272A`.
  - Barra seleccionada/destacada en blanco o púrpura.
  - Etiquetas de hora/día en el eje inferior en texto tenue de tamaño pequeño.

**3.2 Componentes Formulario e Interacción**
**`PillSelectorGroup` (Selector Horizontal de Píldoras)**

- **Estructura:** Fila horizontal de botones con bordes redondeados tipo cápsula (Pill shape) para selección única de fecha, día o categoría.
- **Estados de Píldora:**
  - *Inactiva:* Fondo `#27272A`, texto secundario gris.
  - *Activa:* Fondo blanco brillante `#FFFFFF`, texto negro `#000000` con peso `Bold`.

**`CheckTile` (Casilla de Registro / Serie)**

- **Estructura:** Fila o tarjeta de verificación rápida para completar series o ítems de hábitos.  
- **Elementos Visuales:**
  - Casilla circular u ovalada en el extremo izquierdo.
  - Cajas de valor secundario (ej. `25 lbs`, `4 reps`) encerradas en contenedores ovalados independientes con fondo `#27272A`.
  - Botón contextual de tres puntos (`...`) alineado a la derecha.

**`ActionPopoverMenu` (Menú Contextual Flotante)**

- **Estructura:** Ventana emergente tipo tarjeta con fondo gris `#18181B` y borde redondeado a `20px` que aparece sobre el contenido principal.
- **Elementos Visuales:**
  - Lista vertical de acciones rápidas (ej. *Warmup*, *Dropset*, *RPE*, *Copy + paste*, *Delete*).
  - Cada opción incluye un icono lineal alineado a la izquierda seguido del texto descriptivo.
  - Líneas separadoras imperceptibles o espaciado amplio. Opción destructiva (*Delete*) destacada en tono secundario.

**`StatusPill` (Cápsula de Estado)**

- **Estructura:** Etiqueta flotante o integrada en contenedor con indicador visual de tendencia.
- **Elementos Visuales:**
  - Fondo en tono oscuro con texto claro.
  - Icono de flecha de tendencia (arriba/abajo) o punto de estado.

**`BottomBarLogSet` (Barra de Acción Fija Inferior)**

- **Estructura:** Contenedor de confirmación flotante ubicado justo encima de la navegación principal.
- **Elementos Visuales:**
  - Lado izquierdo: Indicador del siguiente ítem o ejercicio activo con icono de confirmación circular.
  - Lado derecho: Botón primario de confirmación (`Log set` / `Guardar`) en contenedor redondeado con icono de flecha hacia adelante.

**4. Adaptación por Pestañas del Sistema**
1. **Pestaña Hoy:**

  - `BentoCard` superior con `CircularProgressRing` para la puntuación de Estado diaria.  
  - Módulo de métricas `MetricDisplay` para indicadores rápidos de sueño y bienestar.  
  - Fila de `PillSelectorGroup` para el checklist rápido de hábitos.  

2. **Pestaña Entreno:**

  - `BentoCard` principal con `CalendarHeatmapGrid` que muestra la consistencia del ciclo actual.
  - Listado de ejercicios estructurado mediante filas `CheckTile` con selectores `PillSelectorGroup` para datos de carga.  
  - Menús interactivos tipo `ActionPopoverMenu` para ajustes rápidos de series.

3. **Pestaña Cocina:**

  - Tarjetas modulares `BentoCard` de registro rápido por tap para recetas preconfiguradas.  
  - Barras de resumen de balance de composición tipo `BarChartMinimal`.  

4. **Pestaña Progreso:**

  - Grid de métricas `MetricDisplay` de ancho medio (Half Width) para comparación de cargas y tests físicos.  
  - Gráficas avanzadas `BarChartMinimal` para carga semanal y lecturas de fatiga.  