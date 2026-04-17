# AudioRep — Interfaces y Contratos

## Descripción

Los contratos del sistema se definen como `Protocol` de Python en
`audiorep/core/interfaces.py`. Permiten que los Services dependan de
abstracciones y no de implementaciones concretas.

Esto facilita:
- Cambiar el backend de reproducción (VLC → otro) sin tocar los services.
- Mockear dependencias en los tests unitarios.
- Agregar nuevos proveedores de metadatos sin romper el resto.

---

## Interfaces Disponibles

### `IAudioPlayer` — Reproducción de Audio

Implementado por: `infrastructure/audio/vlc_player.py`

```python
class IAudioPlayer(Protocol):
    def play(self, track: Track) -> None
    def pause(self) -> None
    def resume(self) -> None
    def stop(self) -> None
    def seek(self, position_ms: int) -> None
    def get_position_ms(self) -> int
    def get_duration_ms(self) -> int
    def set_volume(self, volume: int) -> None   # 0–100
    def get_volume(self) -> int
    @property is_playing: bool
    @property is_paused: bool
```

---

### Repositories — Acceso a Datos

Implementados en: `infrastructure/database/repositories/`

| Interface | Implementación | Responsabilidad |
|---|---|---|
| `ITrackRepository` | `TrackRepository` | CRUD de pistas |
| `IAlbumRepository` | `AlbumRepository` | CRUD de álbumes |
| `IArtistRepository` | `ArtistRepository` | CRUD de artistas |
| `IPlaylistRepository` | `PlaylistRepository` | CRUD de playlists |

Métodos comunes a todos los repositories:
- `get_by_id(id)` → entidad o None
- `get_all()` → lista de entidades
- `search(query)` → lista filtrada
- `save(entity)` → entidad con ID asignado
- `delete(id)` → None

---

### `IMetadataProvider` — Metadatos Online

Implementado por: `MusicBrainzClient` (primario), `GnuDBClient` (alternativo para CDs)

```python
class IMetadataProvider(Protocol):
    def search_by_disc_id(self, disc_id: str) -> list[dict]
    def search_album(self, artist: str, title: str) -> list[dict]
    def get_track_info(self, recording_id: str) -> dict | None
    def get_cover_url(self, release_id: str) -> str | None
```

---

### `IFingerprintProvider` — Identificación por Audio

Implementado por: `AcoustIDClient`

```python
class IFingerprintProvider(Protocol):
    def identify(self, file_path: str) -> list[dict]
    # Retorna lista de candidatos con score y recording_id de MusicBrainz
```

---

### `IFileTagger` — Tags de Audio

Implementado por: `infrastructure/filesystem/tagger.py` (mutagen)

```python
class IFileTagger(Protocol):
    def read_tags(self, file_path: str) -> dict
    def write_tags(self, file_path: str, tags: dict) -> None
    def read_embedded_cover(self, file_path: str) -> bytes | None
    def write_embedded_cover(self, file_path: str, image_data: bytes) -> None
```

---

### `ILibraryScanner` — Escáner de Directorios

Implementado por: `infrastructure/filesystem/scanner.py`

```python
class ILibraryScanner(Protocol):
    def scan(self, directory: str) -> list[str]
    # Retorna rutas absolutas de todos los archivos de audio encontrados
```

---

### `ICDReader` — Lector de CD

Implementado por: `infrastructure/audio/cd_reader.py` (discid)

```python
class ICDReader(Protocol):
    def read_disc(self, drive: str = "") -> CDDisc
    def list_drives(self) -> list[str]
```

---

### `ICDRipper` — Ripeador de CD

```python
class ICDRipper(Protocol):
    def rip_track(self, disc, track_number, output_path, format="flac") -> None
    def rip_all(self, disc, output_dir, format="flac") -> None
```

---

### `IRadioStationRepository` — Repositorio de Emisoras

Implementado por: `infrastructure/database/repositories/radio_station_repository.py`

```python
class IRadioStationRepository(Protocol):
    def get_by_id(self, station_id: int) -> RadioStation | None
    def get_all(self) -> list[RadioStation]         # ordenadas por nombre
    def get_favorites(self) -> list[RadioStation]
    def save(self, station: RadioStation) -> RadioStation
    def delete(self, station_id: int) -> None
    def set_favorite(self, station_id: int, is_favorite: bool) -> None
```

---

### `IRadioSearchProvider` — Búsqueda de Emisoras Online

Implementado por: `infrastructure/api/radio_browser_client.py`

```python
class IRadioSearchProvider(Protocol):
    def search(self, query="", country="", genre="", limit=50) -> list[RadioStation]
    def get_by_id(self, radio_browser_id: str) -> RadioStation | None
```

---

## Inyección de Dependencias

AudioRep usa **inyección de dependencias manual** (sin frameworks).
La composición ocurre únicamente en `main.py`:

```python
# El service recibe la interfaz en el constructor
player_service = PlayerService(
    player=VLCPlayer(),          # implementa IAudioPlayer
    repo=TrackRepository(db),    # implementa ITrackRepository
)
```

Para tests, se inyectan mocks:

```python
player_service = PlayerService(
    player=MockPlayer(),
    repo=InMemoryTrackRepository(),
)
```
