# AudioRep

AudioRep es un reproductor de música de escritorio para Windows, hecho en Python. Permite escuchar música local, gestionar una biblioteca de canciones, trabajar con CDs físicos y organizar listas de reproducción, todo desde una interfaz visual oscura y limpia.

## Funciones principales

- **Reproducción de música local** — soporta MP3, FLAC, OGG, OPUS, AAC, M4A, WMA, WAV, APE y MPC. Controles de play/pausa/stop/anterior/siguiente con íconos blancos y barra de progreso a ancho completo. El control de volumen aparece junto a los controles principales. El ícono del parlante actúa como botón de silencio: al hacer clic se mutea o desmutea el audio, restaurando automáticamente el nivel anterior.

- **Biblioteca musical** — importá carpetas para agregar canciones. Navegación por artista y álbum, búsqueda en tiempo real y edición de metadatos (tags). La tabla de pistas es ordenable: hacé clic en cualquier columna (Título, Artista, Álbum, Año, Género, Duración, Formato) para ordenar en forma ascendente o descendente. Los archivos se organizan automáticamente siguiendo la estructura `Artista/Álbum/NN - Título`. El botón **Estadísticas** reemplaza la vista de pistas por un panel de gráficos interactivos organizado en 6 secciones: Generales (totales de pistas, artistas, álbumes, horas, géneros, formatos y sellos), Pistas (distribución por duración, formato y bitrate), Álbumes (distribución por cantidad de pistas, duración, décadas y tipo de lanzamiento), Artistas (top 10 por pistas y distribución de países de origen), Géneros (torta de distribución y top 10 en barras) y Sellos (top 10 sellos por pistas y distribución de países de origen de sellos). El botón **Exportar** permite guardar toda la biblioteca en Excel (con hoja de estadísticas), PDF o CSV.

- **Identificación automática de pistas** — usando huella de audio (AcoustID + MusicBrainz), AudioRep puede reconocer una canción y completar sus datos automáticamente.

- **Soporte para CD** — detecta el disco insertado, lo identifica online y permite reproducirlo directamente o ripearlo (copiarlo) al disco en formato FLAC, MP3, OGG o WAV. Incluye selector de lectora para sistemas con varias unidades de CD. El panel muestra artista, álbum y año en una línea compacta sobre la tabla de pistas. El panel de metadatos manual permite buscar y aplicar información desde MusicBrainz o GnuDB con un clic, usando el desplegable "Servicio". Los resultados muestran nombre del disco, artista, sello musical y año con etiquetas claras.

- **Playlists** — creá, renombrá y eliminá listas de reproducción. También incluye listas inteligentes automáticas: las más reproducidas, las mejor valoradas y las agregadas recientemente.

- **Radio por internet** — buscá emisoras en tiempo real usando radio-browser.info (más de 30.000 estaciones). Los resultados, las emisoras guardadas y las favoritas se muestran en tablas con columnas de nombre, país, género y bitrate. Las pestañas Guardadas y Favoritas incluyen una barra de filtro local por nombre, país y género. Guardá tus favoritas, marcalas con ♥ y reproducílas con un clic.

- **Visualización en vivo** — panel derecho con información de la pista actual (portada, título, artista, álbum, año y sello discográfico cuando está disponible) y un vúmetro estéreo que analiza el audio en tiempo real (canales L/R con barras de colores y peak hold).

- **Configuración** — accesible desde el menú *Archivo → Configuración*. Permite ingresar la API key de AcoustID y definir el formato y directorio de ripeo.

---

## Aspectos técnicos

### Lenguaje y entorno

- **Python 3.11+** como lenguaje principal (compatible con 3.13).
- **PyQt6** para toda la interfaz gráfica (ventanas, widgets, señales/slots, estilos QSS).

### Librerías principales

| Librería | Uso |
|---|---|
| `python-vlc` | Reproducción de audio y ripeo de CD (via libVLC con sout transcoding) |
| `mutagen` | Lectura y escritura de tags en archivos de audio (ID3, Vorbis, MP4) |
| `musicbrainzngs` | Búsqueda de metadatos de álbumes, pistas y CDs en MusicBrainz |
| `discid` | Lectura del identificador único (disc ID) de un CD físico |
| `pyacoustid` | Identificación de pistas por huella de audio (requiere `fpcalc` en el PATH) |
| `Pillow` | Procesamiento de imágenes de portada |
| `requests` | Descarga de portadas desde Cover Art Archive y búsqueda de emisoras de radio |
| `sounddevice` | Salida de audio PCM para el análisis real del vúmetro (intercepta el stream de VLC) |
| `PyQt6-Charts` | Gráficos interactivos (torta, barras) en el panel de estadísticas de la biblioteca |
| `openpyxl` | Generación de archivos Excel (.xlsx) con dos hojas al exportar la biblioteca |
| `fpdf2` | Generación de archivos PDF al exportar la biblioteca |

### Herramientas de desarrollo

| Herramienta | Uso |
|---|---|
| `pytest` + `pytest-qt` | Tests unitarios e integración con la UI |
| `pytest-cov` | Cobertura de código |
| `ruff` | Linter y formateador (máximo 100 caracteres por línea) |
| `mypy` | Type checking estricto |

### Persistencia

- **Base de datos**: SQLite (sin ORM). Almacena artistas, álbumes, pistas, playlists y emisoras de radio en `data/audiorep.db`.
- **Configuración**: `QSettings` (registro de Windows / archivo de configuración en Linux). Almacena la API key de AcoustID, formato de ripeo y directorio de salida.
- **Portadas**: descargadas desde Cover Art Archive y cacheadas en `data/covers/`.

### Arquitectura

AudioRep usa **Clean Architecture** con cinco capas y dependencias en un solo sentido:

```
domain → core → services ← infrastructure
                    ↑
              UI (controllers → widgets)
```

- **`domain/`** — Modelos puros del negocio (`Track`, `Album`, `Artist`, `Label`, `Playlist`, `CDDisc`). Sin dependencias externas.
- **`core/`** — Contratos (interfaces `Protocol`), bus de eventos global (`app_events`), configuración persistente (`AppSettings`) y utilidades. Los services solo importan de acá, nunca de `infrastructure/`.
- **`services/`** — Lógica de negocio. Cada service es un `QObject`. Las operaciones largas (importar biblioteca, ripear, identificar huella) se delegan a workers internos (`QThread`) para no bloquear la UI.
- **`infrastructure/`** — Implementaciones concretas: base de datos SQLite, sistema de archivos, VLC, y clientes de APIs externas. Solo se instancian en `main.py`.
- **`ui/`** — Widgets (solo emiten señales, no llaman services), controllers (conectan señales con services) y diálogos. El estilo visual está íntegramente en `dark.qss`.

Toda la inyección de dependencias ocurre en `main.py`, que actúa como raíz de composición.

### Instaladores

| Plataforma | Versión | Fecha | Archivo | Tamaño |
|---|---|---|---|---|
| Windows 10/11 | 0.75 | Abril 2026 | `AudioRep-0.75.0-windows.zip` | ~120 MB |
| Linux Debian/Ubuntu | 0.75 | Abril 2026 | `audiorep_0.75.0_amd64.deb` | ~84 MB |

Los instaladores están disponibles en la sección [Releases](https://github.com/mugolini-14/AudioRep/releases) del repositorio.

#### Windows

El instalador es un **directorio autocontenido**. Incluye las DLLs de VLC y todos sus plugins, por lo que **no requiere ninguna instalación adicional** en el equipo del usuario final.

Para instalarlo:
1. Descargar el `.zip` y descomprimir.
2. Ejecutar `AudioRep.exe`.

#### Linux (Debian / Ubuntu)

El paquete `.deb` instala AudioRep en `/opt/audiorep/` y crea una entrada en el menú de aplicaciones. Requiere que **VLC** esté instalado en el sistema.

Para instalarlo:
```bash
sudo dpkg -i audiorep_<version>_amd64.deb
sudo apt-get install -f   # instala dependencias faltantes si las hay
```

Para desinstalarlo:
```bash
sudo dpkg -r audiorep
```

Para generar una nueva versión de los instaladores, ver las instrucciones en `CLAUDE.md`.
