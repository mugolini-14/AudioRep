"""
LibraryPanel — Panel principal de la biblioteca musical.

Layout:
    ┌──────────────────────────────────────────────────────┐
    │  [📂 Importar]  [___ Buscar ___________________] [🔍] │  ← toolbar
    ├───────────────┬──────────────────────────────────────┤
    │  Árbol        │  Tabla de pistas                     │
    │  ▶ Toda la    │  #  Título  Artista  Álbum  Dur.     │
    │    música     │  ─────────────────────────────────── │
    │  ▸ Artista 1  │  1  ...     ...      ...    3:21     │
    │    ▸ Álbum 1  │  2  ...     ...      ...    4:15     │
    │  ▸ Artista 2  │  ...                                 │
    └───────────────┴──────────────────────────────────────┘

Señales emitidas (el LibraryController las conecta):
    import_requested(str)           — el usuario eligió una carpeta a importar
    track_double_clicked(Track)     — el usuario hizo doble clic en una pista
    artist_selected(int)            — se seleccionó un artista (artist_id)
    album_selected(int)             — se seleccionó un álbum (album_id)
    all_music_selected()            — se seleccionó "Toda la música"
    search_changed(str)             — cambió el texto del buscador
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QProgressBar,
)

from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.track import Track
from audiorep.ui.qt_models.track_table_model import (
    TrackTableModel,
    TrackRole,
    make_track_proxy_model,
)

# IDs de tipo para los nodos del árbol
_TYPE_ALL    = 0
_TYPE_ARTIST = 1
_TYPE_ALBUM  = 2


class LibraryPanel(QWidget):
    """Panel de navegación y exploración de la biblioteca."""

    import_requested      = pyqtSignal(str)    # directorio elegido
    track_double_clicked  = pyqtSignal(object) # Track
    artist_selected       = pyqtSignal(int)    # artist_id
    album_selected        = pyqtSignal(int)    # album_id
    all_music_selected    = pyqtSignal()
    search_changed        = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._track_model = TrackTableModel(self)
        self._proxy_model = make_track_proxy_model(self._track_model)
        self._build_ui()
        self._connect_internal()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_progress_bar())
        root.addWidget(self._build_splitter(), stretch=1)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("libraryToolbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self._btn_import = QPushButton("📂  Importar carpeta")
        self._btn_import.setObjectName("importButton")
        self._btn_import.setToolTip("Agregar una carpeta a la biblioteca")

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Buscar artista, álbum o pista…")
        self._search_box.setObjectName("searchBox")
        self._search_box.setClearButtonEnabled(True)

        layout.addWidget(self._btn_import)
        layout.addWidget(self._search_box, 1)
        return bar

    def _build_progress_bar(self) -> QProgressBar:
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("importProgress")
        self._progress_bar.setMaximumHeight(3)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.hide()
        return self._progress_bar

    def _build_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("librarySplitter")
        splitter.setHandleWidth(1)

        splitter.addWidget(self._build_tree())
        splitter.addWidget(self._build_track_table())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 600])
        return splitter

    def _build_tree(self) -> QWidget:
        container = QWidget()
        container.setObjectName("treeContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setObjectName("libraryTree")
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(16)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)

        # Nodo raíz "Toda la música"
        self._item_all = QTreeWidgetItem(self._tree, ["🎵  Toda la música"])
        self._item_all.setData(0, Qt.ItemDataRole.UserRole, (_TYPE_ALL, None))
        self._tree.addTopLevelItem(self._item_all)
        self._tree.setCurrentItem(self._item_all)

        layout.addWidget(self._tree)
        return container

    def _build_track_table(self) -> QWidget:
        container = QWidget()
        container.setObjectName("trackTableContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Etiqueta de contexto (ej. "Artista: Pink Floyd — 42 pistas")
        self._lbl_context = QLabel("")
        self._lbl_context.setObjectName("libraryContext")
        self._lbl_context.setContentsMargins(10, 4, 10, 4)

        self._table = QTableView()
        self._table.setObjectName("trackTable")
        self._table.setModel(self._proxy_model)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSortIndicatorShown(True)
        self._table.setShowGrid(False)

        # Ancho de columnas
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # #
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)            # Título
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)        # Artista
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)        # Álbum
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Duración
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Año
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)        # Género
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # ★

        # Anchos iniciales de columnas interactivas
        self._table.setColumnWidth(2, 160)
        self._table.setColumnWidth(3, 160)
        self._table.setColumnWidth(6, 100)

        layout.addWidget(self._lbl_context)
        layout.addWidget(self._table)
        return container

    def _connect_internal(self) -> None:
        self._btn_import.clicked.connect(self._on_import_clicked)
        self._search_box.textChanged.connect(self._on_search_changed)
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self._table.doubleClicked.connect(self._on_table_double_clicked)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_import_clicked(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de música",
            "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if directory:
            self.import_requested.emit(directory)

    def _on_search_changed(self, text: str) -> None:
        self._proxy_model.setFilterFixedString(text)
        self.search_changed.emit(text)

    def _on_tree_selection_changed(
        self,
        current: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ) -> None:
        if current is None:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        node_type, node_id = data
        if node_type == _TYPE_ALL:
            self.all_music_selected.emit()
        elif node_type == _TYPE_ARTIST:
            self.artist_selected.emit(node_id)
        elif node_type == _TYPE_ALBUM:
            self.album_selected.emit(node_id)

    def _on_table_double_clicked(self, index) -> None:
        source_index = self._proxy_model.mapToSource(index)
        track = self._track_model.track_at(source_index.row())
        if track:
            self.track_double_clicked.emit(track)

    # ------------------------------------------------------------------
    # API pública — actualización desde el Controller
    # ------------------------------------------------------------------

    def populate_tree(self, artists: list[Artist], albums_by_artist: dict[int, list[Album]]) -> None:
        """Rellena el árbol con artistas y sus álbumes."""
        # Conservar el nodo "Toda la música" y limpiar el resto
        while self._tree.topLevelItemCount() > 1:
            self._tree.takeTopLevelItem(1)

        for artist in artists:
            artist_item = QTreeWidgetItem([f"🎤  {artist.name}"])
            artist_item.setData(0, Qt.ItemDataRole.UserRole, (_TYPE_ARTIST, artist.id))

            for album in albums_by_artist.get(artist.id or -1, []):
                year_str = f" ({album.year})" if album.year else ""
                album_item = QTreeWidgetItem([f"💿  {album.title}{year_str}"])
                album_item.setData(0, Qt.ItemDataRole.UserRole, (_TYPE_ALBUM, album.id))
                artist_item.addChild(album_item)

            self._tree.addTopLevelItem(artist_item)

    def set_tracks(self, tracks: list[Track], context_label: str = "") -> None:
        """Actualiza la tabla de pistas."""
        self._track_model.set_tracks(tracks)
        self._lbl_context.setText(context_label)
        count = len(tracks)
        suffix = f"  —  {count} pista{'s' if count != 1 else ''}" if context_label else ""
        self._lbl_context.setText(f"{context_label}{suffix}")

    def append_track(self, track: Track) -> None:
        """Agrega una pista sin resetear la tabla (usado durante la importación)."""
        self._track_model.append_track(track)

    def show_import_progress(self, current: int, total: int) -> None:
        """Muestra o actualiza la barra de progreso de importación."""
        if total <= 0:
            self._progress_bar.hide()
            return
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._progress_bar.show()
        if current >= total:
            self._progress_bar.hide()

    def get_selected_tracks(self) -> list[Track]:
        """Retorna las pistas actualmente seleccionadas en la tabla."""
        tracks: list[Track] = []
        for proxy_index in self._table.selectedIndexes():
            if proxy_index.column() != 0:
                continue
            source_index = self._proxy_model.mapToSource(proxy_index)
            track = self._track_model.track_at(source_index.row())
            if track:
                tracks.append(track)
        return tracks
