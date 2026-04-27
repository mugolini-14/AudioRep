name: "UI Builder"

# Skill: UI Builder — Mantenimiento del diseño visual de AudioRep

Este archivo es la referencia obligatoria antes de crear, modificar o reconstruir cualquier widget de AudioRep.
Debe leerse íntegramente antes de tocar cualquier archivo en `audiorep/ui/`.

---

## Regla fundamental: el QSS es la fuente de verdad

**Todo el estilo visual está en `audiorep/ui/style/dark.qss` y se aplica exclusivamente por `objectName`.**

El vínculo es:
```
widget.setObjectName("nombre")  ←→  QWidget#nombre { ... }  en dark.qss
```

Si un widget tiene el `objectName` incorrecto o no lo tiene, **el QSS no se aplica** y el widget aparecerá con el estilo base genérico (`#12121e` sobre blanco, sin forma).

Antes de escribir cualquier widget nuevo o reconstruir uno existente, **leer dark.qss primero** para conocer qué objectNames existen y qué tipo de widget espera cada selector.

---

## Paleta de colores

| Variable | Valor | Uso |
|---|---|---|
| `bg-deep` | `#12121e` | Fondo de ventana, fondo de tabla |
| `bg-surface` | `#1e1e2e` | Paneles: NowPlaying, PlayerBar, headers |
| `bg-toolbar` | `#1a1a2e` | Toolbar de biblioteca, árbol |
| `bg-raised` | `#2a2a3e` | Hover, botones secundarios, cover placeholder |
| `accent` | `#7c5cbf` | Color de acento — play button, selección, focus |
| `accent-dim` | `#5a3d9a` | Acento oscurecido — botón presionado |
| `accent-light` | `#8d6dd0` | Acento claro — hover del play button |
| `text-main` | `#e2e2f0` | Texto principal, seleccionado |
| `text-mid` | `#c0c0e0` | Texto de listas y tablas |
| `text-dim` | `#8888aa` / `#a0a0c0` | Texto secundario (artista, labels) |
| `text-faint` | `#7070a0` | Texto muy tenue (álbum, timestamps, headers) |
| `text-ghost` | `#55557a` | Texto casi invisible (iconos apagados, placeholder) |
| `border` | `#33334a` | Bordes sutiles |
| `border-dim` | `#2a2a3e` | Bordes aún más sutiles |

**No usar valores de color que no estén en esta paleta.** Si el diseño necesita un color nuevo, agregarlo aquí y en dark.qss al mismo tiempo.

---

## Tipografía

- Fuente: `"Segoe UI", "Inter", sans-serif`
- Tamaño base: `13px`
- Tamaños específicos por contexto:

| Contexto | Tamaño | Peso |
|---|---|---|
| Título de pista (`trackTitle`) | 14px | 700 (bold), italic |
| Artista (`trackArtist`) | 13px | normal, italic |
| Álbum/disco (`trackAlbum`) | 13px | normal, italic |
| Sello (`trackLabel`) | 13px | normal, italic |
| Año (`trackYear`) | 13px | normal, italic |
| Rating (`trackRating`) | 13px | normal, italic |
| Botones de biblioteca | 12px | normal |
| Headers de tabla | 11px | 600, uppercase, letter-spacing 0.5px |
| Labels de tiempo | 16px | tabular-nums |
| Status bar | 11px | normal |

---

## Layout general de la ventana (`MainWindow`)

```
┌──────────────────────────────────────────────────────┬──────────────────┐
│ menuBar                                              │                  │
├──────────────────────────────────────────────────────┤                  │
│ QTabWidget#mainTabs                                  │ QWidget          │
│ ┌──────────┬──────┬───────────┬──────────────────┐  │ #rightPanel      │
│ │Biblioteca│  CD  │ Playlists │      Radio       │  │ (210–320px)      │
│ └──────────┴──────┴───────────┴──────────────────┘  │                  │
│ [contenido del tab activo]                           │ NowPlaying       │
│                                                      │ (stretch=1)      │
│                                                      ├──────────────────┤
│                                                      │ VUMeterWidget    │
│                                                      │ #vuMeter (110px) │
├──────────────────────────────────────────────────────┴──────────────────┤
│ QFrame#separator (1px, #33334a)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ PlayerBar  (min-height: 90px)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ QStatusBar                                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

El splitter horizontal principal (`mainSplitter`) separa el `QTabWidget` (Expanding, stretch=1) del `rightPanel` (Fixed, stretch=0). NowPlaying y VUMeterWidget están dentro de `rightPanel` con layout vertical.

### Layout del tab CD

El tab CD contiene un `QSplitter#cdTabSplitter` horizontal con dos columnas:

```
┌──────────────────────────────┬────────────────────────┐
│ CDPanel                      │ CDMetadataPanel        │
│ (stretch=1, expande)         │ (220–340px, stretch=0) │
└──────────────────────────────┴────────────────────────┘
```

---

## Inventario completo de objectNames

### Ventana principal

| objectName | Widget | Notas |
|---|---|---|
| `mainSplitter` | `QSplitter` | Splitter horizontal principal (tabs izq. / rightPanel der.) |
| `mainTabs` | `QTabWidget` | Tabs: Biblioteca, CD, Playlists, Radio |
| `separator` | `QFrame` | Línea de 1px entre área principal y PlayerBar |
| `playerBar` | `QWidget` | Barra de controles inferior |
| `rightPanel` | `QWidget` | Panel derecho fijo (210–320px): NowPlaying + VUMeter |
| `vuMeter` | `QWidget` | VU metro estéreo real, altura fija 110px, fondo `#12121e` |
| `cdTabSplitter` | `QSplitter` | Splitter interno del tab CD: CDPanel / CDMetadataPanel |

### CDPanel (`audiorep/ui/widgets/cd_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `cdPanel` | `QWidget` (raíz) | Panel principal del tab CD |
| `cdDriveLabel` | `QLabel` | Label "Lectora:" |
| `cdDriveCombo` | `QComboBox` | Selector de unidad de CD |
| `cdStatus` | `QLabel` | Estado del disco inline en la fila de lectora (ej. "Disco detectado · 11 pistas"). `#7070a0`, 12px |
| `cdDiscInfo` | `QLabel` | Info completa del disco en una línea: "Artista — Álbum (Año)". `text-main`, 13px bold, debajo de la fila de lectora |
| `cdTrackTable` | `QTableWidget` | Tabla de pistas — columnas: #, Título, estado de ripeo. Cabeceras visibles, misma paleta que `trackTable` |
| `cdDetectBtn` | `QPushButton` | Botón "Detectar" |
| `cdIdentifyBtn` | `QPushButton` | Botón "Identificar" |
| `cdPlayBtn` | `QPushButton` | Botón "▶ Reproducir CD" — color de acento `#5a3d9a` |
| `cdRipAllBtn` | `QPushButton` | Botón "💾 Ripear todo" |

> **Nota v0.40:** La portada del disco fue eliminada del CDPanel. Se muestra únicamente en el NowPlaying lateral. Los labels `cdCover`, `cdAlbum` y `cdArtist` ya no existen.

### NowPlaying (`audiorep/ui/widgets/now_playing.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `nowPlayingPanel` | `QWidget` (raíz) | Panel derecho superior, `bg-surface`, border-left |
| `coverLabel` | `QLabel` | Portada del álbum, 190×190, `bg-raised`, border-radius 6px |
| `trackTitle` | `QLabel` | Título de la pista, 14px bold |
| `trackArtist` | `QLabel` | Artista, 12px, `#a0a0c0` |
| `trackAlbum` | `QLabel` | Nombre del disco, 11px, `#7070a0` |
| `trackLabel` | `QLabel` | Sello discográfico, 11px, `#7070a0`, cursiva |
| `trackYear` | `QLabel` | Año, 11px, `#7070a0` |
| `trackRating` | `QLabel` | Estrellas ★☆, 12px, `accent`, letter-spacing 2px |

**Orden estándar obligatorio (v0.60+):**
```
1. coverLabel      — portada (siempre)
2. trackTitle      — nombre de la pista (oculto en modo identificación de disco)
3. trackArtist     — nombre del artista
4. trackAlbum      — nombre del disco
5. trackLabel      — sello discográfico
6. trackYear       — año
7. trackRating     — rating (solo pistas de biblioteca)
```
Todos los campos opcionales usan `setVisible(bool(valor))`. El orden del layout en `_build_ui()` debe respetar siempre esta secuencia. Nunca alterar el orden de los widgets entre versiones.

**Modos de actualización:**
- `update_track(track)` — pista de biblioteca o CD en reproducción. Muestra todos los campos disponibles, incluido `trackTitle`.
- `update_cd_disc(disc)` — disco identificado pero sin pista en reproducción. `trackTitle` se oculta; `trackAlbum` muestra el título del disco.
- `update_cover(data)` — reemplaza solo la portada sin tocar el texto.
- `clear()` — limpia todo y vuelve al placeholder.

> **Nota v0.57:** Todos los campos usan `setVisible(bool)` en lugar de mostrar "—".
> **Nota v0.60:** Sello (`trackLabel`) añadido, orden fijo: portada → título → artista → disco → sello → año → rating. `update_cd_disc` oculta `trackTitle` y muestra el álbum en `trackAlbum`.
> **Tipografía estándar (v0.60+):** `trackTitle` = 14px, bold, italic. Todos los demás campos = 13px, normal, italic. Misma familia tipográfica para todos. No alterar esta jerarquía.

### PlayerBar (`audiorep/ui/widgets/player_bar.py`)

| objectName | Widget | Tamaño | Descripción |
|---|---|---|---|
| `playerBar` | `QWidget` (raíz) | min-height 90px | Fondo `bg-surface`, border-top |
| `transportFrame` | `QFrame` | — | Contenedor redondeado para los 6 botones de transporte. `border-radius: 14px`, fondo `#252538` |
| `modeButton` | `QPushButton` | 46×46 | Shuffle (⇄) y Repeat (↺). Checkable. Inactivo: blanco `#ffffff`. Activo: `#b090ff` |
| `transportButton` | `QPushButton` | 46×46 | Prev (⏮), Stop (⏹) y Next (⏭). Fondo transparente, color blanco, font-size 22px |
| `playButton` | `QPushButton` | 46×46 | Play/Pause. Fondo transparente, color blanco, font-size 28px |
| `trackLabel` | `QLabel` | stretch=1 | Título y artista de la pista en reproducción (`"Título — Artista"`). 16px, `text-main`. Centrado en la fila 1 entre los dos `timeLabel` |
| `timeLabel` | `QLabel` | fixed 52px | Tiempo transcurrido y total, flanqueando el `trackLabel`. `#7070a0`, 16px tabular-nums |
| `progressSlider` | `QSlider` | stretch (fila 2) | Barra de progreso a ancho completo. Handle blanco `#e2e2f0` |
| `volumeIcon` | `QPushButton` | 46×46 | Ícono 🔊/🔇. Actúa como botón de mute toggle. Color `text-ghost`. Al hacer clic silencia/restaura el volumen anterior |
| `volumeSlider` | `QSlider` | min 180px / max 280px | Volumen. Groove 3px, handle `#a090c0` |

**Layout de PlayerBar (2 filas):**
```
Fila 1: [transportFrame: modeBtn | prevBtn | stopBtn | playBtn | nextBtn | modeBtn]
        [timeLabel] [track info label (stretch)] [timeLabel]
        [volumeIcon] [volumeSlider]

Fila 2: [════════════════ progressSlider (ancho completo) ════════════════]
```

**Todos los botones de transporte tienen fondo transparente y color blanco** — sin fondos de colores. El único elemento con color de acento es el `modeButton:checked` (`#b090ff`) y el `transportFrame` que los contiene.

### CDMetadataPanel (`audiorep/ui/widgets/cd_metadata_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `cdMetadataPanel` | `QWidget` (raíz) | Panel lateral del tab CD. `border-left: 1px solid #33334a`, fondo `#18182a` |
| `cdMetaTitle` | `QLabel` | Título "Búsqueda de metadatos". Violeta, 12px bold |
| `cdMetaLabel` | `QLabel` | Labels secundarios ("Servicio:", "Resultados:", etc.). `#8888aa`, 11px |
| `cdMetaServiceCombo` | `QComboBox` | Selector de servicio (MusicBrainz, GnuDB). `#252538`, border `#3a3a5a` |
| `cdMetaSearchBtn` | `QPushButton` | Botón "🔍 Buscar". Estilo secundario oscuro |
| `cdMetaApplyBtn` | `QPushButton` | Botón "✔ Aplicar al disco". Fondo `#4a3480` (acento oscuro), bold |
| `cdMetaResultsList` | `QListWidget` | Lista de resultados de búsqueda. Altura máx. 120px |
| `cdMetaTrackList` | `QListWidget` | Lista de pistas del resultado seleccionado. Expande |
| `cdMetaDetail` | `QLabel` | Álbum y artista del resultado seleccionado. 13px bold |
| `cdMetaDetailSmall` | `QLabel` | Año y género. `#8888aa`, 11px |
| `cdMetaSeparator` | `QFrame` | Separador horizontal interno. `#2a2a3e`, 1px |

### LibraryPanel (`audiorep/ui/widgets/library_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `libraryPanel` | `QWidget` (raíz) | Panel completo |
| `libraryToolbar` | `QWidget` | Toolbar superior. Fondo `#1a1a2e`, border-bottom |
| `searchBox` | `QLineEdit` | Buscador. `bg-raised`, focus: border `accent` |
| `importButton` | `QPushButton` | Botón "Importar carpeta" en la toolbar. Estilo unificado de acción (`#4a3480`, bold) |
| `libraryEditBtn` | `QPushButton` | Botón "✏ Editar tags" en la barra inferior. Estilo unificado de acción, `stretch=1` |
| `libraryIdentifyBtn` | `QPushButton` | Botón "🔍 Identificar" en la barra inferior. Estilo unificado de acción, `stretch=1` |
| `importProgress` | `QProgressBar` | Barra de progreso de scan. 3px de alto, oculta por defecto |
| `librarySplitter` | `QSplitter` | Splitter horizontal árbol / tabla |
| `treeContainer` | `QWidget` | Contenedor del árbol. Fondo `#1a1a2e`, border-right |
| `libraryTree` | `QTreeWidget` | Árbol artista→álbum. Sin header, indentación 14px |
| `trackTableContainer` | `QWidget` | Contenedor de la tabla. Fondo `bg-deep` |
| `libraryContext` | `QLabel` | "Toda la biblioteca (N pistas)". `#7070a0`, 11px, fondo `#1a1a2e` |
| `trackTable` | `QTableView` | Tabla de pistas. Sin gridlines, alternating rows |

### StatsPanel (`audiorep/ui/widgets/stats_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `statsPanel` | `QWidget` (raíz) | Panel de estadísticas de la biblioteca |
| `statsScrollContent` | `QWidget` | Contenedor interno de cada tab con `QScrollArea` |
| `statsSummaryCard` | `QFrame` | Tarjeta de resumen en la tab Generales (8 tarjetas en 2 filas de 4) |
| `statsCardValue` | `QLabel` | Número grande de la tarjeta (ej. "1.234") |
| `statsCardLabel` | `QLabel` | Etiqueta de la tarjeta (ej. "pistas") |
| `statsSectionLabel` | `QLabel` | Título de sección dentro de un tab (también usado para notas de "sin datos") |
| `statsChartView` | `QChartView` | Vista de cualquier gráfico (bar, pie, hbar) |
| `statsTabs` | `QTabWidget` | Tabs: Generales, Pistas, Álbumes, Artistas, Géneros, Sellos |

**Funciones de fábrica disponibles (módulo-nivel, no métodos):**
- `make_bar_chart(title, categories, values)` → `QChartView` (barras verticales, acento violeta)
- `make_pie_chart(title, data: dict[str, int])` → `QChartView` (donut con leyenda inferior)
- `make_hbar_chart(title, labels, values, min_height, left_margin)` → `QChartView` (barras horizontales para tops)
- `_chart_row(*views)` → `QHBoxLayout` (coloca 2 vistas en la misma fila, mitad de ancho cada una)

Ver sección **Estándar de layout de gráficos (StatsPanel)** para las reglas de cuándo usar `_chart_row`.

---

### SettingsDialog (`audiorep/ui/dialogs/settings_dialog.py`)

El diálogo de configuración tiene las siguientes secciones (v0.69+):

| Campo | Widget | Descripción |
|---|---|---|
| API key AcoustID | `QLineEdit` | Clave para identificación por huella de audio |
| Formato de ripeo | `QComboBox` | FLAC / MP3 / OGG / WAV |
| Directorio de ripeo | `QLineEdit` + `QPushButton#SettingsDirBtn` | Carpeta de destino del ripeo |
| API key Last.fm | `QLineEdit` | Clave para obtener géneros de Last.fm (opcional) |
| Enriquecimiento automático | `QCheckBox` | Activa/desactiva actualización automática de metadatos |
| Intervalo (días) | `QSpinBox` | Cada cuántos días ejecutar el enriquecimiento (sufijo " días") |
| Última ejecución | `QLabel` | Fecha de la última ejecución del enriquecimiento |
| "Actualizar ahora" | `QPushButton` | Emite `app_events.enrichment_requested` al hacer clic |

El botón "Actualizar ahora" emite la señal — nunca llama directamente al service. `LibraryController` escucha esa señal y llama `enrichment_service.start()`.

---

### RadioPanel (`audiorep/ui/widgets/radio_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `RadioPanel` | `QWidget` (raíz) | Panel de radio |
| `RadioTabs` | `QTabWidget` | Pestañas internas (Buscar / Guardadas / Favoritas) |
| `RadioSearchInput` | `QLineEdit` | Búsqueda principal, focus: border `accent` |
| `RadioCountryInput` | `QLineEdit` | Filtro por país, maxWidth 160px |
| `RadioGenreInput` | `QLineEdit` | Filtro por género, maxWidth 160px |
| `RadioResultsTable` | `QTableWidget` | Resultados de búsqueda — columnas: Nombre (stretch), País (60px), Género (110px), Bitrate (75px). Mismo estilo visual que `trackTable` |
| `RadioSavedTable` | `QTableWidget` | Emisoras guardadas — columnas: Nombre (stretch), País (60px), Género (110px), Bitrate (75px). Favoritas marcadas con ♥. Incluye barra de filtro local (nombre/país/género) encima de la tabla |
| `RadioFavsTable` | `QTableWidget` | Emisoras favoritas — mismas columnas y estilo que RadioSavedTable. Incluye barra de filtro local |

> **Nota v0.40:** `RadioResultsList` (QListWidget) fue reemplazado por `RadioResultsTable` (QTableWidget).
> **Nota v0.42:** `RadioSavedList` (QListWidget) fue reemplazado por `RadioSavedTable` (QTableWidget).
> **Nota v0.44:** `RadioFavsList` (QListWidget) fue reemplazado por `RadioFavsTable` (QTableWidget). Se agregaron barras de filtro local en las pestañas Guardadas y Favoritas, con los mismos objectNames de inputs que la pestaña Buscar.
| `RadioNowPlaying` | `QLabel` | Emisora en reproducción. `bg-toolbar`, color `accent` |
| `RadioBtnPlay` | `QPushButton` | Reproducir. Fondo `accent` |
| `RadioBtnStop` | `QPushButton` | Detener. Estilo secundario |
| `RadioBtnSearch` | `QPushButton` | Buscar. Fondo `accent-dim` |
| `RadioBtnSave` | `QPushButton` | Guardar emisora. Estilo secundario |
| `RadioBtnDelete` | `QPushButton` | Eliminar emisora. Estilo secundario |
| `RadioBtnFav` | `QPushButton` | Toggle favorito. Hover: color rojizo `#e06080` |

---

## Estándar de botones de acción

Todos los botones que aparecen debajo de tablas o listas en cualquier panel deben seguir este estándar sin excepción:

- **QSS**: `background-color: #4a3480; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: bold;`
  - `:hover` → `background-color: #5a409a`
  - `:disabled` → `background-color: #252538; color: #55557a`
- **Layout**: `btn_row.addWidget(btn, stretch=1)` para distribución a igual ancho. **Nunca** usar `setSizePolicy(Expanding, Fixed)` en botones de acción.
- **Márgenes del contenedor**: `setContentsMargins(8, 8, 8, 8)` y `setSpacing(8)` en el `QHBoxLayout` que agrupa los botones. El layout exterior del panel debe proveer al menos 8px de margen inferior.

---

## Estándar de diálogos modales

Todos los diálogos emergentes (`QDialog`, `QInputDialog`, `QMessageBox`) usan este estándar visual definido en `dark.qss`. **No aplicar estilos inline.**

### Campos de texto (`QLineEdit`)

Regla global en `dark.qss` — aplica automáticamente a cualquier `QLineEdit` sin objectName específico:

```css
QLineEdit {
    background-color: #2a2a3e;
    color: #e2e2f0;
    border: 1px solid #33334a;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    selection-background-color: #7c5cbf;
}
QLineEdit:focus { border-color: #7c5cbf; }
```

### Botones de diálogo (`QDialogButtonBox`)

```css
QDialogButtonBox QPushButton {
    background-color: #4a3480;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: bold;
    min-width: 80px;
}
QDialogButtonBox QPushButton:hover { background-color: #5a409a; }
QDialogButtonBox QPushButton:pressed { background-color: #3a2470; }
```

### Botón de selección de carpeta (`SettingsDirBtn`)

El botón "…" que abre un `QFileDialog` sigue el estilo de input secundario:

```css
QPushButton#SettingsDirBtn {
    background-color: #2a2a3e;
    color: #c0c0e0;
    border: 1px solid #33334a;
    border-radius: 4px;
    padding: 4px 8px;
}
QPushButton#SettingsDirBtn:hover { border-color: #7c5cbf; color: #e2e2f0; }
```

### Convención de textos en botones de confirmación

- **Nunca usar** `QMessageBox.question()` con `StandardButton.Yes/No` — los textos son en inglés y no se pueden cambiar fácilmente.
- **Siempre construir** el `QMessageBox` manualmente con botones en español:

```python
msg = QMessageBox(self)
msg.setWindowTitle("Confirmar")
msg.setText("¿Mensaje de confirmación?")
msg.setIcon(QMessageBox.Icon.Question)
yes_btn = msg.addButton("Sí", QMessageBox.ButtonRole.YesRole)
msg.addButton("No", QMessageBox.ButtonRole.NoRole)
msg.exec()
if msg.clickedButton() == yes_btn:
    # acción confirmada
```

---

## Estándar de QComboBox (dropdowns)

Todos los `QComboBox` de la aplicación comparten una regla base global en `dark.qss`:

```css
QComboBox {
    background-color: #2a2a3e;
    color: #c0c0e0;
    border: 1px solid #33334a;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 12px;
}
QComboBox:hover, QComboBox:focus { border: 1px solid #7c5cbf; }
QComboBox::drop-down { border-left: 1px solid #33334a; width: 22px; border-radius: 0 6px 6px 0; }
QComboBox::down-arrow { image: url(./arrow_down.svg); width: 10px; height: 6px; }
QComboBox QAbstractItemView { background-color: #2a2a3e; ... }
```

- El archivo `audiorep/ui/style/arrow_down.svg` contiene el ícono de la flecha chevron en color `#c0c0e0`.
- La URL `url(./arrow_down.svg)` se resuelve a ruta absoluta en `main_window._load_stylesheet()` para compatibilidad con PyInstaller.
- **No crear reglas `QComboBox#objectName`** para estilos visuales generales. Solo usar objectName-specific si el combo necesita un tamaño o comportamiento realmente diferente.

---

## Reglas obligatorias al crear o modificar widgets

### 1. Todo widget estilizado DEBE tener `setObjectName()`

```python
# ✅ Correcto
btn = QPushButton("Importar carpeta")
btn.setObjectName("importButton")

# ❌ Incorrecto — el QSS no se aplicará
btn = QPushButton("Importar carpeta")
```

### 2. El objectName DEBE existir en dark.qss ANTES de usarlo en código

Si el widget es nuevo, agregar la regla en dark.qss **en el mismo commit** en que se crea el widget. El orden en dark.qss debe seguir la organización por secciones (ver el archivo).

### 3. Un mismo objectName puede usarse en varios widgets del mismo tipo

Los botones de acción inferiores de `LibraryPanel` tienen objectNames propios: `libraryEditBtn` y `libraryIdentifyBtn`. El botón "Importar carpeta" usa `importButton`. Cada uno tiene su regla en `dark.qss` con el estilo unificado de acción.

### 4. No usar estilos inline (`setStyleSheet` en el widget)

```python
# ❌ Prohibido — rompe el tema centralizado
btn.setStyleSheet("background-color: red;")

# ✅ Correcto — agregar la regla en dark.qss
# QPushButton#miBoton { background-color: #7c5cbf; }
```

### 5. No hardcodear colores de la paleta en Python

Los colores están en dark.qss. Si se necesita un color en Python (p. ej., para un pixmap), usar los valores de la paleta tal como están documentados arriba.

### 6. Widgets de modal y diálogo

Los diálogos (`SettingsDialog`, `TagEditorDialog`, `RipperDialog`, `QInputDialog`, `QMessageBox`) usan el estándar de diálogos modales definido en `dark.qss`. Ver sección **Estándar de diálogos modales** más abajo.

---

## Proceso para agregar un widget nuevo

1. **Leer dark.qss** — verificar si ya existe un selector reutilizable.
2. Si el objectName es nuevo: **agregar la regla en dark.qss** en la sección correspondiente.
3. En el widget Python: llamar `setObjectName("nombre")` inmediatamente después de crear el widget.
4. Si el widget tiene estados (hover, pressed, checked, disabled): asegurarse de que dark.qss cubra todos los pseudo-estados necesarios.
5. Verificar visualmente que el estilo se aplique correctamente antes de marcar la tarea como terminada.

---

## Proceso para reconstruir un widget existente (tras pérdida de código)

Este es el escenario que motivó esta skill. Procedimiento estricto:

1. **Leer dark.qss primero**. Buscar todos los selectores relacionados con el widget (por ejemplo, para `PlayerBar` buscar `playerBar`, `playButton`, `transportButton`, etc.).
2. **Leer el docstring del archivo** si está disponible — contiene el layout y los objectNames esperados.
3. **Reconstruir respetando exactamente** los objectNames, tamaños fijos (`setFixedSize`, `setFixedWidth`, `setFixedHeight`) y la estructura de layout que define el diseño.
4. **No inventar objectNames**. Si el selector en dark.qss dice `QPushButton#transportButton`, el botón debe llamarse `transportButton`, no `prevButton`, `navButton` ni ninguna variante.
5. **Verificar contra dark.qss** al terminar: cada `setObjectName(x)` del widget reconstruido debe tener un selector `#x { ... }` en dark.qss (o ser intencional que herede el estilo base).

---

## Estándar de layout de gráficos (StatsPanel)

Aplica a todos los tabs del `StatsPanel` (`audiorep/ui/widgets/stats_panel.py`).

### Alturas estándar (v0.73+)

Las alturas son **fijas** (`setFixedHeight`), no mínimas. Esto garantiza uniformidad y elimina el scroll interno de `QGraphicsView`.

| Constante | Valor | Aplica a |
|---|---|---|
| `_H_HALF` | 280 px | Gráficos en media fila: `make_bar_chart`, `make_pie_chart` |
| `_H_FULL` | 340 px | Gráficos en fila completa: `make_hbar_chart` (tops) |

**Regla de implementación en `_chart_view()`:**
```python
view.setFixedHeight(height)                                            # altura exacta, no mínima
view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # sin scroll interno
view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
```

### Reglas de layout

| Tipo de gráfico | Ancho en fila | Observaciones |
|---|---|---|
| Gráfico regular (bar, pie) con par natural | Mitad de fila (`_chart_row()`) | Hasta 2 por fila |
| Gráfico regular sin par natural | Fila completa | No forzar medio ancho si no hay candidato |
| Gráfico "top" horizontal (`make_hbar_chart`) | Fila completa | Siempre solitario, sin excepción |

### Leyenda en gráficos de torta

La leyenda se posiciona a la **izquierda** (`AlignLeft`), dejando más espacio para el área de la torta.

```python
chart.legend().setAlignment(Qt.AlignmentFlag.AlignLeft)
```

### Cómo emparejar

```python
# Construir ambas vistas primero, luego decidir el layout:
vista_a = make_bar_chart(...) if condicion_a else None
vista_b = make_pie_chart(...)  if condicion_b else None

if vista_a and vista_b:
    layout.addLayout(_chart_row(vista_a, vista_b))
elif vista_a:
    layout.addWidget(vista_a)
elif vista_b:
    layout.addWidget(vista_b)
```

### Pares establecidos (v0.71+)

| Tab | Fila | Gráfico izquierdo | Gráfico derecho |
|---|---|---|---|
| Pistas | 1 | Duración de pistas (bar) | — |
| Pistas | 2 | Formatos de pistas (pie) | BitRate de pistas (bar) |
| Álbumes | 1 | Pistas por álbum (bar) | Duración de álbumes (bar) |

Los "top" (Top 10 pistas, Top 10 artistas, Top 10 géneros, etc.) siempre ocupan fila completa.

---

## Checklist antes de entregar un widget nuevo o modificado

- [ ] Todos los widgets visibles tienen `setObjectName()`
- [ ] Cada objectName existe como selector en dark.qss
- [ ] No hay llamadas a `setStyleSheet()` en el widget
- [ ] No hay colores hardcodeados en Python
- [ ] Los tamaños fijos (`setFixedSize`, etc.) coinciden con los documentados
- [ ] Los widgets checkables (`setCheckable(True)`) tienen regla `:checked` en dark.qss
- [ ] Los widgets deshabilitables tienen regla `:disabled` en dark.qss si corresponde
- [ ] El layout (filas, columnas, splitter, stretch factors) coincide con el diagrama documentado
- [ ] Si se agregó un objectName nuevo: la regla en dark.qss fue agregada en el mismo cambio

---

## Anti-patrones conocidos (errores que ya ocurrieron)

| Anti-patrón | Consecuencia | Corrección |
|---|---|---|
| Reconstruir un widget sin leer dark.qss primero | objectNames incorrectos → widget sin estilo, diseño roto | Leer dark.qss antes de escribir una línea |
| Usar `prevButton` en vez de `transportButton` | El botón aparece sin estilo | Usar el nombre exacto del selector QSS |
| `LibraryPanel` como tabla plana sin árbol | Diseño completamente distinto al original | El panel DEBE tener QSplitter con QTreeWidget a la izquierda |
| `PlayerBar` en una sola fila | No coincide con el diseño de 2 filas | Fila 1: controles + info + volumen; Fila 2: tiempo + progreso + tiempo |
| `import sip` en un controller | Crash en PyQt6 (sip no existe) | No importar sip; en PyQt6 usar directamente los objetos Qt |
| `__import__()` para importar módulos de Qt | Crash en runtime | Siempre usar `from PyQt6.QtCore import ...` al inicio del archivo |
| `setStyleSheet()` inline para "arreglar" un widget | Inconsistencia visual, difícil de mantener | Agregar la regla en dark.qss |
| Omitir `setObjectName("playerBar")` en la raíz del widget | `QWidget#playerBar { min-height: 90px }` no se aplica | La raíz del widget siempre necesita su objectName |
