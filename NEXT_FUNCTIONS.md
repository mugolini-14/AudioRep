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

## Estadísticas ampliadas — ítems pendientes por falta de datos en el dominio

Identificados durante v0.66. Las siguientes secciones fueron solicitadas pero no pueden implementarse sin cambios previos en el dominio y la infraestructura:

### Tipo de álbum (Estudio / EP / Single / Compilación / Box Set)

**Dónde iría:** tab Álbumes → gráfico de barras.

**Por qué no está:** el campo `release_type` no existe en la entidad `Album`. MusicBrainz lo provee en el campo `release-group/primary-type` pero actualmente no se persiste en la base de datos.

**Lo que requiere:**
1. Agregar el campo `release_type: str` a `audiorep/domain/album.py`.
2. Persistirlo en `infrastructure/database/repositories/album_repository.py` (columna `release_type` en la tabla `albums`; migración de schema).
3. Almacenarlo al identificar metadatos en `infrastructure/api/musicbrainz_client.py`.

---

### Nacionalidad de artistas

**Dónde iría:** tab Artistas → gráfico de barras "Top 10 países de origen".

**Por qué no está:** la entidad `Artist` no tiene un campo de país/nacionalidad. MusicBrainz provee `area/name` para el artista, pero no se consulta ni persiste.

**Lo que requiere:**
1. Agregar `country: str` a `audiorep/domain/artist.py`.
2. Persistirlo en `infrastructure/database/repositories/artist_repository.py`.
3. Consultarlo y almacenarlo desde `infrastructure/api/musicbrainz_client.py` al identificar artistas.

---

### Nacionalidad de sellos discográficos

**Dónde iría:** tab Sellos → gráfico de barras "Top 10 países de origen de sellos".

**Por qué no está:** los sellos son solo un `str` en `Album.label`. No hay entidad `Label` en el dominio, ni repositorio, ni metadatos de país asociados.

**Lo que requiere:**
1. Crear entidad `Label` con `name: str` y `country: str`.
2. Crear `ILabelRepository` y su implementación SQLite.
3. Poblar la entidad desde MusicBrainz al identificar releases (campo `label-info/label/country`).

---

## Pantalla de estadísticas de la biblioteca

✅ **Implementado en v0.65** — Panel de estadísticas con gráficos interactivos (PyQt6-Charts): tortas de géneros y formatos, barras de décadas y ratings, top 10 artistas y pistas. Botón "Estadísticas" en la toolbar de la biblioteca alterna entre la vista de pistas y el panel de gráficos.

✅ **Ampliado en v0.66** — Rediseño con 6 tabs (Generales, Pistas, Álbumes, Artistas, Géneros, Sellos). Nuevas tarjetas: géneros únicos, formatos únicos, sellos únicos. Nuevos gráficos: distribución de duración, bitrate y formato de pistas; distribución de álbumes por cantidad de pistas, duración y décadas; top 10 géneros en barras; top 10 sellos. Se eliminó el gráfico de ratings.

**Descripción original:**
Una pantalla accesible desde un botón en la Biblioteca que muestra estadísticas visuales del contenido musical del usuario: totales, distribuciones por género, por década, por formato, artistas con más pistas, canciones más reproducidas, y más. Los datos se presentan con gráficos de barras y/o torta según el tipo de información.

---

### Estadísticas propuestas

| Estadística | Tipo de gráfico | Fuente de datos |
|---|---|---|
| Totales: pistas, artistas, álbumes, tiempo total | Tarjetas de resumen (números grandes) | `COUNT`, `SUM(duration_ms)` |
| Distribución por género | Torta + leyenda | `GROUP BY genre` |
| Distribución por década (60s, 70s, 80s…) | Barras verticales | `GROUP BY (year / 10) * 10` |
| Distribución por formato (MP3, FLAC, OGG…) | Torta o barras | `GROUP BY format` |
| Top 10 artistas por cantidad de pistas | Barras horizontales | `GROUP BY artist ORDER BY COUNT DESC` |
| Top 10 pistas más reproducidas | Barras horizontales | `ORDER BY play_count DESC LIMIT 10` |
| Distribución de ratings (0★ a 5★) | Barras verticales | `GROUP BY rating` |
| Distribución de bitrate (128, 192, 320 kbps…) | Histograma de barras | `GROUP BY bitrate_kbps` |

---

### Librerías disponibles

#### 1. `PyQt6-Charts` — `PyQt6.QtCharts` (recomendado)

**Librería nativa del ecosistema Qt.** Se instala como paquete aparte pero es parte oficial de Qt6. Integra perfectamente con el tema visual de AudioRep porque los gráficos son widgets de Qt que heredan el sistema de colores.

- **PyPI:** `PyQt6-Charts`
- **Licencia:** GPL v3 (misma que PyQt6)
- **Ventaja principal:** los gráficos son `QWidget` — se insertan en cualquier layout de PyQt6 como cualquier otro widget, sin fricción de incrustación.

```python
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

# ── Gráfico de torta: géneros ──────────────────────────────────────── #
def make_genre_pie(genre_counts: dict[str, int]) -> QChartView:
    series = QPieSeries()
    for genre, count in genre_counts.items():
        series.append(genre, count)

    # Estilo: colores de la paleta de AudioRep
    for i, slice_ in enumerate(series.slices()):
        slice_.setLabelVisible(True)
        slice_.setLabelColor(QColor("#e2e2f0"))

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("Géneros")
    chart.setBackgroundBrush(QColor("#1e1e2e"))   # bg-surface
    chart.setTitleBrush(QColor("#e2e2f0"))
    chart.legend().setLabelColor(QColor("#c0c0e0"))

    view = QChartView(chart)
    view.setRenderHint(view.renderHints() | view.renderHints().Antialiasing)
    return view

# ── Gráfico de barras: pistas por década ──────────────────────────── #
def make_decade_bars(decade_counts: dict[str, int]) -> QChartView:
    bar_set = QBarSet("Pistas")
    bar_set.setColor(QColor("#7c5cbf"))   # accent
    categories = []

    for decade, count in sorted(decade_counts.items()):
        bar_set.append(count)
        categories.append(decade)

    series = QBarSeries()
    series.append(bar_set)

    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    axis_x.setLabelsColor(QColor("#8888aa"))

    axis_y = QValueAxis()
    axis_y.setLabelFormat("%d")
    axis_y.setLabelsColor(QColor("#8888aa"))
    axis_y.setGridLineColor(QColor("#2a2a3e"))

    chart = QChart()
    chart.addSeries(series)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)
    chart.setBackgroundBrush(QColor("#1e1e2e"))
    chart.setTitleBrush(QColor("#e2e2f0"))
    chart.setTitle("Pistas por década")
    chart.legend().setVisible(False)

    view = QChartView(chart)
    return view
```

**Ventajas:** integración nativa Qt, mismo sistema de colores del tema, animaciones incluidas, no requiere canvas externo.
**Desventajas:** licencia GPL (compatible con el proyecto); tipos de gráficos más limitados que matplotlib.

---

#### 2. `matplotlib` con backend Qt — `FigureCanvasQTAgg`

La librería de gráficos más usada en Python. Se puede incrustar en PyQt6 usando su backend `Qt6Agg`.

- **PyPI:** `matplotlib`
- **Licencia:** PSF (BSD-like, muy permisiva)
- **Dependencia adicional:** `numpy` (casi siempre ya está instalado)

```python
import matplotlib
matplotlib.use('QtAgg')   # backend Qt6

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

class GenrePieChart(FigureCanvas):
    def __init__(self, genre_counts: dict[str, int], parent=None):
        fig = Figure(figsize=(5, 4), facecolor='#1e1e2e')
        super().__init__(fig)
        self.setParent(parent)

        ax = fig.add_subplot(111)
        ax.set_facecolor('#1e1e2e')

        labels  = list(genre_counts.keys())
        sizes   = list(genre_counts.values())
        colors  = ['#7c5cbf', '#5a3d9a', '#9b7dd4', '#4a3480',
                   '#b090ff', '#c0a8ff', '#3a2470', '#8a6cbf']

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors,
            autopct='%1.1f%%', startangle=90,
            textprops={'color': '#c0c0e0', 'fontsize': 10}
        )
        for t in autotexts:
            t.set_color('#e2e2f0')

        ax.set_title('Géneros', color='#e2e2f0', fontsize=13)
        fig.tight_layout()

class DecadeBarChart(FigureCanvas):
    def __init__(self, decade_counts: dict[str, int], parent=None):
        fig = Figure(figsize=(6, 3), facecolor='#1e1e2e')
        super().__init__(fig)

        ax = fig.add_subplot(111)
        ax.set_facecolor('#12121e')
        ax.tick_params(colors='#8888aa')
        ax.spines[:].set_color('#33334a')

        decades = sorted(decade_counts.keys())
        counts  = [decade_counts[d] for d in decades]

        bars = ax.bar(decades, counts, color='#7c5cbf', edgecolor='#5a3d9a')
        ax.set_title('Pistas por década', color='#e2e2f0', fontsize=12)
        ax.set_xlabel('Década', color='#8888aa')
        ax.set_ylabel('Pistas', color='#8888aa')

        for bar, val in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    str(val), ha='center', color='#c0c0e0', fontsize=9)
        fig.tight_layout()
```

**Ventajas:** mayor variedad de gráficos, documentación extensa, paleta personalizable con cualquier color hex.
**Desventajas:** requiere incrustación via `FigureCanvas` (leve fricción), agrega ~30 MB al bundle de PyInstaller.

---

### Tabla comparativa

| Aspecto | `PyQt6-Charts` | `matplotlib` |
|---|---|---|
| Integración con PyQt6 | Nativa (es un QWidget) | Via `FigureCanvasQTAgg` |
| Licencia | GPL v3 | BSD (PSF) |
| Peso en bundle | ~2 MB | ~30 MB |
| Tipos de gráfico | Barras, torta, línea, spline, scatter, área | +50 tipos incluyendo mapas de calor, radar, etc. |
| Personalización de colores | QColor / QPalette | Cualquier color hex/RGBA |
| Animaciones | Sí (integradas) | No nativas (requieren libs extra) |
| Recomendación | ✓ Preferido para AudioRep | Alternativa si se necesitan más tipos |

**Conclusión:** `PyQt6-Charts` es la mejor opción para AudioRep — se integra con el layout sin fricción, los colores de la paleta del tema se aplican directamente, y el peso en el instalador es mínimo. `matplotlib` queda como alternativa si en el futuro se necesitan gráficos más complejos (radar de géneros, histograma acumulado, etc.).

---

### Arquitectura propuesta

**Nuevo `StatsService`** (`services/stats_service.py`):

```python
from dataclasses import dataclass

@dataclass
class LibraryStats:
    total_tracks:    int
    total_artists:   int
    total_albums:    int
    total_hours:     float                  # suma de duration_ms convertida
    genre_counts:    dict[str, int]         # género → cantidad
    decade_counts:   dict[str, int]         # "1980s" → cantidad
    format_counts:   dict[str, int]         # "MP3" → cantidad
    rating_counts:   dict[int, int]         # 0-5 → cantidad
    top_artists:     list[tuple[str, int]]  # [(nombre, n_pistas), ...]
    top_tracks:      list[tuple[str, int]]  # [(título, play_count), ...]

class StatsService:
    def __init__(self, track_repo, artist_repo, album_repo): ...

    def compute(self) -> LibraryStats:
        """Calcula todas las estadísticas en un solo pase."""
        tracks = self._track_repo.get_all()
        # ... agrupar, contar, ordenar ...
        return LibraryStats(...)
```

**Nuevo `StatsPanel`** (`ui/widgets/stats_panel.py`):
- `QScrollArea` que contiene un grid de gráficos: 2 columnas, N filas.
- Fila 0: tarjetas de resumen (totales en texto grande).
- Fila 1: torta géneros + barras décadas.
- Fila 2: torta formatos + barras ratings.
- Fila 3: barras horizontales top artistas.
- Fila 4: barras horizontales top pistas reproducidas.

**Acceso desde `LibraryPanel`:**
- Botón `📊 Estadísticas` en la toolbar, junto al botón "Importar carpeta".
- Al hacer clic, muestra/oculta el `StatsPanel` como un tab adicional o un `QStackedWidget` que reemplaza la vista de tabla.

---

### Dependencias a agregar

```toml
# pyproject.toml — elegir UNA de las dos:
PyQt6-Charts>=6.6.0   # opción recomendada
# matplotlib>=3.8.0   # alternativa
```

---

### Consideraciones de performance

Las estadísticas se calculan sobre todos los tracks de la biblioteca. Con colecciones grandes (>10.000 pistas), el cálculo debe hacerse en un `QThread` worker para no bloquear la UI:

```python
class _StatsWorker(QThread):
    stats_ready = pyqtSignal(object)   # LibraryStats

    def run(self):
        stats = self._stats_service.compute()
        self.stats_ready.emit(stats)
```

Los gráficos se construyen en el hilo principal una vez que llegan los datos.

---

## Crossfade entre pistas

**Descripción:**
Transición suave entre el final de una pista y el comienzo de la siguiente: la pista actual va bajando de volumen gradualmente mientras la siguiente sube, durante un período configurable por el usuario (por ejemplo, 0 a 12 segundos). Cuando está en 0 el comportamiento es el actual (sin crossfade).

---

### Por qué no existe un crossfade nativo en VLC

`libVLC` no expone una API de crossfade entre medias. El método `audio_set_volume()` sí existe y es accesible desde python-vlc, pero no hay un mecanismo automático de fundido cruzado entre dos instancias.

La solución es implementarlo a nivel de aplicación: usar **dos instancias de `vlc.MediaPlayer`** en simultáneo y manejar el fundido con un `QTimer`.

---

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
    # ... lógica existente ...
    remaining_ms = dur - pos
    cf_ms = self._crossfade_ms   # leído de AppSettings

    if cf_ms > 0 and not self._crossfading and remaining_ms <= cf_ms + 200:
        next_track = self._peek_next()
        if next_track:
            self._start_crossfade(next_track)

def _start_crossfade(self, next_track: Track) -> None:
    self._crossfading = True
    self._player.start_crossfade(next_track, duration_ms=self._crossfade_ms)

def _on_crossfade_done(self) -> None:
    self._crossfading = False
    self._finish_pending = True
    self._on_track_finished()   # contabiliza play_count, avanza índice
```

#### Fundido en `VLCPlayer`

```python
def start_crossfade(self, next_track: Track, duration_ms: int) -> None:
    """Arranca el jugador secundario y comienza el fundido cruzado."""
    # Cargar siguiente pista en el player inactivo a volumen 0
    inactive = self._player_b if self._active == 'a' else self._player_a
    media = self._instance.media_new(next_track.file_path)
    inactive.set_media(media)
    inactive.audio_set_volume(0)
    inactive.play()

    # Timer de fundido: cada 50ms ajusta los volúmenes
    self._cf_duration   = duration_ms
    self._cf_elapsed    = 0
    self._cf_timer      = QTimer()
    self._cf_timer.setInterval(50)
    self._cf_timer.timeout.connect(self._crossfade_tick)
    self._cf_timer.start()

def _crossfade_tick(self) -> None:
    self._cf_elapsed += 50
    ratio = min(self._cf_elapsed / self._cf_duration, 1.0)

    master_vol = self.get_volume()   # volumen configurado por el usuario
    active   = self._player_a if self._active == 'a' else self._player_b
    inactive = self._player_b if self._active == 'a' else self._player_a

    active.audio_set_volume(int(master_vol * (1.0 - ratio)))
    inactive.audio_set_volume(int(master_vol * ratio))

    if ratio >= 1.0:
        self._cf_timer.stop()
        active.stop()
        self._active = 'b' if self._active == 'a' else 'a'
        self.crossfade_finished.emit()   # señal al PlayerService
```

---

### Curva de fundido

La interpolación lineal (`ratio = elapsed / duration`) es la más simple y ya suena bien. Se puede mejorar con una curva suave (ease-in-out):

```python
# Curva suave: más natural que lineal
ratio_smooth = ratio * ratio * (3 - 2 * ratio)  # smoothstep

# O curva logarítmica (más parecida a cómo percibe el oído):
import math
vol_out = int(master_vol * math.cos(ratio * math.pi / 2))
vol_in  = int(master_vol * math.sin(ratio * math.pi / 2))
```

La curva logarítmica (seno/coseno) se recomienda porque el oído percibe el volumen de forma logarítmica — da la sensación de un fundido más parejo.

---

### Configuración en SettingsDialog

```python
# core/settings.py — agregar:
@property
def crossfade_seconds(self) -> int:
    return int(self._s.value("crossfade_seconds", 0))

@crossfade_seconds.setter
def crossfade_seconds(self, v: int) -> None:
    self._s.setValue("crossfade_seconds", v)
```

En `SettingsDialog`, agregar un `QSpinBox` o `QSlider` con rango 0–12 y label "Crossfade (segundos)". Cuando el valor es 0, el crossfade está desactivado y el comportamiento es idéntico al actual.

---

### Casos especiales a considerar

| Caso | Comportamiento esperado |
|---|---|
| Crossfade = 0 | Sin cambios — flujo actual |
| Pista siguiente no existe (última de la cola) | No iniciar crossfade, dejar terminar normalmente |
| El usuario hace skip antes de terminar el crossfade | Cancelar timer, detener ambos players, reproducir la pista elegida |
| Pista muy corta (< duración del crossfade) | Empezar el crossfade desde el inicio de la pista si ya arrancó dentro del período |
| Radio (stream continuo) | Crossfade no aplica — deshabilitarlo cuando `source == TrackSource.CD` o radio |

---

### Dependencias nuevas

**Ninguna.** `audio_set_volume()` ya existe en python-vlc. El fundido se implementa íntegramente con `QTimer` y dos instancias de `vlc.MediaPlayer`, ambas cosas disponibles en el stack actual.

---

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `core/settings.py` | Agregar `crossfade_seconds` property |
| `infrastructure/audio/vlc_player.py` | Agregar segundo `MediaPlayer`, `start_crossfade()`, `_crossfade_tick()` |
| `services/player_service.py` | Detectar cuando iniciar el crossfade en `_poll_position()` |
| `ui/dialogs/settings_dialog.py` | Agregar control de crossfade (QSpinBox 0–12s) |
| `audiorep/ui/style/dark.qss` | Estilo del nuevo control en Settings si es necesario |

---

## Mini-reproductor (modo compacto)

**Descripción:**
Un botón pequeño en la interfaz que colapsa la ventana principal a un reproductor mínimo: solo muestra los controles de transporte, el nombre de la pista y el control de volumen. Útil para escuchar música mientras se trabaja en otra aplicación. La ventana se mantiene al frente de las demás.

---

### Diseño del mini-reproductor

```
┌──────────────────────────────────────────────────────────────┐
│ ⇄  ⏮  ⏹  ▶  ⏭  ↺   Don't Come Close — Ramones   🔊 ███░░ │  ← ~40px alto
└──────────────────────────────────────────────────────────────┘
```

- Ancho: ~520px fijo. Alto: ~52px (una sola fila, sin barra de progreso).
- Sin menú, sin pestañas, sin NowPlaying, sin VU meter, sin barra de estado.
- Ventana sin marco (`Qt.WindowType.FramelessWindowHint`) opcional, o con barra de título mínima.
- `Qt.WindowType.WindowStaysOnTopHint` para que quede por encima de otras ventanas.
- Arrastrable desde cualquier punto (sin barra de título, el usuario arrastra la ventana entera).

---

### Estrategia de implementación

**Opción A (recomendada): ocultar/mostrar componentes de la ventana existente**

No crear una segunda ventana. En cambio, al entrar en modo mini:
1. Guardar el tamaño y posición actual de la ventana.
2. Ocultar: `mainTabs`, `rightPanel`, barra de progreso (`progressSlider`), barra de estado.
3. Remover márgenes y el layout exterior para que la `PlayerBar` ocupe toda la ventana.
4. `setFixedSize(520, 52)` y aplicar `WindowStaysOnTopHint`.
5. Al salir del modo mini: restaurar todo al estado guardado.

**Opción B: ventana separada**

Crear un `MiniPlayerWindow(QWidget)` independiente, ocultar la ventana principal y mostrar la mini. Más aislamiento pero más código de sincronización de estado.

La Opción A es preferida porque reutiliza todos los widgets y señales ya conectados — el `PlayerBar` existente con sus controles sigue funcionando sin cambios.

---

### Implementación de la Opción A

```python
# En MainWindow:

def _setup_mini_toggle(self) -> None:
    """Agrega el botón de mini-reproductor a la PlayerBar."""
    self._mini_btn = QPushButton("⤢")   # o un ícono SVG pequeño
    self._mini_btn.setObjectName("miniPlayerBtn")
    self._mini_btn.setFixedSize(24, 24)
    self._mini_btn.setToolTip("Mini-reproductor")
    self._mini_btn.setCheckable(True)
    self._mini_btn.clicked.connect(self._toggle_mini_player)
    # Agregar al layout de la PlayerBar, alineado a la derecha

def _toggle_mini_player(self, checked: bool) -> None:
    if checked:
        self._enter_mini_mode()
    else:
        self._exit_mini_mode()

def _enter_mini_mode(self) -> None:
    self._normal_geometry = self.saveGeometry()
    self._normal_flags    = self.windowFlags()

    # Ocultar componentes
    self._tabs.setVisible(False)
    self._right_panel.setVisible(False)
    self._status_bar.setVisible(False)
    self._player_bar.hide_progress_row()   # método nuevo en PlayerBar

    # Ajustar ventana
    self.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.FramelessWindowHint
    )
    self.setFixedSize(520, 52)
    self.show()

def _exit_mini_mode(self) -> None:
    # Restaurar
    self._tabs.setVisible(True)
    self._right_panel.setVisible(True)
    self._status_bar.setVisible(True)
    self._player_bar.show_progress_row()

    self.setWindowFlags(self._normal_flags)
    self.setMinimumSize(860, 520)
    self.setMaximumSize(16777215, 16777215)  # quitar el fixed
    self.restoreGeometry(self._normal_geometry)
    self.show()
```

**Métodos nuevos en `PlayerBar`:**
```python
def hide_progress_row(self) -> None:
    """Oculta la fila 2 (barra de progreso) para el modo mini."""
    self._seek_slider.setVisible(False)
    self._pos_label.setVisible(False)
    self._dur_label.setVisible(False)

def show_progress_row(self) -> None:
    self._seek_slider.setVisible(True)
    self._pos_label.setVisible(True)
    self._dur_label.setVisible(True)
```

---

### Arrastre de ventana sin barra de título

Con `FramelessWindowHint`, la ventana no tiene barra de título y no se puede arrastrar por defecto. Implementar arrastre manual en `PlayerBar` o `MainWindow`:

```python
def mousePressEvent(self, event) -> None:
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

def mouseMoveEvent(self, event) -> None:
    if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
        self.move(event.globalPosition().toPoint() - self._drag_pos)
```

---

### Posición del botón de mini-reproductor

Opciones:
- **En la `PlayerBar`**, extremo derecho (después del volumen slider): integrado, siempre visible.
- **En la barra de menú**, como ícono pequeño a la derecha: separado de los controles de audio.

La primera opción es más natural para el usuario — el botón está junto a los demás controles.

**objectName y QSS propuestos:**
```css
QPushButton#miniPlayerBtn {
    background-color: transparent;
    color: #55557a;
    border: none;
    border-radius: 4px;
    font-size: 14px;
}
QPushButton#miniPlayerBtn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    color: #a0a0c0;
}
QPushButton#miniPlayerBtn:checked {
    color: #7c5cbf;
}
```

---

### Persistencia

Guardar en `QSettings`:
- Si el mini-reproductor estaba activo al cerrar → restaurarlo al abrir.
- Posición de la mini-ventana → restaurarla en la misma ubicación.

---

### Dependencias nuevas

**Ninguna.** Todo con PyQt6 nativo: `setWindowFlags`, `setFixedSize`, `saveGeometry`, `restoreGeometry`, `setVisible`.

---

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

✅ **Implementado en v0.65** — Botón "Exportar" en la toolbar de la biblioteca. Soporta XLSX (dos hojas: Biblioteca + Estadísticas), PDF (dos secciones) y CSV (solo pistas).

**Descripción original:**
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
