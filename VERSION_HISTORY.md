# Historial de versiones — AudioRep

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
