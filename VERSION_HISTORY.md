# Historial de versiones — AudioRep

---

# 0.79 — Correcciones de estadísticas: artistas, países y sellos

**Fecha:** 29 de abril de 2026

### Corregido

- **Top artistas con variantes de featuring unificadas** — los artistas con colaboraciones en sus tags (por ejemplo, "The Black Keys feat. X" o "The Black Keys Featuring Y") ahora se agrupan bajo el nombre canónico del artista ("The Black Keys"). La normalización aplica tanto al nombre del artista del álbum como al de la pista.
- **País de origen de artistas sin duplicados** — el gráfico de países contaba una entrada por entidad Artist en la base de datos, lo que duplicaba el conteo cuando un mismo artista estaba almacenado con múltiples variantes de nombre por featuring. Ahora se deduplica por nombre normalizado antes de contar países.
- **País de sellos ahora visible** — el gráfico "País de origen de sellos" no mostraba datos por dos causas combinadas. Primera: el endpoint de MusicBrainz `get_release_by_id` con `includes=["labels"]` devuelve el nombre del sello pero no su campo `country` ni `area`; se necesita una llamada separada a `get_label_by_id` por MBID del sello para obtener el país. Los resultados se cachean por MBID para no repetir la llamada. Segunda: la comparación entre el nombre del sello en la base de datos y el nombre del álbum fallaba cuando diferían en sufijos corporativos ("Nonesuch Records" vs "Nonesuch"). Ahora ambos se normalizan eliminando sufijos comunes antes de comparar.
- **Layout del tab Álbumes estandarizado** — los gráficos "Décadas" y "Tipo de álbum" ahora se muestran en la misma fila a media anchura cada uno, en lugar de ocupar filas completas independientes.

---

# 0.78 — Corrección de estadísticas de artistas

**Fecha:** 29 de abril de 2026

### Corregido

- **Fragmentación de artistas en estadísticas** — el gráfico "Top 10 artistas por cantidad de pistas" mostraba al mismo artista dividido en múltiples entradas cuando alguna de sus pistas tenía tags con variantes de featuring (por ejemplo, "The Black Keys feat. X" o "The Black Keys Featuring Y"). Ahora las estadísticas usan el artista canónico del álbum como referencia para agrupar las pistas, en lugar del campo artista del archivo individual. Esto también corrige el conteo total de artistas únicos y la resolución del sello discográfico por álbum.

---

# 0.77 — Enriquecimiento de metadatos corregido, países completos y flecha de dropdowns

**Fecha:** 28 de abril de 2026

### Corregido

- **Estadísticas no se actualizaban tras enriquecimiento** — el problema raíz era que la señal de actualización de biblioteca solo se emitía cuando había cambios a nivel de pista (género, año, MBID), ignorando los cambios en álbumes (sello, tipo de lanzamiento), artistas (país) y sellos discográficos (país de origen). Ahora cualquier cambio persistido en la base de datos, sin importar en qué tabla, dispara el recálculo de estadísticas.
- **Países de artistas y sellos mostrados como códigos ISO** — MusicBrainz puede devolver el país como código de dos letras ("US", "GB", "DE") cuando el campo de área completo no está disponible. Estos códigos se convierten ahora a nombres completos antes de persistirse ("United States", "United Kingdom", "Germany"). Se usa la librería `pycountry` si está instalada, con un fallback interno de los códigos más frecuentes en contextos musicales.

### Modificado

- **Orden de procesamiento del enriquecimiento** — las pistas se procesan ahora de mayor a menor completitud de metadatos: primero las que ya tienen MBID (lookup directo, sin ambigüedad), luego las que tienen artista y álbum conocidos, luego las que solo tienen artista, y por último el resto. Esto mejora la tasa de coincidencias y reduce las consultas fallidas a la API.
- **Flecha de los dropdowns más visible** — el ícono chevron de los QComboBox pasó de `#c0c0e0` con grosor 1.8px a `#e2e2f0` con grosor 2.0px. A 10×6px de renderizado el color anterior resultaba casi invisible contra el fondo oscuro del dropdown.
- **Importación sin duplicados** — al agregar una carpeta, las pistas que ya existen en la biblioteca (mismo archivo) se omiten. Antes, importar la misma carpeta dos veces duplicaba todas las pistas.
- **Reimportación limpia** — el botón "Importar carpeta" incluye ahora un menú con dos opciones: "Agregar carpeta" (agrega pistas nuevas sin tocar las existentes) y "Limpiar biblioteca y reimportar…" (borra toda la biblioteca y la reconstruye desde la carpeta elegida). La segunda opción pide confirmación antes de proceder.
- **Enriquecimiento cancelado al reimportar** — si el servicio de actualización de metadatos está corriendo cuando el usuario agrega o reimporta una carpeta, se cancela automáticamente. Una vez terminado el escaneo, se relanza sobre la nueva biblioteca.
- **Race condition en el enriquecimiento corregida** — si el worker anterior fue cancelado pero aún no terminó (estaba durmiendo entre requests), el nuevo enriquecimiento esperaba hasta 3 segundos a que se detuviera antes de arrancar. Antes podía saltarse completamente el enriquecimiento de la nueva biblioteca.
- **API de MusicBrainz: país del artista corregido** — el lookup de recordings ahora incluye `artists` además de `artist-credits`. Con solo `artist-credits` los campos `area` y `country` del artista no vienen en la respuesta, lo que hacía que el país siempre quedara vacío.
- **Enriquecimiento rediseñado: por álbum en lugar de por pista** — en lugar de hacer una llamada a la API por cada pista (167 llamadas para 167 pistas), el enriquecimiento ahora agrupa por álbum único y hace una sola llamada por álbum usando el endpoint de releases (Fase 1). Esto reduce las llamadas de 167 a 14 para la misma biblioteca, y obtiene datos más completos (año, sello, país del artista, país del sello, tipo de lanzamiento) que el endpoint de recordings no siempre devuelve. Las pistas sin género siguen procesándose individualmente en una Fase 2 separada.
- **Worker de enriquecimiento con conexión DB propia** — el worker ahora abre su propia conexión SQLite en lugar de compartir la del hilo principal. Una conexión `sqlite3.Connection` compartida entre hilos no es thread-safe aunque use `check_same_thread=False`; las escrituras del worker fallaban silenciosamente.

---

# 0.76 — Correcciones de estadísticas, exportación PDF y tipografía NowPlaying

**Fecha:** 28 de abril de 2026

### Corregido

- **Estadísticas no se actualizaban tras enriquecimiento de metadatos** — el panel de estadísticas ahora se recalcula automáticamente cuando termina cualquier actualización de metadatos (manual o periódica) que haya modificado pistas, incluyendo las disparadas desde Configuración con "Actualizar ahora". Antes el panel mostraba los datos anteriores hasta que el usuario lo abría manualmente.
- **Tablas del PDF de estadísticas con dimensiones irregulares** — todas las tablas del PDF de estadísticas ahora ocupan el ancho completo de la hoja (190 mm en A4 portrait). Antes cada tabla usaba anchos hardcodeados distintos que dejaban espacio en blanco a la derecha.
- **Tipografía inconsistente en el NowPlaying al mostrar un CD** — el campo de sello discográfico en el panel NowPlaying aparecía con el estilo del PlayerBar (16px, blanco, sin cursiva) en lugar del estilo estándar del panel (13px, italic, color tenue). La causa era un conflicto de nombres en el archivo de estilos QSS donde dos reglas distintas compartían el nombre `trackLabel`. Se resolvió renombrando la regla del PlayerBar a `playerTrackLabel`.

### Modificado

- **Estandarización tipográfica del NowPlaying** — todas las reglas de estilo del panel NowPlaying (`trackTitle`, `trackArtist`, `trackAlbum`, `trackYear`, `trackLabel`, `trackRating`) ahora declaran explícitamente `font-family`, `font-size`, `font-weight` y `font-style`, sin depender de herencia. Esto garantiza consistencia visual en cualquier contexto.

---

# 0.75 — Exportaciones mejoradas: fuente legible y biblioteca PDF en horizontal

**Fecha:** 27 de abril de 2026

### Modificado

- **Excel (XLSX) — fuente más grande** — la fuente en ambas hojas (Biblioteca y Estadísticas) pasó de tamaño 9 a 11. Las columnas de la hoja Biblioteca se ampliaron proporcionalmente.
- **PDF de estadísticas — fuente más grande** — las tablas de estadísticas usan fuente 9 para datos y 10 para cabeceras (antes 8 y 8). Los títulos de sección usan 11.
- **PDF de biblioteca — orientación horizontal** — la hoja de la biblioteca cambia de vertical a horizontal (A4 landscape), aprovechando el ancho extra (~277mm útiles vs ~190mm en portrait) para mostrar columnas más anchas y más texto en título, artista y álbum sin truncar.

---

# 0.74 — Exportaciones mejoradas: fuente legible y gráficos integrados

**Fecha:** 27 de abril de 2026

### Modificado

- **Excel (XLSX) — fuente más grande** — la fuente de cabeceras, filas y columnas en ambas hojas (Biblioteca y Estadísticas) pasó de tamaño 9 a 11, mejorando significativamente la legibilidad al abrir el archivo en Excel.
- **Excel (XLSX) — gráficos en hoja Estadísticas** — la hoja de estadísticas ahora incluye gráficos visuales al costado de cada tabla de datos: barras verticales para géneros, décadas, formatos y tipo de álbum; barras horizontales para top artistas y países de origen; torta para distribución de formatos. Los gráficos se posicionan automáticamente en la columna E junto a su tabla correspondiente.
- **PDF — fuente más grande** — el tamaño de fuente en la tabla de la biblioteca y las tablas de estadísticas aumentó de 7 a 9, con cabeceras de 9 a 10.
- **PDF — gráficos al costado en Estadísticas** — cada sección del PDF de estadísticas muestra la tabla de datos en la mitad izquierda de la página y un gráfico de barras simple en la mitad derecha, generado directamente desde los datos sin dependencias adicionales.
- **CSV** — sin cambios (el formato CSV es texto plano y no soporta configuración de fuente; el tamaño de letra queda determinado por la aplicación que lo abre).

---

# 0.73 — Estandarización visual de gráficos estadísticos

**Fecha:** 26 de abril de 2026

### Modificado

- **Alturas uniformes en todos los gráficos** — todos los gráficos del panel de estadísticas tienen ahora altura fija (280 px para gráficos de media fila, 340 px para barras horizontales de fila completa). Antes cada gráfico podía variar de altura, causando asimetría visual entre filas.
- **Eliminado el scroll interno de los gráficos** — los marcos de gráficos ya no muestran barras de desplazamiento propias. El scroll del panel completo sigue funcionando normalmente.
- **Leyenda de gráficos de torta a la izquierda** — en los gráficos de distribución (formatos de pistas, géneros), la leyenda se mueve al lateral izquierdo, dejando más espacio para la torta en sí.

---

# 0.72 — Exportaciones separadas por sección

**Fecha:** 26 de abril de 2026

### Modificado

- **Botón "Exportar" dividido en dos** — la barra de herramientas de la biblioteca ahora tiene "Exportar Biblioteca" y "Exportar Estadísticas" como botones independientes.
- **Exportar Biblioteca** — genera un archivo con solo la lista de pistas (XLSX con una hoja, PDF con solo la tabla de canciones, CSV). Sin estadísticas adjuntas.
- **Exportar Estadísticas** — genera un archivo con solo el resumen estadístico (XLSX con una hoja, PDF con solo la sección de estadísticas, CSV en formato Sección/Indicador/Valor). No requiere haber abierto el panel de estadísticas previamente; si no hay datos calculados, los calcula automáticamente antes de exportar.

---

# 0.71 — Rediseño de layout de gráficos estadísticos

**Fecha:** 26 de abril de 2026

### Modificado

- **Gráfico de formatos de pistas** — convertido de barras a torta (pie chart). La distribución por formato ahora se entiende de un vistazo, mostrando proporciones relativas con etiquetas de porcentaje.
- **Layout de gráficos en el panel de estadísticas** — los gráficos regulares ahora se muestran de a dos por fila (mitad del ancho cada uno), reduciendo el scroll necesario. Los gráficos "Top 10" siguen usando el ancho completo de la fila. Cambios concretos: "Formatos de pistas" (torta) y "BitRate de pistas" (barras) en la misma fila; "Pistas por álbum" y "Duración de álbumes" en la misma fila.

---

# 0.70 — Estadísticas de nacionalidades y exportaciones mejoradas

**Fecha:** 26 de abril de 2026

### Agregado

- **Total de nacionalidades en estadísticas generales** — nueva tarjeta en la sección Generales del panel de estadísticas que muestra la cantidad de países de origen únicos representados en la biblioteca.

### Modificado

- **Exportación Excel (XLSX) — tabla de biblioteca** — rediseñada con un tema profesional legible: cabecera gris oscuro con texto blanco, filas alternas en blanco y gris claro (#F2F2F2), texto en negro. La versión anterior usaba fondos casi negros que resultaban ilegibles en Excel.
- **Exportación Excel — hoja de estadísticas** — mismo rediseño visual. Se eliminaron "Top 10 pistas más reproducidas" y "Distribución de ratings". Se agregó "Nacionalidades de artistas" en el resumen general.
- **Exportación PDF — diseño para impresión** — colores completamente rediseñados para impresión: fondo blanco, filas alternas en gris muy claro, cabeceras en gris claro, todo el texto en negro. Los títulos de sección cambian de violeta a gris oscuro. Se eliminaron las mismas secciones que en el Excel y se agregó la nueva estadística.

---

# 0.69 — Enriquecimiento automático de metadatos de la biblioteca

**Fecha:** 26 de abril de 2026

### Agregado

- **Enriquecimiento automático de metadatos** — nuevo servicio que recorre toda la biblioteca y completa los campos faltantes (género, sello, tipo de álbum, país de artista y sello) consultando MusicBrainz en segundo plano. El proceso respeta el límite de 1 solicitud por segundo de MusicBrainz y puede cancelarse en cualquier momento.
- **Actualización automática al importar** — al importar una carpeta con "Importar Carpeta", el enriquecimiento se inicia automáticamente al terminar el escaneo, sin intervención del usuario.
- **Actualización automática al arrancar** — si la opción está habilitada en Configuración y pasó el intervalo configurado, el enriquecimiento corre al iniciar la aplicación.
- **Configuración de programación** — nueva sección en el diálogo de Configuración con opciones para activar/desactivar la actualización automática, definir el intervalo en días y ver la fecha de la última ejecución.
- **Soporte para Last.fm** — campo opcional de API Key de Last.fm en Configuración. Si está configurado, se usa como fuente secundaria de géneros cuando MusicBrainz no tiene datos. Requiere la librería `pylast`.
- **Botón "Actualizar metadatos ahora"** — en el diálogo de Configuración, permite lanzar el enriquecimiento manualmente en cualquier momento.
- **Tags escritos en los archivos** — el enriquecimiento actualiza tanto la base de datos como los tags de los archivos de audio (género, MBID, año).

---

# 0.68 — Correcciones en estadísticas y exportaciones

**Fecha:** 26 de abril de 2026

### Corregido

- **Etiquetas de géneros y artistas no se mostraban en gráficos horizontales** — el fondo del área de gráficos solapaba el espacio reservado para las etiquetas del eje de categorías. Corregido unificando el fondo del chart y aumentando el contraste de los textos de los ejes.
- **Crash al exportar a PDF** — el símbolo de estrella (★) en la columna de ratings no es compatible con la fuente Helvetica de fpdf2. Reemplazado por texto plano (`1/5`, `2/5`, etc.) en la exportación PDF.

### Agregado

- **Valores numéricos sobre cada barra** — todos los gráficos de barras (verticales y horizontales) muestran el número exacto al final de cada barra, sin necesidad de leer el eje.
- **Nuevas secciones en la exportación XLSX** — la hoja "Estadísticas" del Excel ahora incluye tipo de álbum, país de origen de artistas y país de origen de sellos cuando hay datos disponibles.
- **Nuevas secciones en la exportación PDF** — la sección de estadísticas del PDF incluye las mismas tres secciones nuevas.

---

# 0.67 — Estadísticas ampliadas: tipo de álbum, países de artistas y sellos

**Fecha:** 26 de abril de 2026

### Agregado

- **Tipo de álbum en estadísticas** — la sección Álbumes del panel de estadísticas incorpora un gráfico de barras con la distribución por tipo de lanzamiento (Estudio, Single, EP, Compilación, etc.). El dato se obtiene de MusicBrainz al identificar un disco CD y se almacena en la base de datos. Los álbumes sin dato identificado muestran una nota indicando cómo completar la información.
- **País de origen de artistas en estadísticas** — la sección Artistas incorpora un gráfico de barras horizontal con los países de origen de los artistas de la biblioteca. El dato se obtiene de MusicBrainz al identificar un CD y se persiste en la base de datos del artista.
- **País de origen de sellos en estadísticas** — la sección Sellos incorpora un gráfico de barras horizontal con los países de origen de los sellos discográficos. El dato se obtiene de MusicBrainz al identificar un CD.
- **Nueva entidad `Label`** — el dominio de AudioRep incorpora un modelo `Label` con nombre y país de origen, respaldado por una nueva tabla `labels` en la base de datos.

### Modificado

- **MusicBrainz extrae más datos por identificación** — al identificar un CD, el cliente de MusicBrainz ahora obtiene el tipo de lanzamiento del release group, el país/área del artista y el país del sello discográfico. Estos datos se persisten automáticamente en la base de datos al momento de la identificación.
- **Panel de estadísticas actualiza álbumes y artistas existentes** — cuando se identifica un CD, si el álbum o artista ya existe en la biblioteca, sus campos `release_type` y `country` se actualizan automáticamente con el dato de MusicBrainz (si no tenían uno asignado previamente).

---

# 0.66 — Estadísticas ampliadas por secciones

**Fecha:** 26 de abril de 2026

### Agregado
- Panel de estadísticas rediseñado con 6 secciones (tabs): Generales, Pistas, Álbumes, Artistas, Géneros y Sellos Discográficos.
- Sección Generales: tres tarjetas nuevas con el total de géneros únicos, formatos únicos y sellos discográficos únicos en la biblioteca.
- Sección Pistas: gráficos de barras con distribución de duración (6 rangos: 0–2 min, 2–3 min, 3–4 min, 4–5 min, 5–10 min, +10 min), distribución de formatos y distribución de bitrate (0–96 kbps, 96–128 kbps, 128–256 kbps, 256–320 kbps, ≥320 kbps).
- Sección Álbumes: gráficos de barras con distribución de pistas por álbum (4 rangos), distribución de duración de álbumes (5 rangos) y décadas de los álbumes.
- Sección Artistas: gráfico de barras horizontal con top 10 artistas por cantidad de pistas. Se corrigió la visualización del nombre completo del artista en el eje.
- Sección Géneros: mantiene la torta de distribución y agrega un gráfico de barras horizontal con el top 10 de géneros.
- Sección Sellos: gráfico de barras horizontal con el top 10 de sellos discográficos por cantidad de pistas.

### Eliminado
- Gráfico de distribución de ratings: removido del panel de estadísticas por no ser relevante para el análisis de la biblioteca.

---

# 0.65 — Estadísticas de biblioteca y exportación

**Fecha:** 25 de abril de 2026

### Agregado

- **Estadísticas de biblioteca** — nuevo botón "Estadísticas" en la barra superior de la pestaña Biblioteca. Al presionarlo, la vista de la biblioteca se reemplaza por un panel de gráficos interactivos que incluye: tarjetas de resumen (total de pistas, artistas, álbumes y horas de música), distribución por géneros (gráfico de torta), por décadas (barras verticales), por formato de archivo (gráfico de torta), distribución de ratings (barras verticales), top 10 artistas con más pistas y top 10 pistas más reproducidas (barras horizontales). Presionar el botón nuevamente vuelve a la vista de biblioteca.
- **Exportación de biblioteca** — nuevo botón "Exportar" en la barra superior de la pestaña Biblioteca. Permite guardar el contenido de la biblioteca en tres formatos:
  - **Excel (.xlsx):** dos hojas — "Biblioteca" con todas las pistas y "Estadísticas" con todos los datos numéricos (géneros, décadas, formatos, ratings, tops).
  - **PDF (.pdf):** dos secciones con el mismo contenido, optimizadas para impresión.
  - **CSV (.csv):** solo la lista de pistas, compatible con Excel, LibreOffice y Google Sheets.

---

# 0.60 — Sello discográfico, correcciones de NowPlaying y panel CD

**Fecha:** 22 de abril de 2026

### Corregido

- **Portada del CD no se mostraba tras búsqueda manual** — al aplicar metadatos desde el panel "Búsqueda de metadatos" por segunda vez o más, la portada del CD ya no desaparecía del panel NowPlaying.
- **Identificación automática por MusicBrainz fallaba silenciosamente** — el cliente de MusicBrainz usaba un parámetro interno inválido (`label-info`) que causaba error silencioso y devolvía resultados vacíos. Corregido a `labels`.
- **Título de pista visible al identificar un disco** — el campo "Nombre de la pista" en NowPlaying ahora se oculta correctamente al mostrar información de un disco sin pista en reproducción.

### Agregado

- **Sello discográfico en NowPlaying** — el panel NowPlaying ahora muestra el sello discográfico cuando está disponible, entre el nombre del disco y el año.
- **Sello discográfico desde MusicBrainz** — el cliente de MusicBrainz extrae el sello del release y lo incluye en los metadatos normalizados.

### Modificado

- **Panel de detalle en Búsqueda de metadatos rediseñado** — la sección "Detalle" ahora muestra los campos con etiquetas explícitas: "Nombre del Disco:", "Artista:", "Sello Musical:" y "Año:". Los campos sin información se ocultan automáticamente.
- **Orden estándar de NowPlaying** — el panel NowPlaying adopta un orden fijo: portada, título de pista, artista, nombre del disco, sello, año. Este orden se aplica a todos los modos (biblioteca, CD identificado, CD en reproducción).
- **Tipografía unificada en NowPlaying** — el título de pista aparece en negrita e itálica (14px); el resto de los campos en itálica peso normal (13px).

---

# 0.59 — Corrección de título y comportamiento del botón Play tras Stop

**Fecha:** 19 de abril de 2026

### Modificado

- **Título de la ventana simplificado** — la barra de título ya no muestra el nombre de la pista en reproducción; ahora muestra únicamente el nombre y versión de la aplicación ("AudioRep 0.59") en todo momento.
- **Play tras Stop funcional** — al presionar Play después de detener la reproducción con Stop, la aplicación vuelve a reproducir la última pista desde el principio. Antes el botón no hacía nada en ese estado.

---

# 0.58 — Estandarización de diálogos modales

**Fecha:** 19 de abril de 2026

### Modificado

- **Diálogos con tema oscuro** — los formularios emergentes (Configuración, Nueva playlist, Renombrar playlist) ahora aplican el tema visual oscuro de la aplicación: campos de texto con fondo `#2a2a3e`, borde sutil y foco con acento violeta; botones OK/Cancelar con el mismo estilo que los botones de acción del resto de la interfaz.
- **Confirmación en español** — el diálogo "Eliminar playlist" reemplazó los botones "Yes"/"No" de sistema por "Sí"/"No" en español.

---

# 0.57 — Mejoras visuales en controles y panel NowPlaying

**Fecha:** 19 de abril de 2026

### Modificado

- **Botones de transporte sin fondo de color** — los botones Anterior, Stop, Siguiente, Play/Pausa, Shuffle y Repeat ya no muestran el highlight de foco de Windows al hacer clic. Todos tienen fondo transparente y color blanco de forma consistente.
- **Panel NowPlaying mejorado** — ahora muestra el año de la pista cuando está disponible. Los campos sin datos (artista, album, año) se ocultan en lugar de mostrar un guion. La portada del track anterior ya no persiste al cambiar de pista.

---

# 0.56 — Columnas ordenables en Radio (Favoritas) y ajuste visual del reproductor

**Fecha:** 19 de abril de 2026

### Agregado

- **Columnas ordenables en Radio (pestaña Favoritas)** — las columnas Nombre, Pais, Genero y Bitrate son ahora clickeables para ordenar ascendente o descendente.

### Modificado

- **Tamaño del texto de pista en reproduccion** — el nombre de la pista y artista que se muestra en el centro de la barra de controles ahora tiene el mismo tamaño de fuente que los contadores de tiempo (16px).

---

# 0.55 — Columnas ordenables en Radio (Guardadas)

**Fecha:** 19 de abril de 2026

### Agregado

- **Columnas ordenables en Radio (pestaña Guardadas)** — las columnas Nombre, Pais, Genero y Bitrate son ahora clickeables para ordenar ascendente o descendente. El bitrate se ordena numericamente.

---

# 0.54 — Ordenamiento en Radio y fix de reproducción en Playlists

**Fecha:** 19 de abril de 2026

### Agregado

- **Columnas ordenables en Radio (pestaña Buscar)** — las columnas Nombre, País, Género y Bitrate son ahora clickeables para ordenar ascendente o descendente. El bitrate se ordena numéricamente (no como texto).

### Corregido

- **Doble-clic en Playlists siempre reproducía desde el principio** — al hacer doble-clic en cualquier pista de una playlist, la reproducción ahora comienza desde esa pista en lugar de comenzar siempre desde la primera.

---

# 0.53 — Columnas ordenables en Playlists

**Fecha:** 19 de abril de 2026

### Agregado

- **Ordenamiento de columnas en la tabla de pistas de Playlists** — al igual que en la Biblioteca, todas las columnas de la grilla de pistas en el panel de Playlists son ahora clickeables para ordenar de forma ascendente o descendente.

---

# 0.52 — Columnas ordenables en la Biblioteca

**Fecha:** 19 de abril de 2026

### Agregado

- **Ordenamiento de columnas en la tabla de pistas** — todas las columnas de la Biblioteca (Título, Artista, Álbum, Año, Género, Duración, Formato y #) son ahora clickeables. Un clic ordena de forma ascendente; otro clic en la misma columna invierte al orden descendente. La flecha indicadora aparece en el encabezado activo. El orden se mantiene al cambiar la selección del árbol (artista o álbum).

---

# 0.51 — Análisis de audio sin bloqueo

**Fecha:** 18 de abril de 2026

### Modificado

- **Hilo RMS dedicado** — el cálculo de niveles L/R para el vúmetro ya no ocurre dentro del hilo de audio de VLC. Los frames PCM se encolan y son procesados por un hilo `_RMSAnalyzer` separado, eliminando el riesgo de glitches o saltos en la reproducción bajo carga del sistema.
- **Notificación de underruns de audio** — cuando la cola de audio (`_SDAudioBridge`) se llena y descarta frames, ahora se registra una advertencia en el log cada 10 descartes acumulados. El contador se resetea en cada seek o stop.

---

# 0.50 — Dropdowns unificados y refactor de performance

**Fecha:** 18 de abril de 2026

### Modificado

- **Dropdowns estandarizados** — todos los desplegables de la aplicación (selector de lectora de CD, servicio de metadatos, formato de ripeo en Configuración) adoptan ahora un estilo visual unificado: fondo oscuro, borde sutil, `border-radius: 6px` y flecha indicadora chevron en el lateral derecho. El estilo aplica globalmente vía una regla `QComboBox` en `dark.qss`; los estados hover y foco resaltan con el color de acento violeta.
- **Latencia de avance de pista reducida** — el intervalo de polling de posición bajó de 500 ms a 200 ms, reduciendo la latencia promedio de detección de fin de pista de ~500 ms a ~200 ms.
- **VU metro apaga inmediatamente al detener** — al presionar Stop, el vúmetro se apaga al instante (en lugar de esperar el ciclo de decay). En pausa mantiene el decay visual gradual.
- **Actualización de play_count asíncrona** — la escritura en la base de datos al terminar cada pista ahora se ejecuta en un hilo de fondo (`QThread`), eliminando el bloqueo del hilo principal de la UI en la transición entre pistas.

---

# 0.49 — Estandarización de botones

**Fecha:** 17 de abril de 2026

### Modificado

- **Estilo de botones unificado** — todos los botones de acción de la aplicación (Biblioteca, Playlists, Radio, CD) adoptan el mismo estilo: fondo púrpura (`#4a3480`), texto blanco, negrita y bordes redondeados.
- **Botones de Biblioteca alargados** — "Editar tags" e "Identificar" ahora se distribuyen a lo ancho del panel de pistas.
- **Botones de Playlists alargados** — "Reproducir" (antes "Play") y "Quitar pista" ahora se distribuyen a lo ancho del panel de pistas.
- **Botón Play alineado** — el botón de reproducción en la barra de controles ahora tiene el mismo tamaño que los botones secundarios (46×46 px), eliminando el desalineamiento al redimensionar la ventana.

---

# 0.48 — Rediseño de la pestaña CD

**Fecha:** 17 de abril de 2026

### Modificado

- **Fila superior unificada** — el selector de lectora, el estado de detección y la información del disco (artista, álbum, año) ahora conviven en una única fila compacta. Si no hay disco en la unidad, la zona de información muestra "Sin información.".
- **Tabla de pistas más alta** — al eliminar la fila separada de información del disco, la tabla de pistas sube y muestra más pistas sin necesidad de scroll.
- **Botones a ancho completo** — los botones Detectar, Identificar, Reproducir CD y Ripear todo se distribuyen a lo ancho de todo el panel con altura y estilo unificados (mismo diseño que el botón "Aplicar al disco").

---

# 0.47 — Números de tiempo más grandes

**Fecha:** 17 de abril de 2026

### Modificado

- **Números de tiempo de reproducción agrandados** — los contadores de posición y duración en la barra de reproducción aumentaron de 11 px a 16 px, acompañando visualmente el tamaño de los controles de transporte.

---

# 0.46 — Correcciones de UI: Menú y Mute

**Fecha:** 17 de abril de 2026

### Modificado

- **Hover del menú "Archivo" corregido** — el menú de la barra superior ahora respeta la paleta oscura del tema en hover y selección (`QMenuBar` y `QMenu` con reglas QSS estándar: fondo `#2a2a3e`, texto `#e0e0f0`).
- **Ícono de volumen con toggle de silencio** — el ícono del parlante es ahora un botón clickeable (mismo tamaño que los controles secundarios, 46×46 px). Al hacer clic silencia el audio (🔇) y al hacer clic nuevamente restaura el volumen previo (🔊).

---

# 0.44 — Mejoras de Interfaz: Radio con Filtros y Volumen

**Fecha:** 17 de abril de 2026

### Modificado

- **Barra de filtro en "Guardadas" y "Favoritas"** — ambas pestañas de Radio ahora incluyen una fila de búsqueda idéntica a la de "Buscar" (nombre, país, género + botón Filtrar) que filtra el contenido de la tabla localmente en tiempo real, sin llamada a API.
- **"Favoritas" convertida a tabla** — la pestaña Favoritas ahora muestra sus emisoras en una `QTableWidget` con columnas Nombre, País, Género y Bitrate, en línea con el estándar visual del resto de las pestañas de Radio.
- **Volumen inicial al 100% (fix correcto)** — se corrige la causa raíz del slider silenciado al arranque: `audio_get_volume()` devuelve `-1` en modo callback PCM (sounddevice), que se clampeaba a 0. El `PlayerController` ahora inicializa a 100 cuando el player reporta un valor inválido.

---

# 0.42 — Mejoras de Interfaz: Radio y Volumen Inicial

**Fecha:** 16 de abril de 2026

### Modificado

- **Emisoras guardadas como tabla** — la pestaña "Guardadas" de Radio ahora muestra las emisoras en una `QTableWidget` con columnas Nombre, País, Género y Bitrate, en línea con el estándar visual de la pestaña de resultados. Las emisoras marcadas como favorita muestran ♥ al inicio del nombre.
- **Volumen inicial al 100%** — al iniciar la aplicación, el slider de volumen arranca correctamente en el 100% en lugar de quedar en 0 por falta de inicialización del player VLC.

---

# 0.40 — Mejoras de Interfaz: Radio, CD y Barra de Reproducción

**Fecha:** 15 de abril de 2026

### Modificado

- **Resultados de radio como tabla** — la pestaña Radio ahora muestra los resultados de búsqueda en una `QTableWidget` con columnas Nombre, País, Género y Bitrate, en línea con el estándar visual de grillas del resto de la aplicación
- **Campos de filtro de radio ampliados** — los campos País y Género son ahora más anchos (160 px cada uno), y el botón Buscar tiene un ancho mínimo de 100 px, evitando el corte del texto
- **Panel de CD sin portada** — eliminada la portada del panel de CD; la imagen ya se muestra en el NowPlaying lateral, por lo que duplicarla no aportaba valor. La tabla de pistas gana todo ese espacio vertical
- **Estado del disco inline en CD** — la etiqueta "No hay CD" / "Disco detectado" se movió a la misma fila que el selector de lectora, eliminando el bloque visual de info separado
- **Info del disco en una sola línea** — artista, álbum y año se muestran ahora juntos en una línea compacta sobre la tabla de pistas (`Artista — Álbum (Año)`)
- **Barra de progreso a ancho completo** — la barra de tiempo (seek slider) ocupa ahora el ancho completo de la barra de reproducción, sin las etiquetas de tiempo restando espacio a los lados
- **Etiquetas de tiempo reubicadas** — los tiempos transcurrido y total se movieron a la fila superior de controles, flanqueando el nombre de la pista, liberando la fila inferior para la barra de progreso
- **Slider de volumen ampliado** — el slider de volumen ahora tiene un ancho mínimo de 180 px (máx. 280 px) para alinearse visualmente con el VU metro del panel derecho
- **Íconos de controles totalmente blancos** — los botones de modo (shuffle/repeat) ahora muestran sus íconos en blanco completo en todos los estados, coherente con el resto de los controles de transporte

### Corregido

- **Crash al iniciar con radio** — `RadioPanel` lanzaba `AttributeError: '_station_label'` al cargar las emisoras guardadas. El método fue restaurado ya que las listas de Guardadas y Favoritas lo siguen necesitando
- **Tema oscuro en listas de metadatos de CD** — los `QListWidget` de resultados y pistas del panel de metadatos aparecían con fondo blanco (estilo nativo de Windows). Causa: `border-radius` en QSS impide que Qt aplique el color de fondo al viewport interno. Se eliminó `border-radius` y se agregaron `alternate-background-color` y regla de hover

---

# 0.35 — VU Metro Real, Tabla de Pistas CD y Correcciones de UI

**Fecha:** 15 de abril de 2026

### Agregado

- **VU metro estéreo con análisis real** — el vúmetro ahora intercepta el stream PCM de VLC via `libvlc_audio_set_callbacks` y reproduce el audio a través de `sounddevice`. Los 24 canales se dividen en 12 para L y 12 para R, mostrando niveles RMS reales con peak hold por canal y divisor central. Incluye fallback a simulación si sounddevice no está disponible
- **`sounddevice`** agregado como nueva dependencia de runtime para la salida de audio del análisis PCM

### Modificado

- **Lista de pistas del CD ahora es una tabla** — la pestaña CD usa `QTableWidget` con columnas (#, Título, Estado) y cabeceras con el mismo estilo visual estándar que la Biblioteca y Playlists, en lugar de la lista plana anterior
- **Portada en NowPlaying se mantiene al reproducir** — corregido el bug por el que la portada identificada del CD desaparecía al iniciar la reproducción. La imagen ahora persiste entre cambios de pista mientras sea del mismo CD
- **Portada se limpia correctamente al eyectar el CD** — `_on_cd_ejected` ahora llama a `clear_cover()` en NowPlaying, evitando que la imagen quede varada cuando no hay disco
- **VU metro más alto** — altura aumentada de 90 px a 110 px

---

# 0.30 — Corrección de CD y Búsqueda Manual de Metadatos

**Fecha:** 15 de abril de 2026

### Agregado

- **Panel de metadatos manual de CD** — nueva columna lateral dentro del tab CD con un desplegable "Servicio" para elegir la fuente de búsqueda, lista de resultados con artista/álbum/año, detalle de pistas del resultado seleccionado y botón "Aplicar al disco" que actualiza el panel principal
- **GnuDB** — soporte para búsqueda de metadatos de CD en GnuDB (sucesor libre y gratuito de FreeDB/CDDB), sin API key requerida. Complementa la búsqueda existente de MusicBrainz
- **Cálculo de Disc ID CDDB** — AudioRep ahora computa y almacena el identificador CDDB/FreeDB del disco (formato estándar de 8 caracteres hexadecimales), necesario para la consulta a GnuDB
- **Búsqueda asíncrona** — las consultas a servicios de metadatos se ejecutan en un hilo separado para que la UI no se bloquee durante los requests HTTP

### Corregido

- **Reproducción de CD** — corregida la generación de URIs CDDA para VLC. Ahora se usa el URI del dispositivo (`cdda:///D:/`) con el número de pista como media option (`:cdda-track=N`), que es el formato correcto que acepta el módulo CDDA de VLC
- **Identificación automática de CD** — corregida la normalización de la respuesta de MusicBrainz. El worker de identificación ahora recibe los datos en el formato esperado (claves `album`, `artist`, `year`, `release_id`, `tracks`), lo que permite completar correctamente el artista, álbum, año y títulos de pistas

---

# 0.25 — Rediseño de Interfaz y Correcciones

**Fecha:** 14 de abril de 2026

### Agregado

- **Vúmetro animado** — nuevo panel inferior derecho con barras de colores (verde → amarillo → rojo) que se animan durante la reproducción y se apagan gradualmente al detenerla
- **Selector de lectora de CD** — nuevo desplegable en la pestaña CD para elegir la unidad de disco, útil en equipos con múltiples lectoras
- **Botón Stop** — agregado a la barra de controles de reproducción (entre el botón de pista anterior y Play)

### Modificado

- **NowPlaying movido al panel derecho** — la portada y datos de la pista actual ahora se muestran en un panel lateral derecho (antes estaba a la izquierda), compartiendo espacio vertical con el vúmetro
- **Pestañas rediseñadas** — las pestañas Biblioteca, CD, Playlists y Radio ahora usan el color de acento del programa: activa con subrayado violeta, inactiva con texto atenuado
- **Controles de reproducción mejorados** — botones más grandes y envueltos en un contenedor redondeado con fondo ligeramente distinto al del resto de la barra
- **Grilla de Playlist** — ahora usa el mismo estilo visual estándar (`trackTable`) que la grilla de la biblioteca
- **Panel de CD** — ocupa todo el espacio disponible del tab; lista de pistas expandible hacia abajo con los botones de acción fijados en la parte inferior
- **Reproducción de CD corregida** — las pistas de CD ahora se pasan al reproductor VLC con URIs CDDA correctas (`cdda:///D:@1` en Windows, `cdda:///dev/sr0@1` en Linux), corrigiendo la regresión que impedía la reproducción desde la v0.10

---

# 0.20 — Radio por Internet

**Fecha:** 12 de abril de 2026

### Agregado

- **Panel de radio** — nueva pestaña *📻 Radio* en la ventana principal
- Búsqueda de emisoras en tiempo real a través de [radio-browser.info](https://radio-browser.info) (más de 30.000 estaciones)
- Filtros de búsqueda por nombre, país (código ISO) y género musical
- Reproducción de streams de radio vía VLC (HTTP, HTTPS, M3U, PLS, etc.)
- Guardado de emisoras en la base de datos local para acceso rápido
- Lista de favoritas — marcado/desmarcado con ♥
- Gestión completa: guardar desde resultados, eliminar y alternar favorita desde las listas
- Etiqueta de reproducción en curso con nombre de emisora y bitrate
- Estilos QSS para todos los nuevos elementos visuales del panel de radio
- Migración automática de base de datos (v2) para la nueva tabla `radio_stations`

---

# 0.10 — Versión Inicial

**Fecha:** 12 de abril de 2026

### Agregado

- Reproducción de música local con soporte para MP3, FLAC, OGG, OPUS, AAC, M4A, WMA, WAV, APE y MPC
- Controles de reproducción: play/pausa/stop, pista anterior/siguiente, barra de progreso y control de volumen
- Biblioteca musical con importación de carpetas, navegación por artista y álbum, y búsqueda en tiempo real
- Edición de metadatos (tags) de archivos de audio
- Organización automática de archivos según la estructura `Artista/Álbum/NN - Título`
- Identificación automática de pistas por huella de audio (AcoustID + MusicBrainz)
- Soporte para CD: detección, identificación online, reproducción directa y ripeo en FLAC, MP3, OGG o WAV
- Playlists manuales: crear, renombrar y eliminar
- Playlists inteligentes automáticas: más reproducidas, mejor valoradas y agregadas recientemente
- Menú *Archivo* con acceso a Configuración y Salir
- Diálogo de configuración con ajustes de API key de AcoustID, formato de ripeo y directorio de salida
- Interfaz visual con tema oscuro completo (QSS)
- Persistencia de configuración mediante `QSettings` (registro de Windows / archivo de configuración en Linux)
- Instalador para Windows (directorio autocontenido, sin dependencias externas)
- Instalador para Linux Debian/Ubuntu (paquete `.deb`)
