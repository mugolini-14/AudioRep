# Historial de versiones — AudioRep

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
