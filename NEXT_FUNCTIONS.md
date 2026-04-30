# Funciones pendientes — AudioRep

Este archivo registra funcionalidades consideradas pero no implementadas aún, con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

## Streaming público — Jamendo

**Complejidad estimada: BAJA**

**Descripción:**
Integrar el catálogo de Jamendo como fuente de streaming de música libre. Jamendo ofrece más de 600.000 tracks de artistas independientes bajo licencias Creative Commons, reproducibles en streaming completo y legalmente desde aplicaciones de terceros.

**API:** REST en `https://api.jamendo.com/v3.0/`. Sin librería Python oficial; se usa `requests` directamente.

**Autenticación:** `client_id` (API key gratuita, registrada en el portal de desarrolladores de Jamendo) enviado como parámetro GET. Sin OAuth para consultas de solo lectura.

**Endpoints principales:**

| Endpoint | Descripción |
|---|---|
| `GET /tracks/` | Búsqueda por nombre, artista, género, tags. Retorna `stream_url` (MP3 directo) |
| `GET /albums/` | Búsqueda de álbumes. Retorna portada (`image` field) |
| `GET /artists/` | Búsqueda de artistas |
| `GET /playlists/` | Playlists públicas de Jamendo |

**Stream URL:** el campo `stream_url` de cada track devuelve una URL MP3 directa que `VLCPlayer.play_url()` puede reproducir sin cambios — el mismo mecanismo ya implementado para radio por internet.

**Casos de uso en AudioRep:**
- Tab "Descubrir" con búsqueda libre en el catálogo de Jamendo.
- Reproducir tracks completos y opcionalmente guardarlos como emisoras en RadioPanel.
- Fuente de portadas y metadatos para pistas de la biblioteca local si coinciden por artista/título.

**Rate limits:** no documentados oficialmente. En la práctica, uso moderado sin restricciones.

**Arquitectura:**

```
infrastructure/api/jamendo_client.py  ← NUEVO
    search_tracks(query, genre, limit) → list[JamendoTrack]
    search_albums(query, limit) → list[JamendoAlbum]

services/discovery_service.py  ← NUEVO (compartido con otras fuentes)
    search(query) → list[StreamableTrack]

ui/widgets/discovery_panel.py  ← NUEVO (tab "Descubrir")
```

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/api/jamendo_client.py` | NUEVO: wrapper REST de Jamendo |
| `services/discovery_service.py` | NUEVO: orquesta múltiples fuentes (Jamendo, Archive, etc.) |
| `ui/widgets/discovery_panel.py` | NUEVO: buscador + tabla de resultados + botón Reproducir |
| `ui/main_window.py` | Agregar tab "Descubrir" al `QTabWidget#mainTabs` |

**Dependencias nuevas:** ninguna (`requests` ya disponible).

---

## Streaming público — Internet Archive

**Complejidad estimada: BAJA**

**Descripción:**
Internet Archive (archive.org) aloja más de 200.000 grabaciones de audio accesibles en streaming público, incluyendo conciertos en vivo, música clásica de dominio público, jazz histórico y colecciones de netlabels Creative Commons. No requiere autenticación.

**Librería Python oficial:** `internetarchive` (mantenida por archive.org).

```bash
pip install internetarchive
```

**Búsqueda y streaming:**

```python
import internetarchive as ia

# Buscar items de audio
results = ia.search_items('mediatype:audio subject:"jazz"')

# Obtener archivos de un item
item = ia.get_item('GratefulDead_1977-05-08')
for f in item.files:
    if f['name'].endswith('.mp3'):
        stream_url = f"https://archive.org/download/{item.identifier}/{f['name']}"
        # → VLCPlayer.play_url(stream_url)
```

**URL de stream directa:** `https://archive.org/download/{ITEM_ID}/{FILENAME}` — URL HTTP pública, sin auth, reproducible directamente por VLC.

**Búsqueda avanzada:** `https://archive.org/advancedsearch.php` con parámetros Lucene query syntax:
- `mediatype:audio` — filtrar solo audio
- `subject:"blues"` — por género
- `creator:"Miles Davis"` — por artista

**Casos de uso en AudioRep:**
- Acceso a grabaciones históricas y conciertos en vivo.
- Complementa Jamendo (Archive tiene material más antiguo y clásico; Jamendo tiene indie contemporáneo).
- Integrable en el mismo `DiscoveryService` y `DiscoveryPanel` que Jamendo.

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/api/archive_client.py` | NUEVO: wrapper de `internetarchive` para búsqueda y resolución de URLs |
| `services/discovery_service.py` | Agregar Archive como fuente adicional |

**Dependencias nuevas:**
```toml
internetarchive>=5.1.0
```

---

## Streaming público — SoundCloud

**Complejidad estimada: MEDIA**

**Descripción:**
SoundCloud tiene el catálogo público más amplio de los tres servicios. Miles de pistas de artistas independientes, remixes y podcasts son accesibles en streaming completo si el uploader lo permite. La integración es más compleja que Jamendo por requerir OAuth 2.1.

**API:** REST en `https://api.soundcloud.com/`. Documentación oficial activa.

**Autenticación:**
- Registro en el portal de desarrolladores de SoundCloud → obtener `client_id` y `client_secret`.
- OAuth 2.1 con PKCE para operaciones que requieren identidad del usuario (biblioteca personal, likes).
- Client Credentials flow para búsqueda y streaming de tracks públicos (sin usuario).

**Endpoints principales:**

| Endpoint | Descripción |
|---|---|
| `GET /tracks?q=...` | Búsqueda de tracks públicos |
| `GET /tracks/{id}/stream` | URL de streaming HLS AAC 160kbps |
| `GET /users/{id}/tracks` | Tracks de un artista |
| `GET /playlists/{id}` | Playlists públicas |

**Formato de stream:**
SoundCloud migró de MP3 a **HLS AAC** en 2023. El endpoint `/stream` retorna una URL `.m3u8` que VLC ya sabe reproducir nativamente (`VLCPlayer.play_url()` sin cambios).

**Rate limits:** 50 tokens cada 12 horas por app; 30 tokens por hora por IP. Relativamente restrictivo — implementar caché de resultados de búsqueda.

**Limitación importante:** no todas las pistas son streamables — el campo `streamable: true/false` en la respuesta indica si el uploader permite reproducción externa. Filtrar en la búsqueda.

**Casos de uso en AudioRep:**
- Búsqueda y reproducción de música independiente y remixes.
- Complementa Jamendo (SoundCloud tiene géneros más urbanos y electrónicos).
- Seguir artistas y acceder a sus novedades (requiere OAuth con usuario).

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/api/soundcloud_client.py` | NUEVO: auth OAuth 2.1, search, resolve stream URL |
| `core/settings.py` | `soundcloud_client_id`, `soundcloud_client_secret` |
| `ui/dialogs/settings_dialog.py` | Campos de API key de SoundCloud |
| `services/discovery_service.py` | Agregar SoundCloud como fuente (con caché de resultados) |

**Dependencias nuevas:** ninguna (`requests` ya disponible; OAuth 2.1 se implementa manualmente o con `requests-oauthlib`).

---

## Free Music Archive (FMA)

**Estado: DESCARTADO — API fuera de servicio**

La API de FMA fue dada de baja definitivamente por carga de servidor. El sitio sigue en línea para descargas manuales pero no expone endpoints reproducibles en tiempo real. No es viable para integración en AudioRep.

**Alternativa:** el dataset completo de FMA está disponible en GitHub (`mdeff/fma`) como archivo estático descargable, pero no como API en streaming.

---

## Streaming de biblioteca personal — Protocolo Subsonic / OpenSubsonic

**Complejidad estimada: MEDIA**

**Descripción:**
El protocolo Subsonic / OpenSubsonic es el estándar abierto para servidores personales de música en streaming. Implementarlo en AudioRep permitiría conectarse a un servidor propio (Navidrome, Funkwhale, etc.) y reproducir la biblioteca personal en streaming remoto — útil para escuchar desde cualquier lugar sin subir nada a servicios de terceros.

**Servidores compatibles más usados:**

| Servidor | Tecnología | Casos de uso |
|---|---|---|
| **Navidrome** | Go, muy liviano | Servidor casero, Raspberry Pi, VPS. El más popular. |
| **Funkwhale** | Python/Django | Federado (ActivityPub), social features |
| **Jellyfin** | .NET | Media center completo (video + audio) |

**API:** REST en `http://{servidor}/rest/{endpoint}`. Soporte JSON nativo. Autenticación por token MD5 (password + salt aleatorio) o API key.

**Endpoints principales:**

| Endpoint | Descripción |
|---|---|
| `ping` | Verificar conexión y credenciales |
| `getArtists` | Árbol de artistas de la biblioteca remota |
| `search3` | Búsqueda full-text |
| `stream?id={songId}` | URL de streaming del archivo (con transcoding opcional) |
| `getCoverArt?id={albumId}` | Portada del álbum |
| `getSong?id={songId}` | Metadatos de una pista |

**Librería Python:** `py-opensonic` — wrapper moderno con soporte async.

```python
import libopensonic
conn = libopensonic.Connection('http://mi-navidrome.com', 'usuario', 'contraseña', appName='AudioRep')
results = conn.search3(query='Miles Davis')
stream_url = conn.stream(song_id)  # URL directa → VLCPlayer.play_url()
```

**Integración con AudioRep:**
A diferencia de Jamendo/Archive/SoundCloud (catálogos externos), Subsonic conecta con **la propia biblioteca del usuario**. El flujo natural sería:
1. El usuario configura la URL del servidor y credenciales en `SettingsDialog`.
2. AudioRep puede operar en modo **local** (biblioteca local, comportamiento actual) o modo **remoto** (biblioteca en servidor Subsonic).
3. En modo remoto, las URLs de stream van directamente a `VLCPlayer.play_url()`.

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/api/subsonic_client.py` | NUEVO: wrapper de `py-opensonic` |
| `core/settings.py` | `subsonic_server_url`, `subsonic_username`, `subsonic_password` |
| `ui/dialogs/settings_dialog.py` | Sección "Servidor remoto (Subsonic)" |
| `services/library_service.py` | Modo remoto: delegar `get_all_tracks()` al cliente Subsonic |

**Dependencias nuevas:**
```toml
py-opensonic>=5.0.0
```

## Optimización de arranque del ejecutable Windows

**Descripción:**
El bundle de PyInstaller tarda varios segundos en iniciarse en Windows. Hay mejoras concretas identificadas que reducirían el tiempo de arranque sin cambios en el código de la aplicación.

**Cambios pendientes en `audiorep.spec`:**

- **Deshabilitar UPX** (`upx=False` en `EXE` y `COLLECT`) — es la mejora más significativa. UPX comprime cada `.pyd` individualmente; en un bundle de directorio, eso obliga a descomprimir cada módulo en cada arranque. El bundle quedará algo más grande en disco pero arrancará notablemente más rápido.
- **Ampliar la lista de `excludes`** — PyInstaller incluye módulos del stdlib que AudioRep no usa. Agregar:
  ```python
  "tkinter", "_tkinter",
  "pytest", "unittest", "doctest",
  "IPython", "jupyter", "notebook",
  "xml.etree.cElementTree", "lxml",
  "ftplib", "imaplib", "smtplib", "poplib", "xmlrpc", "http.server",
  "bz2", "lzma",
  "pydoc", "docutils",
  "setuptools", "pkg_resources", "distutils",
  "email", "multiprocessing",
  ```

**Recomendaciones para el usuario final (fuera del código):**
- Excluir la carpeta de instalación del antivirus (Windows Defender en particular escanea cada `.pyd` y `.dll` al cargarlos, añadiendo segundos al arranque).
- Instalar en SSD si es posible; con HDD el I/O de los ~180 archivos del `_internal/` domina el tiempo de arranque.

**Por qué no se implementó antes:**
Los cambios en el spec no afectan el código fuente, pero sí requieren un rebuild y validación de que ningún módulo excluido sea necesario en runtime.

---

## Crossfade entre pistas

**Descripción:**
Transición suave entre el final de una pista y el comienzo de la siguiente: la pista actual va bajando de volumen gradualmente mientras la siguiente sube, durante un período configurable por el usuario (por ejemplo, 0 a 12 segundos). Cuando está en 0 el comportamiento es el actual (sin crossfade).

### Por qué no existe un crossfade nativo en VLC

`libVLC` no expone una API de crossfade entre medias. El método `audio_set_volume()` sí existe y es accesible desde python-vlc, pero no hay un mecanismo automático de fundido cruzado entre dos instancias.

La solución es implementarlo a nivel de aplicación: usar **dos instancias de `vlc.MediaPlayer`** en simultáneo y manejar el fundido con un `QTimer`.

### Arquitectura propuesta

#### Dos instancias de MediaPlayer

```python
# En VLCPlayer.__init__():
self._player_a = self._instance.media_player_new()  # player principal (actual)
self._player_b = self._instance.media_player_new()  # player secundario (crossfade)
self._active   = 'a'   # cuál está reproduciendo ahora
```

Se alternan: la pista activa reproduce en `_player_a`; cuando hay crossfade, la siguiente pista arranca en `_player_b`. Al terminar el crossfade, `_player_b` pasa a ser el activo y viceversa.

#### Lógica del crossfade en `PlayerService`

```python
def _poll_position(self) -> None:
    remaining_ms = dur - pos
    cf_ms = self._crossfade_ms   # leído de AppSettings

    if cf_ms > 0 and not self._crossfading and remaining_ms <= cf_ms + 200:
        next_track = self._peek_next()
        if next_track:
            self._start_crossfade(next_track)
```

#### Curva de fundido

```python
# Curva logarítmica (más natural para el oído):
import math
vol_out = int(master_vol * math.cos(ratio * math.pi / 2))
vol_in  = int(master_vol * math.sin(ratio * math.pi / 2))
```

### Casos especiales a considerar

| Caso | Comportamiento esperado |
|---|---|
| Crossfade = 0 | Sin cambios — flujo actual |
| Pista siguiente no existe (última de la cola) | No iniciar crossfade, dejar terminar normalmente |
| El usuario hace skip antes de terminar el crossfade | Cancelar timer, detener ambos players, reproducir la pista elegida |
| Pista muy corta (< duración del crossfade) | Empezar el crossfade desde el inicio de la pista si ya arrancó dentro del período |
| Radio (stream continuo) | Crossfade no aplica — deshabilitar cuando `source == TrackSource.CD` o radio |

### Dependencias nuevas

**Ninguna.** `audio_set_volume()` ya existe en python-vlc. El fundido se implementa íntegramente con `QTimer` y dos instancias de `vlc.MediaPlayer`.

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `core/settings.py` | Agregar `crossfade_seconds` property |
| `infrastructure/audio/vlc_player.py` | Agregar segundo `MediaPlayer`, `start_crossfade()`, `_crossfade_tick()` |
| `services/player_service.py` | Detectar cuando iniciar el crossfade en `_poll_position()` |
| `ui/dialogs/settings_dialog.py` | Agregar control de crossfade (QSpinBox 0–12s) |

---

## Mini-reproductor (modo compacto)

**Descripción:**
Un botón pequeño en la interfaz que colapsa la ventana principal a un reproductor mínimo: solo muestra los controles de transporte, el nombre de la pista y el control de volumen. Útil para escuchar música mientras se trabaja en otra aplicación. La ventana se mantiene al frente de las demás.

### Diseño del mini-reproductor

```
┌──────────────────────────────────────────────────────────────┐
│ ⇄  ⏮  ⏹  ▶  ⏭  ↺   Don't Come Close — Ramones   🔊 ███░░ │  ← ~40px alto
└──────────────────────────────────────────────────────────────┘
```

- Ancho: ~520px fijo. Alto: ~52px (una sola fila, sin barra de progreso).
- Sin menú, sin pestañas, sin NowPlaying, sin VU meter, sin barra de estado.
- `Qt.WindowType.WindowStaysOnTopHint` para que quede por encima de otras ventanas.
- Arrastrable desde cualquier punto (sin barra de título).

### Estrategia de implementación (Opción A — recomendada)

No crear una segunda ventana. Al entrar en modo mini:
1. Guardar el tamaño y posición actual de la ventana.
2. Ocultar: `mainTabs`, `rightPanel`, barra de progreso, barra de estado.
3. `setFixedSize(520, 52)` y aplicar `WindowStaysOnTopHint`.
4. Al salir del modo mini: restaurar todo al estado guardado.

```python
def _enter_mini_mode(self) -> None:
    self._normal_geometry = self.saveGeometry()
    self._tabs.setVisible(False)
    self._right_panel.setVisible(False)
    self._status_bar.setVisible(False)
    self._player_bar.hide_progress_row()
    self.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.FramelessWindowHint
    )
    self.setFixedSize(520, 52)
    self.show()
```

### objectName y QSS propuestos

```css
QPushButton#miniPlayerBtn {
    background-color: transparent;
    color: #55557a;
    border: none;
    border-radius: 4px;
    font-size: 14px;
}
QPushButton#miniPlayerBtn:hover { background-color: rgba(255,255,255,0.10); color: #a0a0c0; }
QPushButton#miniPlayerBtn:checked { color: #7c5cbf; }
```

### Dependencias nuevas

**Ninguna.** Todo con PyQt6 nativo.

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `audiorep/ui/main_window.py` | `_setup_mini_toggle()`, `_enter_mini_mode()`, `_exit_mini_mode()` |
| `audiorep/ui/widgets/player_bar.py` | `hide_progress_row()`, `show_progress_row()`, botón `miniPlayerBtn` |
| `audiorep/ui/style/dark.qss` | Regla `QPushButton#miniPlayerBtn` |
| `core/settings.py` | `mini_player_active`, `mini_player_geometry` (persistencia) |

---

## Ecualizador gráfico con presets

**Descripción:**
Un ecualizador gráfico de 10 bandas integrado en la interfaz de AudioRep. El usuario puede ajustar cada banda de frecuencia mediante sliders verticales, seleccionar presets predeterminados (Rock, Pop, Jazz, Clásica, etc.) y crear/guardar sus propios presets.

### Enfoque técnico: ecualizador nativo de VLC

**No hace falta ninguna librería adicional.** `python-vlc` expone directamente la API de ecualizador integrada en libVLC. VLC tiene un ecualizador de **10 bandas** con **preamp** incluido y **18 presets predeterminados**.

```python
import vlc

eq = vlc.libvlc_audio_equalizer_new()
vlc.libvlc_audio_equalizer_set_preamp(eq, 0.0)
vlc.libvlc_audio_equalizer_set_amp_at_index(eq, amplitude_db, band_index)
player.audio_set_equalizer(eq)   # cambio en tiempo real, sin interrumpir reproducción
player.audio_set_equalizer(None) # desactivar

# Presets predeterminados
count = vlc.libvlc_audio_equalizer_get_preset_count()     # → 18
name  = vlc.libvlc_audio_equalizer_get_preset_name(index) # → "Rock"
eq    = vlc.libvlc_audio_equalizer_new_from_preset(index)
```

### Las 10 bandas de VLC

| Índice | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Frecuencia | 60Hz | 170Hz | 310Hz | 600Hz | 1kHz | 3kHz | 6kHz | 12kHz | 14kHz | 16kHz |

Rango de cada banda: **-20.0 dB a +20.0 dB**

### Los 18 presets predeterminados de VLC

```
0  Flat    1  Classical  2  Club      3  Dance   4  Fullbass   5  Fullbass&Treble
6  Full Treble  7  Headphones  8  Large Hall  9  Live  10 Party  11 Pop
12 Reggae  13 Rock  14 Ska  15 Soft  16 Softrock  17 Techno
```

### Diseño de la UI (`EqualizerWidget`)

```
┌────────────────────────────────────────────────────────────┐
│  Preset: [Rock ▼]                  [Guardar]  [Eliminar]   │
├────────────────────────────────────────────────────────────┤
│  Preamp  60Hz 170Hz 310Hz 600Hz  1kHz  3kHz  6kHz 12kHz 14kHz 16kHz │
│  [sliders verticales -20dB a +20dB]                        │
│  [Activar EQ]                              [Resetear]      │
└────────────────────────────────────────────────────────────┘
```

- Acceso: botón `EQ` en la `PlayerBar` abre `EqualizerWidget` como `QDialog` no modal.

### Persistencia de presets de usuario (SQLite)

```sql
CREATE TABLE eq_presets (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    preamp  REAL NOT NULL DEFAULT 0.0,
    band_0 REAL, band_1 REAL, band_2 REAL, band_3 REAL, band_4 REAL,
    band_5 REAL, band_6 REAL, band_7 REAL, band_8 REAL, band_9 REAL,
    is_user INTEGER NOT NULL DEFAULT 1
);
```

### Dependencias nuevas

**Ninguna.** API de ecualizador ya disponible en `python-vlc`.

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `core/settings.py` | `eq_enabled`, `eq_preset_name` |
| `infrastructure/audio/vlc_player.py` | `apply_equalizer(preamp, bands)`, `disable_equalizer()` |
| `infrastructure/database/repositories/eq_preset_repository.py` | NUEVO: CRUD de presets |
| `services/equalizer_service.py` | NUEVO: carga presets, aplica, guarda |
| `ui/widgets/equalizer_widget.py` | NUEVO: 11 sliders + combobox de presets |
| `ui/controllers/equalizer_controller.py` | NUEVO: conecta widget ↔ equalizer_service |

---

## Integración de YouTube Music

**Descripción:**
Buscar, explorar y reproducir canciones de YouTube Music directamente desde AudioRep, sin necesidad de abrir el navegador.

### Stack técnico

| Librería | Rol |
|---|---|
| `ytmusicapi` | Búsqueda y metadatos (artista, álbum, portada, letras, biblioteca, radio) |
| `yt-dlp` | Extracción de URL de audio reproducible vía Python API |

**Flujo:** `ytmusicapi.search()` → `yt-dlp.extract_info(videoId)` → URL HTTP → `VLCPlayer.play_url()` (sin cambios en VLC, mismo mecanismo que radio).

### Autenticación

| Modo | Ventajas | Desventajas |
|---|---|---|
| **Browser auth** (recomendado) | Simple, estable ~2 años | Requiere copiar headers del navegador una vez |
| OAuth | — | Bug activo HTTP 400 desde nov. 2024 |
| Sin autenticación | Sin setup | Solo búsqueda pública |

### Problemas conocidos

| Problema | Mitigación |
|---|---|
| URLs de audio expiran en ~6h | Cache SQLite con TTL |
| yt-dlp se rompe cuando YouTube cambia el cipher | Mantener yt-dlp actualizado |
| ytmusicapi se rompe con cambios en API privada | Suscribirse a releases; fallback a modo público |

### Consideraciones legales

`ytmusicapi` es no oficial — emula requests del navegador. Limitar a uso personal y diseñar el feature para poder desactivarlo fácilmente.

### Dependencias a agregar

```toml
ytmusicapi>=1.11.5
yt-dlp>=2024.12.16
```

### Roadmap sugerido

**Fase 1 — MVP:** búsqueda de canciones + reproducción directa
**Fase 2 — Biblioteca:** canciones guardadas, playlists personales, radio automática
**Fase 3 — Polish:** letras sincronizadas, artwork en NowPlaying, historial, cache de URLs

---

## Radio FM real (sintonización de señal en vivo)

**Descripción:**
Permitir que AudioRep sintonice emisoras de FM del aire en tiempo real (88.0–108.0 MHz), sin depender de streams de internet.

**Por qué no se implementó:**
Requiere hardware específico no disponible al momento del desarrollo. Una PC estándar no puede recibir señales FM por sí sola.

**Requisitos:**
- **Hardware:** dongle RTL-SDR con chipset **RTL2832U + R820T2**. Disponible en MercadoLibre Argentina (~USD 15).
- **Driver (Windows):** Zadig → aplicar driver `WinUSB` o `libusb-win32`.
- **Driver (Linux):** `sudo apt install rtl-sdr`.
- **Librería Python:** `pyrtlsdr` (wrapper de `librtlsdr`).

**Stack:**
```
pyrtlsdr → IQ samples raw → demodulación FM (numpy/scipy) → audio PCM → VLC / sounddevice
```

**Notas adicionales:**
- La demodulación FM por software sobre datos IQ es código conocido con ejemplos en `numpy`/`scipy`.
- RDS (bonus): decodificar para mostrar el nombre de la emisora en el panel.

---

## Exportación de radios guardadas

**Complejidad estimada: BAJA**

**Descripción:**
Exportar la lista de emisoras guardadas (y/o favoritas) a un archivo que pueda compartirse y abrirse directamente en cualquier reproductor. El formato principal es M3U/M3U8, estándar soportado por VLC, Winamp, foobar2000 y cualquier reproductor moderno. Al abrirlo, el receptor puede escuchar la emisora sin pasos adicionales.

**Estado actual del código:**
- `RadioStation.stream_url` ya existe en el dominio y en la DB — es la URL directa del stream.
- `ExportService` ya implementa XLSX/PDF/CSV para biblioteca y estadísticas; agregar radios es solo un método adicional.
- `RadioPanel` ya tiene la estructura de botones de acción; solo falta agregar uno de exportación.

**Formato M3U (el más valioso para compartir):**

```m3u
#EXTM3U
#EXTINF:-1,Radio Paradise (320 kbps) — Rock / United States
http://stream.radioparadise.com/flac
#EXTINF:-1,Jazz24 — Jazz / United States
https://live.amperwave.net/direct/ppm-jazz24aac-ibc1
```

El formato es texto plano, una línea `#EXTINF` seguida de la URL. Trivial de generar sin dependencias adicionales.

**Otros formatos opcionales:**
- **XSPF** (XML) — más estructurado, menos universal que M3U.
- **CSV/XLSX** — para el caso de uso de archivar o analizar la lista.

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `services/export_service.py` | Agregar `export_radio_m3u(stations, filepath)` y opcionalmente `export_radio_xlsx/csv` |
| `ui/widgets/radio_panel.py` | Agregar botón "Exportar radios" en la barra de acción de la pestaña Guardadas/Favoritas |
| `ui/controllers/radio_controller.py` | Conectar señal del botón con `ExportService` |

**Dependencias nuevas:** ninguna. M3U es texto plano.

---

## Integración de Spotify y Deezer

**Complejidad estimada: MEDIA (metadatos) / MUY ALTA o INVIABLE (streaming)**

**Descripción:**
Usar las APIs oficiales de Spotify y Deezer para búsqueda, exploración y metadatos (portadas, artistas, álbumes, géneros). El streaming completo enfrenta restricciones legales y técnicas severas en ambas plataformas.

### Spotify

**API oficial:** Web API REST. Biblioteca Python: `spotipy`.
**Capacidades disponibles legalmente:**
- Búsqueda de artistas, álbumes, pistas.
- Metadatos completos: portadas, géneros, popularidad, fechas, ISRC.
- Previews de 30 segundos (MP3 directo, sin auth adicional para muchas pistas).
- Biblioteca personal del usuario (requiere OAuth).

**Streaming completo:** **No disponible para aplicaciones de escritorio Python.** Los Terms of Service de Spotify prohíben explícitamente extraer el audio completo desde la API. El Spotify SDK oficial (para streaming nativo) está disponible solo para plataformas móviles y web, no existe versión Python de escritorio. No hay alternativa legal.

**Autenticación:** OAuth 2.0. `spotipy` lo maneja con PKCE. Requiere registrar la app en Spotify Developer Dashboard (gratuito).

### Deezer

**API oficial:** REST en `api.deezer.com`. Biblioteca Python: `deezer-python`.
**Capacidades disponibles legalmente:**
- Búsqueda, metadatos, portadas, charts.
- Preview de 30 segundos (URL directa en cada track object, campo `preview`).
- Sin auth para búsqueda pública.

**Streaming completo:** Requiere cuenta Deezer Premium y acuerdo de licencia comercial. La API oficial no expone las URLs de streaming completo. `deemix` (librería no oficial, similar a yt-dlp para Deezer) permite descarga en zona gris legal — diseñada para uso personal, pero viola los TOS.

### Roadmap recomendado

**Fase viable sin conflictos legales:**
1. **Enriquecimiento de metadatos**: usar Spotify/Deezer como fuentes adicionales en `EnrichmentService` — portadas en alta resolución, géneros, fechas de lanzamiento, ISRC.
2. **Previews**: reproducir los 30 segundos oficiales vía `VLCPlayer.play_url()` (mismo mecanismo que radio) desde un panel de búsqueda/descubrimiento.

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/api/spotify_client.py` | NUEVO: wrapper de `spotipy` para search + metadata |
| `infrastructure/api/deezer_client.py` | NUEVO: wrapper de `deezer-python` para search + metadata |
| `core/interfaces.py` | Extender `IMetadataProvider` o crear `IDiscoveryProvider` |
| `services/enrichment_service.py` | Agregar Spotify/Deezer como fuentes opcionales de enriquecimiento |

**Dependencias nuevas:**
```toml
spotipy>=2.24.0
deezer-python>=7.0.0
```

---

## Mejoras al editor de metadatos, portadas y nuevas fuentes

**Complejidad estimada: MEDIA**

**Descripción:**
El `TagEditorDialog` ya existe con edición de campos de texto. Tres mejoras independientes que completan el flujo de metadatos:

### A — Edición de portada en TagEditorDialog (BAJA)

**Estado actual:** `IFileTagger.write_embedded_cover()` ya existe. `TagEditorDialog` no tiene campo de portada.

**Cambios:** agregar en el diálogo un `QLabel` con la portada actual y un botón "Cambiar portada" que abra `QFileDialog` para seleccionar una imagen. La imagen se incrusta en el archivo con `write_embedded_cover()` y se actualiza `Album.cover_path` en la DB.

### B — Persistencia local de portadas (MEDIA)

**Estado actual:** `Album.cover_path` existe en el schema y en el repositorio, pero no hay un pipeline que lo pueble consistentemente. NowPlaying lee la portada desde el archivo embebido en cada reproducción (lento, lee el archivo completo).

**Propuesta:** Al importar o enriquecer una pista, guardar la portada extraída como `{DATA_DIR}/covers/{album_mbid_or_hash}.jpg` y almacenar la ruta en `Album.cover_path`. NowPlaying lee desde `cover_path` primero (caché local, más rápido) y solo recurre al archivo embebido como fallback.

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `infrastructure/filesystem/cover_cache.py` | NUEVO: `save_cover(data, key) → path`, `get_cover(key) → path | None` |
| `services/library_service.py` | Llamar a `cover_cache.save_cover()` al importar si el archivo tiene portada embebida |
| `services/enrichment_service.py` | Guardar portada descargada de Cover Art Archive en el caché |
| `ui/widgets/now_playing.py` | Leer `track.album.cover_path` como primera opción antes del archivo embebido |

### C — Renombrado de archivos desde la UI (BAJA)

**Estado actual:** `FileOrganizer.organize()` ya implementa el renombrado a `Artista/Álbum/NN - Título`. No está expuesto en la UI.

**Cambios:** agregar botón "Organizar archivos" en `LibraryPanel` (o en el `TagEditorDialog`) que llame a `FileOrganizer.organize()` sobre la selección y actualice `Track.file_path` en la DB.

### D — Nuevas fuentes de metadatos (BAJA-MEDIA cada una)

| Servicio | Librería | Fortaleza | Auth |
|---|---|---|---|
| **Discogs** | `discogs_client` | Cobertura de sellos, ediciones, portadas de alta resolución | Token gratuito |
| **TheAudioDB** | requests (REST directo) | Biografías, imágenes de artistas, álbumes | API key gratuita |
| **Fanart.tv** | requests (REST directo) | Artwork de alta calidad (logos, banners, disc art) | API key gratuita |
| **MusicBrainz** | ya integrado | Datos estructurados de releases | — |
| **Last.fm** | ya integrado | Géneros, scrobbling | — |

Integración propuesta: como fuentes adicionales opcionales en `EnrichmentService`, consultadas en cascada si MusicBrainz no tiene el dato.

**Dependencias nuevas:**
```toml
discogs-client>=2.3.0
```
TheAudioDB y Fanart.tv usan REST puro con `requests` (ya disponible).

---

## Panel de letras de canciones

**Complejidad estimada: MEDIA**

**Descripción:**
Un panel colapsable que muestra la letra de la pista en reproducción. Con letras sincronizadas (formato LRC), la línea actual se resalta automáticamente en tiempo real al avanzar la reproducción.

### APIs disponibles

| Servicio | Costo | Auth | Letras sincronizadas | Notas |
|---|---|---|---|---|
| **LRCLIB** (lrclib.net) | Gratuito | No requiere | Sí (formato LRC) | Open source, primera opción |
| **Genius** (`lyricsgenius`) | Gratuito | API key | No | Cobertura muy amplia, texto plano |
| **MusixMatch** | Limitado gratis | API key | Sí | Free tier: solo 30% de la letra |

**Recomendación:** LRCLIB como primera fuente (sin auth, sincronizado), Genius como fallback (sin sync, cobertura más amplia).

### Formato LRC (letras sincronizadas)

```lrc
[00:12.00] First verse line
[00:14.50] Second verse line
[00:17.00] Third line...
```

El timestamp se compara con `position_changed` (`pos_ms`) para resaltar la línea activa.

### API de LRCLIB

```
GET https://lrclib.net/api/get?artist_name=X&track_name=Y&album_name=Z&duration=N
```
Retorna JSON con `syncedLyrics` (string LRC) y `plainLyrics` (texto plano). Sin autenticación. Sin límite de rate publicado para uso personal.

### Diseño de UI

```
┌─────────────────────┐
│  NowPlaying         │  ← panel existente (stretch=1)
├─────────────────────┤
│  LyricsPanel        │  ← nuevo, colapsable (altura variable)
│  (scroll, resalta   │
│   línea activa)     │
├─────────────────────┤
│  VUMeter (110px)    │
└─────────────────────┘
```

Alternativa: botón en la `PlayerBar` que abre `LyricsPanel` como un `QDockWidget` o panel flotante.

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `infrastructure/api/lyrics_client.py` | NUEVO: `fetch(artist, title, album, duration_ms) → LyricsResult | None` (LRCLIB + Genius fallback) |
| `services/lyrics_service.py` | NUEVO: caché en memoria/disco, conecta con `app_events.track_changed` |
| `ui/widgets/lyrics_panel.py` | NUEVO: `QScrollArea` con líneas, resaltado activo; conecta con `app_events.position_changed` |
| `ui/main_window.py` | Integrar `LyricsPanel` en el `rightPanel` debajo de NowPlaying |
| `core/events.py` | Sin cambios — `track_changed` y `position_changed` ya existen |

**Dependencias nuevas:**
```toml
lyricsgenius>=3.0.1   # solo si se agrega Genius como fallback
```
LRCLIB no requiere ninguna librería adicional (usa `requests`, ya disponible).

---

## Sincronización a dispositivos portátiles

**Complejidad estimada: BAJA (USB drives) / MEDIA (reproductores MTP) / ALTA (iPod)**

**Descripción:**
Copiar canciones desde la biblioteca de AudioRep a un dispositivo externo: pen drives, reproductores MP3 genéricos, iPod clásico. Con opción de convertir el formato si el dispositivo no soporta el original (ej. FLAC → MP3).

### Tipos de dispositivos y protocolos

| Dispositivo | Protocolo | Complejidad | Librería Python |
|---|---|---|---|
| **Pen drive / disco USB** | MSC (mass storage) — aparece como unidad de disco | **BAJA** | `shutil` (stdlib) |
| **Reproductores MP3 genéricos** | MTP (Media Transfer Protocol) | **MEDIA** | `pymtp` (Linux) / `comtypes` + WPD (Windows) |
| **iPod clásico / nano (pre-2011)** | Protocolo Apple propietario (libgpod) | **ALTA** | `libgpod` (solo Linux, C binding) |
| **iPod moderno / iPhone** | AFC/USB (libimobiledevice) | **MUY ALTA** | `pymobiledevice3` |

### Funcionalidades propuestas

**Fase 1 — USB drives (MSC):** seleccionar pistas en la biblioteca → copiar a carpeta del dispositivo con `shutil.copy2()`. Detectar unidades disponibles con `psutil.disk_partitions()`. Sin dependencias adicionales.

**Fase 2 — Conversión de formato:** si el dispositivo no soporta el formato original (detectado por extensión o configurado por el usuario), transcodificar via VLC `sout` antes de copiar — el mismo mecanismo ya implementado en `CDRipper`.

**Fase 3 — MTP:** detectar dispositivos MTP y transferir via protocolo MTP. En Windows se accede al dispositivo via WPD (Windows Portable Devices) COM API usando `comtypes`. Más complejo pero cubre la mayoría de reproductores genéricos.

**Fase 4 — iPod clásico:** solo viable en Linux con `libgpod`. Requiere actualizar la base de datos interna del iPod (archivo `iTunesDB`), no solo copiar archivos.

### Detección de dispositivos

```python
import psutil
# Listar unidades removibles (MSC)
removable = [p for p in psutil.disk_partitions() if 'removable' in p.opts or p.fstype in ('vfat', 'exfat')]
```

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `services/sync_service.py` | NUEVO: detectar dispositivos, copiar/transcodificar pistas |
| `ui/widgets/sync_panel.py` | NUEVO: selector de dispositivo, lista de pistas a sincronizar, progreso |
| `ui/controllers/sync_controller.py` | NUEVO: conecta `SyncPanel` ↔ `SyncService` |
| `ui/main_window.py` | Agregar pestaña "Sync" o acceso desde menú |

**Dependencias nuevas:**
```toml
psutil>=5.9.0         # detección de unidades (ya puede estar instalado)
pymtp>=0.0.6          # solo si se implementa Fase 3 (MTP en Linux)
```
Fase 1 (USB) no requiere ninguna dependencia adicional más allá de stdlib.
