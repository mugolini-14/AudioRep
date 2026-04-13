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
| Título de pista (`trackTitle`) | 14px | 700 (bold) |
| Artista (`trackArtist`) | 12px | normal |
| Álbum (`trackAlbum`) | 11px | normal |
| Rating (`trackRating`) | 12px | normal |
| Botones de biblioteca | 12px | normal |
| Headers de tabla | 11px | 600, uppercase, letter-spacing 0.5px |
| Labels de tiempo | 11px | tabular-nums |
| Status bar | 11px | normal |

---

## Layout general de la ventana (`MainWindow`)

```
┌──────────────────────────────────────────────────────┐
│ menuBar                                              │
├─────────────┬────────────────────────────────────────┤
│ NowPlaying  │  QTabWidget#mainTabs                   │
│ (220–320px) │  ┌──────────┬──────┬──────┬─────────┐ │
│ objectName: │  │ Biblioteca│  CD │Playlist│  Radio │ │
│ nowPlaying  │  └──────────┴──────┴──────┴─────────┘ │
│ Panel       │  [contenido del tab activo]            │
├─────────────┴────────────────────────────────────────┤
│ QFrame#separator (1px, #33334a)                      │
├──────────────────────────────────────────────────────┤
│ PlayerBar  (min-height: 90px)                        │
├──────────────────────────────────────────────────────┤
│ QStatusBar                                           │
└──────────────────────────────────────────────────────┘
```

El splitter horizontal principal (`mainSplitter`) separa `nowPlayingPanel` (Fixed) del `QTabWidget` (Expanding).

---

## Inventario completo de objectNames

### Ventana principal

| objectName | Widget | Notas |
|---|---|---|
| `mainSplitter` | `QSplitter` | Splitter horizontal principal |
| `mainTabs` | `QTabWidget` | Tabs: Biblioteca, CD, Playlists, Radio |
| `separator` | `QFrame` | Línea de 1px entre área principal y PlayerBar |
| `playerBar` | `QWidget` | Barra de controles inferior |

### NowPlaying (`audiorep/ui/widgets/now_playing.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `nowPlayingPanel` | `QWidget` (raíz) | Panel izquierdo, `bg-surface`, border-right |
| `coverLabel` | `QLabel` | Portada del álbum, 190×190, `bg-raised`, border-radius 6px |
| `trackTitle` | `QLabel` | Título, 14px bold |
| `trackArtist` | `QLabel` | Artista, 12px, `#a0a0c0` |
| `trackAlbum` | `QLabel` | Álbum, 11px, `#7070a0` |
| `trackRating` | `QLabel` | Estrellas ★☆, 12px, `accent`, letter-spacing 2px |

### PlayerBar (`audiorep/ui/widgets/player_bar.py`)

| objectName | Widget | Tamaño | Descripción |
|---|---|---|---|
| `playerBar` | `QWidget` (raíz) | min-height 90px | Fondo `bg-surface`, border-top |
| `modeButton` | `QPushButton` | 32×32 | Shuffle (⇄) y Repeat (↺). Checkable. Apagado: `text-ghost`. Encendido: `accent` |
| `transportButton` | `QPushButton` | 36×36 | Prev (⏮) y Next (⏭). Color `#c0c0e0`, hover `bg-raised` |
| `playButton` | `QPushButton` | 48×48 | Play/Pause. Fondo `accent`, border-radius 24px, font-size 18px |
| `timeLabel` | `QLabel` | fixed 36px | Tiempo transcurrido y total. `#7070a0`, 11px tabular-nums |
| `progressSlider` | `QSlider` | stretch | Barra de progreso. Handle blanco `#e2e2f0` |
| `volumeIcon` | `QLabel` | — | Ícono 🔊. Color `text-ghost`, 14px |
| `volumeSlider` | `QSlider` | fixed 80px | Volumen. Groove 3px, handle `#a090c0` |

**Layout de PlayerBar (2 filas):**
```
Fila 1: [modeButton] [transportButton] [playButton] [transportButton] [modeButton]
        [─── stretch ──] track info label [─── stretch ──]
        [volumeIcon] [volumeSlider]

Fila 2: [timeLabel] [════ progressSlider ════] [timeLabel]
```

### LibraryPanel (`audiorep/ui/widgets/library_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `libraryPanel` | `QWidget` (raíz) | Panel completo |
| `libraryToolbar` | `QWidget` | Toolbar superior. Fondo `#1a1a2e`, border-bottom |
| `searchBox` | `QLineEdit` | Buscador. `bg-raised`, focus: border `accent` |
| `importButton` | `QPushButton` | Botones de acción (Importar, Editar tags, Identificar). `bg-raised`, border `border` |
| `importProgress` | `QProgressBar` | Barra de progreso de scan. 3px de alto, oculta por defecto |
| `librarySplitter` | `QSplitter` | Splitter horizontal árbol / tabla |
| `treeContainer` | `QWidget` | Contenedor del árbol. Fondo `#1a1a2e`, border-right |
| `libraryTree` | `QTreeWidget` | Árbol artista→álbum. Sin header, indentación 14px |
| `trackTableContainer` | `QWidget` | Contenedor de la tabla. Fondo `bg-deep` |
| `libraryContext` | `QLabel` | "Toda la biblioteca (N pistas)". `#7070a0`, 11px, fondo `#1a1a2e` |
| `trackTable` | `QTableView` | Tabla de pistas. Sin gridlines, alternating rows |

### RadioPanel (`audiorep/ui/widgets/radio_panel.py`)

| objectName | Widget | Descripción |
|---|---|---|
| `RadioPanel` | `QWidget` (raíz) | Panel de radio |
| `RadioTabs` | `QTabWidget` | Pestañas internas (Buscar / Guardadas / Favoritas) |
| `RadioSearchInput` | `QLineEdit` | Búsqueda principal, focus: border `accent` |
| `RadioCountryInput` | `QLineEdit` | Filtro por país |
| `RadioGenreInput` | `QLineEdit` | Filtro por género |
| `RadioResultsList` | `QListWidget` | Resultados de búsqueda |
| `RadioSavedList` | `QListWidget` | Emisoras guardadas |
| `RadioFavsList` | `QListWidget` | Emisoras favoritas |
| `RadioNowPlaying` | `QLabel` | Emisora en reproducción. `bg-toolbar`, color `accent` |
| `RadioBtnPlay` | `QPushButton` | Reproducir. Fondo `accent` |
| `RadioBtnStop` | `QPushButton` | Detener. Estilo secundario |
| `RadioBtnSearch` | `QPushButton` | Buscar. Fondo `accent-dim` |
| `RadioBtnSave` | `QPushButton` | Guardar emisora. Estilo secundario |
| `RadioBtnDelete` | `QPushButton` | Eliminar emisora. Estilo secundario |
| `RadioBtnFav` | `QPushButton` | Toggle favorito. Hover: color rojizo `#e06080` |

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

Por ejemplo, `importButton` se usa en el botón "Importar carpeta", "Editar tags" e "Identificar" de `LibraryPanel`. Todos comparten el mismo estilo. Esto es correcto e intencional.

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

Los diálogos (`SettingsDialog`, `TagEditorDialog`, `RipperDialog`) heredan el estilo base de `QMainWindow, QWidget { background-color: #12121e; color: #e2e2f0; }`. Los campos específicos del diálogo deben tener objectNames únicos (ej. `SettingsAcoustID`, `SettingsRipFormat`) y sus reglas en dark.qss si necesitan estilo especial.

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
