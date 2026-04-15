# AudioRep — Arquitectura del Sistema

## Visión General

AudioRep es un reproductor de música de escritorio desarrollado en Python con PyQt6.
Soporta reproducción de archivos locales (MP3, FLAC, OGG, etc.) y CDs físicos,
ripeo de CDs, identificación automática de metadatos vía internet, edición de tags
y radio por internet.

La arquitectura sigue los principios de **Clean Architecture**:
las capas internas no conocen a las externas, y las dependencias siempre apuntan
hacia el centro (dominio).

---

## Diagrama de Capas

```
┌──────────────────────────────────────────────────────────────┐
│                        UI (PyQt6)                            │
│       Vistas · Widgets · Qt Models · Diálogos                │
│                    ↕ señales/slots                            │
│                    Controllers                               │
└───────────────────────┬──────────────────────────────────────┘
                        │ llama métodos
┌───────────────────────▼──────────────────────────────────────┐
│                      Services                                │
│   PlayerService · LibraryService · CDService                 │
│   RipperService · TaggerService  · SearchService             │
└──────┬─────────────────┬──────────────────┬──────────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼──────┐  ┌────────▼───────────────┐
│  Database   │  │  Filesystem  │  │     API Clients         │
│ Repos SQLite│  │ Scanner/Tagger│  │ MusicBrainz · CoverArt │
└──────┬──────┘  └───────┬──────┘  └────────┬───────────────┘
       │                 │                  │
┌──────▼─────────────────▼──────────────────▼────────────────┐
│                        Domain                               │
│        Track · Album · Artist · Playlist · CDDisc           │
│          (dataclasses puras, sin dependencias)              │
└─────────────────────────────────────────────────────────────┘
```

---

## Reglas de la Arquitectura

| Regla | Motivo |
|---|---|
| `domain/` no importa nada del proyecto | Es el núcleo; debe ser testeable sin frameworks |
| `core/` solo importa de `domain/` | Contratos y utilidades sin implementaciones |
| `services/` importa de `domain/` y `core/` únicamente | Nunca importa `PyQt6`, `vlc` ni SQLite directamente |
| `infrastructure/` implementa los contratos de `core/interfaces.py` | Permite sustituir implementaciones sin tocar services |
| `ui/` nunca accede a `infrastructure/` directamente | Todo pasa por un service |
| `ui/controllers/` es la única conexión UI ↔ services | Los widgets no llaman services directamente |
| Toda API externa vive en `infrastructure/api/` | Fácil de mockear en tests o cambiar de proveedor |

---

## Flujo de una Acción Típica

### Ejemplo: el usuario presiona "Play"

```
1. PlayerBar (widget)          → emite señal btn_play.clicked
2. PlayerController            → captura la señal, llama player_service.resume()
3. PlayerService               → llama vlc_player.resume()  [IAudioPlayer]
4. VLCPlayer (infrastructure)  → controla libVLC
5. PlayerService               → emite app_events.playback_resumed
6. PlayerBar (widget)          → recibe la señal, actualiza ícono del botón
```

---

## Composición Raíz (main.py)

El único lugar donde todas las capas se instancian y conectan es `main.py`.
Esto garantiza que:
- Las dependencias son explícitas y visibles.
- No hay "service locators" ni singletons ocultos (excepto `app_events`).
- El reemplazo de implementaciones es trivial.

```python
# main.py — composición raíz simplificada
db          = DatabaseConnection("audiorep.db")
track_repo  = TrackRepository(db)
vlc_player  = VLCPlayer()
mb_client   = MusicBrainzClient(app_name="AudioRep", version="0.1.0")

player_service  = PlayerService(player=vlc_player, repo=track_repo)
library_service = LibraryService(repo=track_repo, tagger=FileTagger())
cd_service      = CDService(reader=CDReader(), metadata=mb_client)

window = MainWindow(player_service, library_service, cd_service)
```

---

## Layout de la Ventana Principal (v0.25+)

```
┌────────────────────────────────────────────────────────────┐
│  [Biblioteca][CD][Playlists][Radio]  │  NowPlaying (top)  │
│  LibraryPanel / CDPanel /            │  (portada + info)  │
│  PlaylistPanel / RadioPanel          ├────────────────────┤
│                                      │  VU Meter (bottom) │
├──────────────────────────────────────────────────────────  ┤
│  Barra de estado                                           │
├────────────────────────────────────────────────────────────┤
│  PlayerBar (transportFrame + progreso + volumen)           │
└────────────────────────────────────────────────────────────┘
```

- El **panel derecho** (NowPlaying + VU Meter) está fijo a la derecha de la ventana
  con un ancho entre 210 y 320 px.
- El **NowPlaying** muestra portada, título, artista y álbum.
- El **VU Meter** anima barras de colores (verde → amarillo → rojo) en respuesta
  a los eventos `playback_started`, `playback_paused` y `playback_stopped`.
- Los **controles de reproducción** (shuffle, prev, stop, play, next, repeat) están
  envueltos en un `QFrame#transportFrame` con bordes redondeados.

---

## Tecnologías Utilizadas

| Componente | Librería | Versión mínima |
|---|---|---|
| Interfaz gráfica | PyQt6 | 6.6 |
| Reproducción de audio | python-vlc | 3.0 |
| Lectura/escritura de tags | mutagen | 1.47 |
| Consulta a MusicBrainz | musicbrainzngs | 0.7.1 |
| Cálculo de Disc ID | discid | 1.2 |
| Fingerprinting de audio | pyacoustid | 1.3 |
| Descarga de recursos | requests | 2.31 |
| Procesamiento de imágenes | Pillow | 10.0 |
| Base de datos local | SQLite (stdlib) | — |
| Testing | pytest + pytest-qt | 7.4 |
| Linting | ruff | 0.1 |
| Type checking | mypy | 1.7 |
