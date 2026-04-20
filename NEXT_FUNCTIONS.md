# Funciones pendientes — AudioRep

Este archivo registra funcionalidades que fueron consideradas pero que no pudieron implementarse al momento, junto con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

## Refactorización de performance del reproductor

~~Identificada en v0.50. Se implementaron los problemas 2, 3 y 4. Quedan pendientes:~~

✅ **Resuelto en v0.51** — Todos los problemas de performance del reproductor han sido implementados:
- Problemas 2, 3 y 4: resueltos en v0.50.
- Problema 1 (hilo RMS dedicado): resuelto en v0.51.
- Problema 5 (backpressure con log de underruns): resuelto en v0.51.

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
Los cambios en el spec no afectan el código fuente, pero sí requieren un rebuild y validación de que ningún módulo excluido sea necesario en runtime. Se decidió dejarlo para una versión posterior para no demorar el release de la 0.40.

---

## Ecualizador gráfico con presets

**Descripción:**
Un ecualizador gráfico de 10 bandas integrado en la interfaz de AudioRep. El usuario podría:
- Ver y ajustar cada banda de frecuencia mediante sliders verticales
- Seleccionar presets predeterminados (Rock, Pop, Jazz, Clásica, etc.)
- Crear, nombrar y guardar sus propios presets
- Recordar el preset activo entre sesiones

---

### Enfoque técnico recomendado: ecualizador nativo de VLC

**No hace falta ninguna librería adicional.** `python-vlc`, que AudioRep ya usa para toda la reproducción, expone directamente la API de ecualizador integrada en libVLC. Es el enfoque más sencillo, más robusto y con cero dependencias nuevas.

VLC tiene un ecualizador de **10 bandas** con **preamp** incluido, y viene con **18 presets predeterminados**.

---

### API de python-vlc para el ecualizador

```python
import vlc

# ── Crear un ecualizador vacío (flat) ────────────────────────────── #
eq = vlc.libvlc_audio_equalizer_new()

# ── Preamp (-20.0 a +20.0 dB) ────────────────────────────────────── #
vlc.libvlc_audio_equalizer_set_preamp(eq, 0.0)

# ── Ajustar banda por índice (0–9), amplitud en dB (-20.0 a +20.0) ─ #
vlc.libvlc_audio_equalizer_set_amp_at_index(eq, amplitude_db, band_index)

# ── Leer valor actual de una banda ───────────────────────────────── #
amp = vlc.libvlc_audio_equalizer_get_amp_at_index(eq, band_index)

# ── Leer frecuencia central de cada banda ────────────────────────── #
freq = vlc.libvlc_audio_equalizer_get_band_frequency(band_index)

# ── Aplicar al reproductor en tiempo real ────────────────────────── #
player.audio_set_equalizer(eq)   # player = instancia de vlc.MediaPlayer

# ── Desactivar el ecualizador ─────────────────────────────────────── #
player.audio_set_equalizer(None)

# ── Liberar el objeto ────────────────────────────────────────────── #
vlc.libvlc_audio_equalizer_release(eq)

# ── Presets predeterminados de VLC ───────────────────────────────── #
count = vlc.libvlc_audio_equalizer_get_preset_count()          # → 18
name  = vlc.libvlc_audio_equalizer_get_preset_name(index)     # → "Rock"
eq    = vlc.libvlc_audio_equalizer_new_from_preset(index)      # carga el preset
```

**El cambio es en tiempo real:** llamar a `audio_set_equalizer()` mientras una pista está reproduciéndose actualiza el sonido inmediatamente, sin interrumpir la reproducción.

---

### Las 10 bandas de VLC

| Índice | Frecuencia |
|--------|-----------|
| 0 | 60 Hz |
| 1 | 170 Hz |
| 2 | 310 Hz |
| 3 | 600 Hz |
| 4 | 1 kHz |
| 5 | 3 kHz |
| 6 | 6 kHz |
| 7 | 12 kHz |
| 8 | 14 kHz |
| 9 | 16 kHz |

Rango de cada banda: **-20.0 dB a +20.0 dB**

---

### Los 18 presets predeterminados de VLC

```
0  Flat             9  Live
1  Classical        10 Party
2  Club             11 Pop
3  Dance            12 Reggae
4  Fullbass         13 Rock
5  Fullbass&Treble  14 Ska
6  Full Treble      15 Soft
7  Headphones       16 Softrock
8  Large Hall       17 Techno
```

Estos ya están embebidos en libVLC — no hace falta definir los valores manualmente.

---

### Diseño de la UI

**Widget propuesto: `EqualizerWidget`** (un panel flotante o fijo, similar a cómo otros reproductores lo muestran).

```
┌────────────────────────────────────────────────────────────┐
│  Preset: [Rock ▼]                  [Guardar]  [Eliminar]   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Preamp  60Hz 170Hz 310Hz 600Hz  1kHz  3kHz  6kHz 12kHz 14kHz 16kHz │
│                                                            │
│  +20 ─  ─    ─    ─    ─    ─    ─    ─    ─    ─    ─   │
│        │    │    │    │    │    │    │    │    │    │      │
│  ±0 ── ●    ●    ●    ●    ●    ●    ●    ●    ●    ●    │  ← sliders verticales
│        │    │    │    │    │    │    │    │    │    │      │
│  -20 ─  ─    ─    ─    ─    ─    ─    ─    ─    ─    ─   │
│                                                            │
│  [Activar EQ]                              [Resetear]      │
└────────────────────────────────────────────────────────────┘
```

**Componentes del widget:**
- `QComboBox` de presets (predeterminados + usuario, separados con separador)
- 11 `QSlider` verticales: 1 preamp + 10 bandas. Rango: -200 a 200 (internamente en décimas de dB para precisión con enteros). Tick marks cada 5 dB.
- `QLabel` debajo de cada slider con la frecuencia (`60`, `170`, `310`…) y arriba con el valor actual en dB
- Botón `Activar EQ` (toggle, checkable) — desactiva pasando `None` al ecualizador
- Botón `Resetear` — pone todos los sliders en 0 dB
- Botones `Guardar` y `Eliminar` para presets de usuario

**Dónde mostrarlo:**
- Opción A: botón `EQ` en la `PlayerBar` que abre `EqualizerWidget` como ventana flotante (`QDialog` no modal)
- Opción B: panel colapsable debajo del `PlayerBar`

---

### Persistencia de presets de usuario

Los presets del usuario se guardan en **SQLite** (misma base de datos que usa AudioRep):

```sql
CREATE TABLE eq_presets (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    preamp    REAL NOT NULL DEFAULT 0.0,
    band_0    REAL NOT NULL DEFAULT 0.0,
    band_1    REAL NOT NULL DEFAULT 0.0,
    band_2    REAL NOT NULL DEFAULT 0.0,
    band_3    REAL NOT NULL DEFAULT 0.0,
    band_4    REAL NOT NULL DEFAULT 0.0,
    band_5    REAL NOT NULL DEFAULT 0.0,
    band_6    REAL NOT NULL DEFAULT 0.0,
    band_7    REAL NOT NULL DEFAULT 0.0,
    band_8    REAL NOT NULL DEFAULT 0.0,
    band_9    REAL NOT NULL DEFAULT 0.0,
    is_user   INTEGER NOT NULL DEFAULT 1   -- 0 = predeterminado, 1 = usuario
);
```

El preset activo y si el EQ está activado se guardan en `QSettings` (igual que el resto de preferencias):
```python
settings.eq_enabled     = True
settings.eq_preset_name = "Mi preset de Rock"
```

---

### Arquitectura propuesta

```
domain/
  (sin cambios — el EQ no es una entidad del dominio)

core/
  settings.py         — agregar: eq_enabled, eq_preset_name, eq_preamp, eq_bands[]

infrastructure/
  audio/
    vlc_player.py     — agregar: apply_equalizer(preset), disable_equalizer()
  database/
    repositories/
      eq_preset_repository.py  — NUEVO: CRUD de presets de usuario

services/
  equalizer_service.py  — NUEVO: carga presets (VLC + usuario), aplica, guarda

ui/
  widgets/
    equalizer_widget.py  — NUEVO: panel con sliders + combobox de presets
  controllers/
    equalizer_controller.py  — NUEVO: conecta widget ↔ equalizer_service
```

**`VLCPlayer` recibe métodos nuevos:**
```python
def apply_equalizer(self, preamp: float, bands: list[float]) -> None:
    """Aplica EQ con los valores dados. bands: lista de 10 floats en dB."""
    eq = vlc.libvlc_audio_equalizer_new()
    vlc.libvlc_audio_equalizer_set_preamp(eq, preamp)
    for i, amp in enumerate(bands):
        vlc.libvlc_audio_equalizer_set_amp_at_index(eq, amp, i)
    self._player.audio_set_equalizer(eq)
    vlc.libvlc_audio_equalizer_release(eq)

def disable_equalizer(self) -> None:
    self._player.audio_set_equalizer(None)
```

---

### Alternativa: DSP con `pedalboard` (Spotify, Apache 2.0)

Si en el futuro se quisiera un ecualizador más avanzado (paramétrico, bandas configurables, compresión, reverb, etc.), existe `pedalboard` de Spotify.

- **PyPI:** `pedalboard`
- **Licencia:** Apache 2.0
- **Repositorio:** [github.com/spotify/pedalboard](https://github.com/spotify/pedalboard)

```python
from pedalboard import Pedalboard, LowShelfFilter, HighShelfFilter, PeakFilter
import numpy as np

board = Pedalboard([
    LowShelfFilter(cutoff_frequency_hz=60, gain_db=4.0),
    PeakFilter(cutoff_frequency_hz=1000, gain_db=-2.0, q=0.7),
    HighShelfFilter(cutoff_frequency_hz=10000, gain_db=3.0),
])

# Aplicar sobre buffer PCM (numpy array)
output_audio = board(input_audio, sample_rate=44100)
```

**Por qué no es el enfoque principal para AudioRep:**
- Requiere interceptar el stream PCM antes de que llegue a la salida de audio — lo cual implicaría rediseñar el pipeline de audio alrededor de `sounddevice` en lugar de VLC.
- Más complejo de integrar; VLC ya tiene su propio mezclador interno.
- El ecualizador de 10 bandas de VLC cubre el 99% de los casos de uso de un reproductor doméstico.

`pedalboard` sería valioso si en el futuro se quisiera agregar efectos de estudio (compresor, reverb, chorus, delay).

---

### Resumen

| Aspecto | Decisión |
|---|---|
| Motor del EQ | API nativa de VLC (`libvlc_audio_equalizer_*`) |
| Dependencias nuevas | **Ninguna** |
| Número de bandas | 10 (60Hz a 16kHz) + preamp |
| Presets predeterminados | 18 (ya incluidos en VLC) |
| Presets de usuario | Tabla `eq_presets` en SQLite |
| Persistencia del estado | `QSettings` (eq_enabled, preset activo) |
| UI | `EqualizerWidget` con 11 sliders verticales + combobox |
| Cambio en tiempo real | Sí — `audio_set_equalizer()` no interrumpe reproducción |

---

## Exportación de la biblioteca de pistas

**Descripción:**
Permitir al usuario exportar el contenido de su biblioteca de pistas a un archivo de hoja de cálculo o PDF. El archivo resultante incluiría todas las columnas visibles en la tabla: #, Título, Artista, Álbum, Año, Género, Duración y Formato. El export podría aplicarse a toda la biblioteca o solo a la selección / filtro activo.

**Por qué no se implementó antes:**
No hay urgencia técnica; es una funcionalidad de valor añadido que requiere elegir el formato(s) a soportar y la librería adecuada, decisión que se documenta aquí para el momento en que se implemente.

---

### Formatos y librerías disponibles

#### 1. CSV — `csv` (librería nativa de Python)

**Sin dependencias externas.** El módulo `csv` de la stdlib de Python es suficiente para exportar a CSV.

```python
import csv

def export_to_csv(tracks: list[Track], filepath: str) -> None:
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        # utf-8-sig agrega BOM para compatibilidad con Excel en Windows
        writer = csv.DictWriter(f, fieldnames=[
            '#', 'Título', 'Artista', 'Álbum', 'Año',
            'Género', 'Duración', 'Formato'
        ])
        writer.writeheader()
        for i, t in enumerate(tracks, 1):
            writer.writerow({
                '#':        i,
                'Título':   t.title or '',
                'Artista':  t.artist_name or '',
                'Álbum':    t.album_title or '',
                'Año':      t.year or '',
                'Género':   t.genre or '',
                'Duración': _ms_to_str(t.duration_ms),
                'Formato':  t.format.value if t.format else '',
            })
```

**Ventajas:** sin dependencias, compatible con Excel, LibreOffice, Google Sheets.
**Desventajas:** sin estilos, sin anchos de columna, sin colores.

---

#### 2. XLSX — `openpyxl` (librería externa, MIT license)

`openpyxl` es la librería estándar de facto para escribir archivos `.xlsx` en Python. Pure Python, activamente mantenida, sin dependencias de Excel.

- **PyPI:** `openpyxl`
- **Licencia:** MIT
- **Repositorio:** [github.com/theorchard/openpyxl](https://foss.heptapod.net/openpyxl/openpyxl)

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

def export_to_xlsx(tracks: list[Track], filepath: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Biblioteca"

    # Cabeceras con estilo
    headers = ['#', 'Título', 'Artista', 'Álbum', 'Año', 'Género', 'Duración', 'Formato']
    header_fill = PatternFill("solid", fgColor="1e1e2e")
    header_font = Font(bold=True, color="e2e2f0")

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Datos
    for row, t in enumerate(tracks, 2):
        ws.cell(row=row, column=1, value=row - 1)
        ws.cell(row=row, column=2, value=t.title or '')
        ws.cell(row=row, column=3, value=t.artist_name or '')
        ws.cell(row=row, column=4, value=t.album_title or '')
        ws.cell(row=row, column=5, value=t.year or '')
        ws.cell(row=row, column=6, value=t.genre or '')
        ws.cell(row=row, column=7, value=_ms_to_str(t.duration_ms))
        ws.cell(row=row, column=8, value=t.format.value if t.format else '')

    # Anchos automáticos
    col_widths = [5, 35, 25, 30, 6, 18, 10, 8]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width

    wb.save(filepath)
```

**Ventajas:** formato nativo de Excel y LibreOffice, soporta estilos completos (fuentes, colores, anchos, freeze de cabecera), fácil de usar.
**Desventajas:** dependencia externa (~500KB instalada).

---

#### 3. ODS — `odfpy` (librería externa, Apache/LGPL license)

`.ods` es el formato nativo de LibreOffice Calc. `odfpy` es la librería Python más completa para crearlo.

- **PyPI:** `odfpy`
- **Licencia:** Apache 2.0 / LGPL
- **Repositorio:** [github.com/eea/odfpy](https://github.com/eea/odfpy)

```python
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P

def export_to_ods(tracks: list[Track], filepath: str) -> None:
    doc = OpenDocumentSpreadsheet()
    table = Table(name="Biblioteca")

    headers = ['#', 'Título', 'Artista', 'Álbum', 'Año', 'Género', 'Duración', 'Formato']
    header_row = TableRow()
    for h in headers:
        cell = TableCell()
        cell.addElement(P(text=h))
        header_row.addElement(cell)
    table.addElement(header_row)

    for i, t in enumerate(tracks, 1):
        row = TableRow()
        for value in [i, t.title, t.artist_name, t.album_title,
                      t.year, t.genre, _ms_to_str(t.duration_ms),
                      t.format.value if t.format else '']:
            cell = TableCell()
            cell.addElement(P(text=str(value or '')))
            row.addElement(cell)
        table.addElement(row)

    doc.spreadsheet.addElement(table)
    doc.save(filepath)
```

**Ventajas:** formato nativo de LibreOffice, sin dependencia de Microsoft.
**Desventajas:** API verbosa, menos usado que XLSX, menor comunidad.

---

#### 4. PDF — `fpdf2` (librería externa, LGPL license)

`fpdf2` es un fork moderno y activo de PyFPDF, orientado a generación simple de PDFs. Pure Python.

- **PyPI:** `fpdf2`
- **Licencia:** LGPL v3
- **Repositorio:** [github.com/py-pdf/fpdf2](https://github.com/py-pdf/fpdf2)

```python
from fpdf import FPDF

def export_to_pdf(tracks: list[Track], filepath: str) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "AudioRep — Biblioteca de pistas", ln=True)
    pdf.set_font("Helvetica", size=8)

    # Cabeceras
    col_widths = [8, 55, 35, 40, 12, 22, 15, 12]
    headers    = ['#', 'Título', 'Artista', 'Álbum', 'Año', 'Género', 'Dur.', 'Fmt']

    pdf.set_fill_color(30, 30, 46)
    pdf.set_text_color(226, 226, 240)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 6, h, border=1, fill=True)
    pdf.ln()

    # Filas alternadas
    pdf.set_text_color(0, 0, 0)
    for i, t in enumerate(tracks, 1):
        fill = i % 2 == 0
        if fill:
            pdf.set_fill_color(240, 240, 250)
        row = [str(i), t.title or '', t.artist_name or '', t.album_title or '',
               str(t.year or ''), t.genre or '', _ms_to_str(t.duration_ms),
               t.format.value if t.format else '']
        for w, val in zip(col_widths, row):
            pdf.cell(w, 5, val[:30], border='B', fill=fill)
        pdf.ln()

    pdf.output(filepath)
```

**Ventajas:** pure Python, sin dependencias externas pesadas, salida portable y lista para imprimir.
**Desventajas:** PDF no es editable, caracteres Unicode avanzados requieren fuentes embebidas.

> **Nota sobre Unicode en PDF:** si los títulos/artistas tienen caracteres especiales (tildes, kanji, etc.), hay que registrar una fuente TTF:
> ```python
> pdf.add_font("DejaVu", fname="DejaVuSans.ttf", uni=True)
> pdf.set_font("DejaVu", size=8)
> ```

---

#### 5. Opción unificada — `tablib` (librería externa, MIT license)

`tablib` es una librería que provee una única API para exportar a CSV, XLSX, ODS, JSON, YAML y más. Abstrae las librerías anteriores.

- **PyPI:** `tablib`
- **Licencia:** MIT
- **Repositorio:** [github.com/jazzband/tablib](https://github.com/jazzband/tablib)

```python
import tablib

def build_dataset(tracks: list[Track]) -> tablib.Dataset:
    ds = tablib.Dataset(
        headers=['#', 'Título', 'Artista', 'Álbum', 'Año', 'Género', 'Duración', 'Formato']
    )
    for i, t in enumerate(tracks, 1):
        ds.append([i, t.title, t.artist_name, t.album_title,
                   t.year, t.genre, _ms_to_str(t.duration_ms),
                   t.format.value if t.format else ''])
    return ds

# Exportar a cualquier formato
dataset = build_dataset(tracks)
with open('biblioteca.csv',  'w') as f: f.write(dataset.csv)
with open('biblioteca.xlsx', 'wb') as f: f.write(dataset.xlsx)
with open('biblioteca.ods',  'wb') as f: f.write(dataset.ods)
```

**Ventajas:** una sola dependencia, API muy limpia, fácil de mantener.
**Desventajas:** no soporta estilos (color de cabeceras, anchos de columna) — para eso hay que usar openpyxl directamente.

---

### Tabla comparativa

| Formato | Librería | Tipo | Estilos | Peso | Recomendación |
|---|---|---|---|---|---|
| CSV | `csv` (stdlib) | Nativa | No | 0 | ✓ Siempre incluir |
| XLSX | `openpyxl` | Externa (MIT) | Completos | ~500 KB | ✓ Formato principal |
| ODS | `odfpy` | Externa (LGPL) | Básicos | ~200 KB | Opcional |
| PDF | `fpdf2` | Externa (LGPL) | Básicos | ~600 KB | ✓ Para imprimir |
| Multi | `tablib` | Externa (MIT) | No | variable | Si se priorizan varios formatos sin estilos |

---

### Arquitectura propuesta en AudioRep

**Lugar en la arquitectura:**
- La lógica de exportación va en un `ExportService` nuevo en `services/`.
- El service recibe una `list[Track]` y el formato elegido; devuelve el filepath.
- La UI dispara el export desde el `LibraryPanel` con un botón "Exportar" y un `QFileDialog`.

**Flujo:**
```
LibraryPanel → botón "Exportar"
    ↓
QFileDialog.getSaveFileName(filter="CSV (*.csv);;Excel (*.xlsx);;PDF (*.pdf)")
    ↓
ExportService.export(tracks, filepath, format)
    ↓
Writer apropiado (csv / openpyxl / fpdf2)
    ↓
Archivo en disco → notificación al usuario
```

**El export se puede aplicar a:**
- Toda la biblioteca (todos los tracks del modelo)
- Solo el álbum / artista seleccionado en el árbol izquierdo
- La búsqueda activa (filtro de texto)

---

### Dependencias a agregar (según formatos elegidos)

```toml
# pyproject.toml — agregar según los formatos que se implementen
openpyxl>=3.1.0    # XLSX
fpdf2>=2.8.0       # PDF
odfpy>=1.4.0       # ODS (opcional)
```

CSV no requiere dependencia (stdlib).

---

## Integración de YouTube Music

**Descripción:**
Permitir buscar, explorar y reproducir canciones de YouTube Music directamente desde AudioRep, sin necesidad de abrir el navegador. Incluiría búsqueda de canciones, álbumes y artistas, acceso a la biblioteca personal del usuario (canciones guardadas, playlists), radio automática basada en canción y visualización de letras.

**Por qué no se implementó antes:**
YouTube Music no tiene API oficial. La integración requiere librerías de terceros con distintos niveles de estabilidad, y hay consideraciones de autenticación y durabilidad que hay que evaluar y diseñar con cuidado antes de comenzar.

---

### Stack técnico

La integración usa dos librerías open source encadenadas:

| Librería | Rol | Versión |
|---|---|---|
| `ytmusicapi` | Búsqueda y metadatos (artista, álbum, portada, letras, biblioteca, radio) | ≥ 1.11.5 |
| `yt-dlp` | Extracción de URL de audio reproducible vía Python API | última |

**Flujo de reproducción:**
```
Usuario busca "Adele Hello"
    ↓
ytmusicapi.search() → [{ title, artists, videoId, thumbnails, ... }]
    ↓
yt-dlp.extract_info(videoId, download=False)
    → formats[] → URL HTTP con audio Opus/AAC (expira en ~6h)
    ↓
VLCPlayer.play_url(streaming_url)  ← sin cambios en VLCPlayer
    ↓
Audio + VU meter en tiempo real (igual que radio por internet)
```

VLC ya soporta reproducción de URLs HTTP — el mismo mecanismo que se usa para radio.

---

### Autenticación

`ytmusicapi` soporta tres modos:

| Modo | Ventajas | Desventajas |
|---|---|---|
| **Browser auth** (recomendado) | Simple, estable ~2 años, sin cuenta de Google Cloud | Requiere copiar headers del navegador una vez |
| OAuth | "Oficial" dentro del ecosistema privado | Tiene bug activo (HTTP 400 Bad Request) desde nov. 2024 |
| Sin autenticación | Sin setup | Solo búsqueda pública, sin biblioteca personal |

**Estrategia de fallback:** intentar OAuth → si falla, browser.json → si falla, modo público.

**Setup de browser auth:**
```python
YTMusic.setup(filepath='browser.json')  # Guiado en consola, una sola vez
yt = YTMusic('browser.json')
```

---

### Features disponibles

| Feature | Disponible | Notas |
|---|---|---|
| Búsqueda de canciones / álbumes / artistas | ✓ | Con filtros |
| Sugerencias de búsqueda | ✓ | Autocompletado |
| Biblioteca personal (canciones guardadas) | ✓ | Requiere auth |
| Playlists del usuario | ✓ | Requiere auth |
| Radio automática (mix basada en canción) | ✓ | `get_watch_playlist()` |
| Portadas / artwork | ✓ | URLs en campo `thumbnails[]` |
| Letras | ✓ | Con y sin timestamps |
| Historial | ✓ | Requiere auth |
| Calidad de audio | AAC 128kbps (gratis) / 256kbps (Premium) | Depende de cuenta |

---

### Arquitectura propuesta (Clean Architecture)

**Cambios en `domain/track.py`:**
```python
class TrackSource(str, Enum):
    LOCAL         = "LOCAL"
    CD            = "CD"
    RIPPED        = "RIPPED"
    YOUTUBE_MUSIC = "YOUTUBE_MUSIC"   # NUEVO

@dataclass
class Track:
    # ... campos existentes ...
    streaming_url: str | None = None  # NUEVO — URL HTTP temporal
    youtube_id:    str | None = None  # NUEVO — video ID de YT
```

**Nueva infraestructura (`infrastructure/api/`):**
- `youtube_music_client.py` — wrapper de `ytmusicapi` (implementa `IYouTubeMusicProvider`)
- `youtube_extractor.py` — wrapper de `yt-dlp` (implementa `IAudioURLExtractor`)

**Nuevas interfaces (`core/interfaces.py`):**
```python
class IYouTubeMusicProvider(Protocol):
    def search_songs(self, query: str, limit: int = 50) -> list[dict]: ...
    def get_watch_playlist(self, video_id: str) -> list[dict]: ...
    def get_library_songs(self) -> list[dict]: ...
    def get_lyrics(self, browse_id: str) -> dict: ...

class IAudioURLExtractor(Protocol):
    def extract_audio_url(self, video_id: str) -> str | None: ...
```

**Nuevo service (`services/youtube_music_service.py`):**
- `YouTubeMusicService(QObject)` con worker interno `_SearchWorker(QThread)`
- Emite señales: `results_ready(list[Track])`, `error(str)`

**UI:**
- Nuevo tab o subtab `YouTube Music` dentro del panel principal
- Barra de búsqueda + tabla de resultados (igual al RadioPanel)
- Sin cambios en `PlayerBar`, `NowPlaying`, ni `PlayerService`

**Sin cambios en `VLCPlayer`:** ya soporta `media_new(url)` para URLs HTTP.

---

### Cache de URLs

Las URLs de audio expiran en ~6 horas. Se necesita un cache SQLite con TTL:

```python
class StreamingCache:
    def get(self, video_id: str) -> str | None:
        """Retorna URL cacheada si tiene menos de 5h."""
    def put(self, video_id: str, url: str) -> None:
        """Guarda URL con timestamp actual."""
```

---

### Problemas conocidos y mitigaciones

| Problema | Causa | Mitigación |
|---|---|---|
| OAuth retorna HTTP 400 | Bug activo en ytmusicapi (nov. 2024–) | Usar browser auth como fallback |
| URLs de audio expiran en ~6h | YouTube las firma con TTL | Cache SQLite con invalidación automática |
| yt-dlp se rompe cuando YouTube cambia el cipher | Rotación frecuente de scripts en YouTube | Mantener yt-dlp actualizado; la comunidad lo parchea rápido |
| ytmusicapi se rompe con cambios en API privada | Endpoints no documentados | Suscribirse a releases; tener fallback a modo público |

---

### Consideraciones legales

- `ytmusicapi` es **no oficial** — emula requests del navegador, no usa API oficial de Google.
- YouTube Music puede bloquear cuentas si detecta uso automatizado masivo.
- Proyectos similares existentes (gytmdl, Melody-CLI, YouTubeMusicDesktop) prueban que hay cierta tolerancia para uso personal.
- **Recomendación:** documentar claramente que es integración no oficial, limitar a uso personal, y diseñar el feature para poder desactivarlo fácilmente si Google lo bloquea.

---

### Dependencias a agregar

```toml
# pyproject.toml
ytmusicapi>=1.11.5
yt-dlp>=2024.12.16
```

No requiere FFmpeg adicional (yt-dlp lo maneja internamente; VLC ya tiene codecs).

---

### Roadmap sugerido

**Fase 1 — MVP:** búsqueda de canciones + reproducción directa
**Fase 2 — Biblioteca:** canciones guardadas, playlists personales, radio automática
**Fase 3 — Polish:** letras sincronizadas, artwork en NowPlaying, historial, cache de URLs

---

### Referencias

- [ytmusicapi docs](https://ytmusicapi.readthedocs.io/)
- [ytmusicapi GitHub](https://github.com/sigma67/ytmusicapi)
- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [gytmdl — referencia de implementación](https://github.com/glomatico/gytmdl)
- [Issue OAuth 400 Bad Request (ytmusicapi #676)](https://github.com/sigma67/ytmusicapi/issues/676)

---

## Radio FM real (sintonización de señal en vivo)

**Descripción:**
Permitir que AudioRep sintonice emisoras de FM del aire en tiempo real, usando el rango de frecuencias estándar (88.0–108.0 MHz), sin depender de streams de internet.

**Por qué no se implementó:**
Requiere hardware específico no disponible al momento del desarrollo. Una PC estándar no puede recibir señales FM por sí sola.

**Requisitos para implementarla:**

- **Hardware investigado:** dongle RTL-SDR con chipset **RTL2832U + R820T2** (sintonizador). Rango real: ~24 MHz a 1766 MHz. El aparato disponible en MercadoLibre Argentina ("receptor SDR 30 MHz a 1.7 GHz 820T2") es exactamente este combo. Es el SDR con mejor soporte en Python/Windows que existe.
- **Driver (Windows):** instalar **Zadig** → seleccionar el dispositivo RTL2832U → aplicar driver `WinUSB` o `libusb-win32`. Gratuito, bien mantenido.
- **Driver (Linux):** `sudo apt install rtl-sdr` (incluye `librtlsdr` y `rtl_fm`).
- **Librería Python:** `pyrtlsdr` (wrapper de `librtlsdr`, instalable con pip). En Windows requiere `librtlsdr.dll` y `libusb-1.0.dll` en el PATH o junto al ejecutable.

**Stack de implementación:**

```
pyrtlsdr  →  IQ samples raw  →  demodulación FM (numpy/scipy)  →  audio PCM  →  VLC / sounddevice
```

1. **`core/interfaces.py`** — agregar protocolo `IRadioTuner` con métodos `tune(freq_mhz)`, `scan()`, `stop()`.
2. **`services/rtlsdr_service.py`** — `RtlSdrService(QObject)` con un worker `_RtlSdrWorker(QThread)` que lee samples continuamente y emite audio demodulado.
3. **`ui/widgets/`** — extender el `RadioPanel` existente para distinguir entre modo "internet" y modo "FM real (SDR)".
4. **Detección en runtime** — detectar si hay un dispositivo RTL-SDR conectado al arrancar y habilitar el modo FM real solo si está disponible.
5. **RDS (bonus)** — decodificar RDS para mostrar el nombre de la emisora en el panel.

**Notas adicionales:**
- La demodulación FM por software sobre datos IQ es código conocido y bien documentado; hay ejemplos listos con `numpy`/`scipy`.
- Convendría tener una librería alternativa como `rtlsdr-scanner` para el scan automático de estaciones.
- La antena incluida con los dongles genéricos es suficiente para pruebas; para uso real conviene una antena VHF dedicada.
