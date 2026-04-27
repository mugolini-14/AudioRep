# Funciones pendientes — AudioRep

Este archivo registra funcionalidades consideradas pero no implementadas aún, con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

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
