# Historial de versiones — AudioRep

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
