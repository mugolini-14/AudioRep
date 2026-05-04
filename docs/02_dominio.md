# AudioRep — Modelos de Dominio

## Descripción

El dominio es el núcleo de la aplicación. Contiene las entidades del negocio
como clases Python puras (`@dataclass`), sin dependencias de frameworks,
bases de datos ni APIs externas.

Todos los modelos viven en `audiorep/domain/`.

---

## Entidades

### `Track` — Pista de Audio

Entidad central del sistema. Representa un archivo de audio local o una pista de CD.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno (None si no persistido) |
| `title` | `str` | Título de la pista |
| `artist_name` | `str` | Nombre del artista (desnormalizado) |
| `album_title` | `str` | Título del álbum (desnormalizado) |
| `track_number` | `int` | Número de pista en el disco |
| `disc_number` | `int` | Número de disco (álbumes dobles) |
| `duration_ms` | `int` | Duración en milisegundos |
| `year` | `int \| None` | Año de lanzamiento |
| `genre` | `str` | Género musical |
| `file_path` | `str \| None` | Ruta absoluta al archivo |
| `format` | `AudioFormat` | Formato del archivo |
| `source` | `TrackSource` | LOCAL, CD, o RIPPED |
| `bitrate_kbps` | `int` | Bitrate en kbps |
| `musicbrainz_id` | `str \| None` | MBID de la grabación |
| `acoustid` | `str \| None` | Huella AcoustID |
| `play_count` | `int` | Veces reproducida |
| `rating` | `int` | Puntuación 0–5 |

**Enums relacionados:**
- `AudioFormat`: MP3, FLAC, OGG, AAC, WAV, WMA, OPUS, CD, UNKNOWN
- `TrackSource`: LOCAL, CD, RIPPED

---

### `Album` — Álbum Musical

Agrupa pistas bajo un lanzamiento.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno |
| `title` | `str` | Título del álbum |
| `artist_id` | `int \| None` | FK al Artist |
| `artist_name` | `str` | Nombre del artista (desnormalizado) |
| `year` | `int \| None` | Año de lanzamiento |
| `release_date` | `date \| None` | Fecha exacta |
| `genre` | `str` | Género principal |
| `label` | `str` | Sello discográfico |
| `musicbrainz_id` | `str \| None` | MBID del release |
| `cover_path` | `str \| None` | Ruta local a la portada |
| `total_tracks` | `int` | Total de pistas |
| `total_discs` | `int` | Total de discos |
| `release_type` | `str` | Tipo de lanzamiento (Album, Single, EP, etc.) — se completa con MusicBrainz |

---

### `Artist` — Artista o Banda

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno |
| `name` | `str` | Nombre del artista |
| `sort_name` | `str` | Nombre para ordenar (ej. "Beatles, The") |
| `musicbrainz_id` | `str \| None` | MBID del artista |
| `genres` | `list[str]` | Géneros asociados |
| `country` | `str` | País de origen — se completa con MusicBrainz |

---

### `Label` — Sello Discográfico

Entidad persistida (tabla `labels` en SQLite). Representa un sello discográfico con su país de origen.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno |
| `name` | `str` | Nombre del sello |
| `country` | `str` | País de origen — se completa con MusicBrainz |

Repositorio: `LabelRepository` (`infrastructure/database/repositories/label_repository.py`).
Métodos clave: `upsert_country(name, country)`, `get_country_map() → dict[str, str]`.

---

### `Playlist` — Lista de Reproducción

Contenedor de referencias a pistas, ordenadas por posición.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno |
| `name` | `str` | Nombre de la playlist |
| `entries` | `list[PlaylistEntry]` | Entradas ordenadas |
| `is_smart` | `bool` | Si se genera automáticamente |
| `smart_query` | `dict` | Criterios de la smart playlist |

**`PlaylistEntry`:**
| Atributo | Tipo | Descripción |
|---|---|---|
| `track_id` | `int` | ID de la pista referenciada |
| `position` | `int` | Posición en la playlist (base 1) |
| `added_at` | `datetime` | Fecha de agregado |

---

### `CDDisc` — Disco Compacto Físico

Representa un CD en la unidad lectora, antes o después de ser identificado.

| Atributo | Tipo | Descripción |
|---|---|---|
| `disc_id` | `str` | Disc ID calculado (formato MusicBrainz) |
| `drive_path` | `str` | Ruta de la unidad (ej. "D:") |
| `tracks` | `list[CDTrack]` | Pistas del disco |
| `musicbrainz_id` | `str \| None` | MBID del release identificado |
| `album_title` | `str` | Título (vacío hasta identificación) |
| `identified` | `bool` | True si fue reconocido online |
| `release_type` | `str` | Tipo de lanzamiento (Album, Single, EP, etc.) — poblado por MusicBrainz |
| `artist_country` | `str` | País de origen del artista — poblado por MusicBrainz |
| `label_country` | `str` | País de origen del sello — poblado por MusicBrainz |

**`CDTrack`:**
| Atributo | Tipo | Descripción |
|---|---|---|
| `number` | `int` | Número de pista (base 1) |
| `duration_ms` | `int` | Duración |
| `offset` | `int` | Offset en sectores (para Disc ID) |
| `rip_status` | `RipStatus` | PENDING, RIPPING, DONE, ERROR, SKIPPED |
| `ripped_path` | `str \| None` | Archivo resultante del ripeo |

---

### `RadioStation` — Emisora de Radio por Internet

Representa una emisora de radio en streaming. Puede provenir de una búsqueda en
radio-browser.info o ser creada manualmente por el usuario.

| Atributo | Tipo | Descripción |
|---|---|---|
| `id` | `int \| None` | ID interno (None si no persistida) |
| `name` | `str` | Nombre de la emisora |
| `stream_url` | `str` | URL del stream (HTTP/HTTPS, M3U, PLS, etc.) |
| `country` | `str` | País de origen (código ISO o nombre) |
| `genre` | `str` | Género o categoría principal |
| `logo_url` | `str` | URL del logo/ícono de la emisora |
| `is_favorite` | `bool` | True si el usuario la marcó como favorita |
| `added_at` | `datetime` | Fecha y hora en que fue guardada |
| `bitrate_kbps` | `int` | Bitrate en kbps (0 si desconocido) |
| `radio_browser_id` | `str` | UUID en radio-browser.info (vacío si es manual) |

---

### `EqPreset` — Preset del Ecualizador

Representa la configuración de un preset del ecualizador gráfico de 10 bandas.

| Atributo | Tipo | Descripción |
|---|---|---|
| `name` | `str` | Nombre del preset (ej. "Rock", "Mi preset") |
| `preamp` | `float` | Amplificación general en dB (-20.0 a +20.0) |
| `bands` | `list[float]` | Lista de 10 valores en dB, una por banda (60Hz a 16kHz) |
| `is_builtin` | `bool` | True si proviene de los presets predefinidos de VLC |

Los presets con `is_builtin=True` se cargan desde la API nativa de libVLC (`libvlc_audio_equalizer_new_from_preset`) y **no se persisten en la base de datos**. Los presets de usuario (`is_builtin=False`) se almacenan en la tabla `eq_presets` de SQLite.

---

## Relaciones entre Entidades

```
Artist (1) ──────── (*) Album (1) ──────── (*) Track
                                 \
                                  └── (*) Playlist ──── (*) Track (via PlaylistEntry)

CDDisc (1) ──────── (*) CDTrack
    │
    └── se convierte en → Album + Track(source=RIPPED) después del ripeo
```

---

## Decisiones de Diseño

- **Desnormalización controlada**: `Track` y `Album` almacenan `artist_name` además
  del `artist_id`. Esto evita JOINs en la UI para mostrar listas y simplifica el
  modelo Qt. La fuente de verdad sigue siendo el `Artist`.

- **`CDDisc` es efímero**: No se persiste en la base de datos. Solo existe en memoria
  mientras el CD está insertado. Tras el ripeo, se generan entidades `Track` normales.

- **Sin ORM**: Los modelos son `@dataclass` puras. El mapeo a/desde SQLite es
  responsabilidad exclusiva de los Repositories en `infrastructure/database/`.
