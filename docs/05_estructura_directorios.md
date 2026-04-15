# AudioRep — Estructura de Directorios

```
audiorep/                                ← raíz del proyecto
│
├── main.py                              ← Entry point y composición raíz (DI)
├── pyproject.toml                       ← Configuración del proyecto y dependencias
├── requirements.txt                     ← Dependencias para pip install
│
├── docs/                                ← Documentación técnica
│   ├── 01_arquitectura.md
│   ├── 02_dominio.md
│   ├── 03_interfaces.md
│   ├── 04_eventos.md
│   ├── 05_estructura_directorios.md
│   └── 06_guia_desarrollo.md
│
├── audiorep/                            ← Paquete principal
│   ├── __init__.py
│   ├── __main__.py                      ← Permite: python -m audiorep
│   │
│   ├── domain/                          ← [CAPA 1] Entidades del negocio
│   │   ├── __init__.py                  ← Re-exporta todas las entidades
│   │   ├── track.py                     ← Track, AudioFormat, TrackSource
│   │   ├── album.py                     ← Album
│   │   ├── artist.py                    ← Artist
│   │   ├── playlist.py                  ← Playlist, PlaylistEntry
│   │   └── cd_disc.py                   ← CDDisc, CDTrack, RipStatus
│   │
│   ├── core/                            ← [CAPA 2] Contratos y utilidades compartidas
│   │   ├── __init__.py
│   │   ├── interfaces.py                ← Protocols: IAudioPlayer, IRepository, etc.
│   │   ├── events.py                    ← Bus de eventos global (app_events)
│   │   ├── exceptions.py               ← Jerarquía de excepciones del dominio
│   │   └── utils.py                     ← Funciones puras reutilizables
│   │
│   ├── infrastructure/                  ← [CAPA 3] Implementaciones concretas
│   │   ├── __init__.py
│   │   │
│   │   ├── database/                    ← Persistencia SQLite
│   │   │   ├── __init__.py
│   │   │   ├── connection.py            ← Conexión, migraciones de schema
│   │   │   └── repositories/
│   │   │       ├── __init__.py
│   │   │       ├── track_repository.py  ← Implementa ITrackRepository
│   │   │       ├── album_repository.py  ← Implementa IAlbumRepository
│   │   │       ├── artist_repository.py ← Implementa IArtistRepository
│   │   │       └── playlist_repository.py
│   │   │
│   │   ├── audio/                       ← Reproducción y hardware de audio
│   │   │   ├── __init__.py
│   │   │   ├── vlc_player.py            ← Implementa IAudioPlayer con python-vlc
│   │   │   └── cd_reader.py             ← Implementa ICDReader con discid
│   │   │
│   │   ├── filesystem/                  ← Operaciones con archivos
│   │   │   ├── __init__.py
│   │   │   ├── scanner.py               ← Implementa ILibraryScanner
│   │   │   ├── tagger.py                ← Implementa IFileTagger con mutagen
│   │   │   └── organizer.py             ← Mueve/renombra archivos según tags
│   │   │
│   │   └── api/                         ← Clientes de APIs externas
│   │       ├── __init__.py
│   │       ├── musicbrainz_client.py    ← Implementa IMetadataProvider
│   │       ├── coverart_client.py       ← Descarga portadas de Cover Art Archive
│   │       ├── acoustid_client.py       ← Implementa IFingerprintProvider
│   │       └── discogs_client.py        ← Implementa IMetadataProvider (alternativo)
│   │
│   ├── services/                        ← [CAPA 4] Casos de uso / lógica de negocio
│   │   ├── __init__.py
│   │   ├── player_service.py            ← Reproducción, cola, historial
│   │   ├── library_service.py           ← Importar, escanear, gestionar biblioteca
│   │   ├── cd_service.py                ← Detectar CD, leer pistas, buscar info online
│   │   ├── ripper_service.py            ← Orquestar el ripeo de CD
│   │   ├── tagger_service.py            ← Leer/escribir tags, buscar metadatos
│   │   └── search_service.py            ← Búsqueda full-text en la biblioteca
│   │
│   └── ui/                              ← [CAPA 5] Interfaz gráfica PyQt6
│       ├── __init__.py
│       ├── main_window.py               ← Ventana principal, layout general
│       │
│       ├── controllers/                 ← Conectan señales UI ↔ services
│       │   ├── __init__.py
│       │   ├── player_controller.py
│       │   ├── library_controller.py
│       │   ├── cd_controller.py
│       │   └── tagger_controller.py
│       │
│       ├── widgets/                     ← Componentes visuales reutilizables
│       │   ├── __init__.py
│       │   ├── player_bar.py            ← Play/Pausa/Stop/Sig./Vol./Progreso
│       │   ├── library_panel.py         ← Árbol Artistas > Álbumes > Pistas
│       │   ├── now_playing.py           ← Portada + info de la pista actual (panel derecho)
│       │   ├── cd_panel.py              ← Estado del CD, selector de lectora, pistas, ripeo
│       │   ├── playlist_panel.py        ← Gestión de playlists + grilla estándar
│       │   ├── vu_meter.py              ← Vúmetro animado con barras de colores (panel derecho)
│       │   └── search_bar.py
│       │
│       ├── dialogs/                     ← Ventanas modales
│       │   ├── __init__.py
│       │   ├── settings_dialog.py
│       │   ├── tag_editor_dialog.py     ← Edición manual de tags
│       │   ├── ripper_dialog.py         ← Progreso del ripeo
│       │   └── import_dialog.py         ← Importar carpetas a la biblioteca
│       │
│       ├── qt_models/                   ← QAbstractItemModel para las vistas Qt
│       │   ├── __init__.py
│       │   ├── track_table_model.py     ← Para QTableView de pistas
│       │   ├── album_list_model.py      ← Para QListView de álbumes
│       │   └── playlist_model.py
│       │
│       └── style/
│           ├── dark.qss                 ← Tema oscuro
│           └── light.qss               ← Tema claro
│
└── tests/                               ← Tests automatizados
    ├── __init__.py
    ├── unit/
    │   ├── domain/                      ← Tests de modelos de dominio
    │   └── services/                    ← Tests de services (con mocks)
    └── integration/                     ← Tests con DB real y archivos reales
```

---

## Convenciones de Nomenclatura

| Tipo | Convención | Ejemplo |
|---|---|---|
| Archivos Python | `snake_case.py` | `track_repository.py` |
| Clases | `PascalCase` | `TrackRepository` |
| Interfaces (Protocols) | `I` + PascalCase | `ITrackRepository` |
| Instancias | `snake_case` | `track_repo` |
| Constantes | `UPPER_SNAKE_CASE` | `AUDIO_EXTENSIONS` |
| Señales PyQt6 | `snake_case` | `track_changed` |
| Archivos de test | `test_` + nombre | `test_track.py` |
