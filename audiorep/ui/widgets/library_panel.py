"""
LibraryPanel — Panel de la biblioteca musical.

Layout: árbol Artistas/Álbumes (izquierda) + tabla de pistas (derecha).
En modo estadísticas, la vista se reemplaza por StatsPanel.

objectNames alineados con dark.qss:
    libraryPanel, libraryToolbar, importButton, searchBox,
    libraryStatsBtn, libraryExportLibBtn, libraryExportStatsBtn,
    treeContainer, libraryTree,
    trackTableContainer, libraryContext, trackTable,
    importProgress

Signals:
    import_requested:              El usuario quiere importar un directorio.
    play_requested(list, int):     El usuario quiere reproducir (cola, índice).
    search_changed(str):           El texto de búsqueda cambió.
    edit_tags_requested(Track):
    identify_requested(Track):
    stats_requested:               El usuario quiere ver/calcular estadísticas.
    export_library_requested:      El usuario quiere exportar solo la lista de pistas.
    export_stats_requested:        El usuario quiere exportar solo las estadísticas.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.track import Track
from audiorep.services.stats_service import LibraryStats
from audiorep.ui.qt_models.track_table_model import TrackTableModel
from audiorep.ui.widgets.stats_panel import StatsPanel


class LibraryPanel(QWidget):
    """Panel de la biblioteca musical con árbol artista/álbum."""

    import_requested     = pyqtSignal()
    reimport_requested   = pyqtSignal()
    play_requested       = pyqtSignal(list, int)
    search_changed       = pyqtSignal(str)
    edit_tags_requested  = pyqtSignal(object)   # Track
    identify_requested   = pyqtSignal(object)   # Track
    stats_requested          = pyqtSignal()
    export_library_requested = pyqtSignal()
    export_stats_requested   = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("libraryPanel")
        self._all_tracks: list[Track] = []
        self._in_stats_mode = False
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────── #
        toolbar = QWidget()
        toolbar.setObjectName("libraryToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("searchBox")
        self._search_edit.setPlaceholderText("Buscar pistas, artistas, álbumes…")
        self._search_edit.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self._search_edit, stretch=1)

        self._stats_btn = QPushButton("📊  Estadísticas")
        self._stats_btn.setObjectName("libraryStatsBtn")
        self._stats_btn.setCheckable(True)
        self._stats_btn.clicked.connect(self._on_stats_toggled)
        toolbar_layout.addWidget(self._stats_btn)

        import_btn = QPushButton("Importar carpeta")
        import_btn.setObjectName("importButton")
        import_menu = QMenu(import_btn)
        import_menu.addAction("Agregar carpeta",
                              lambda: self.import_requested.emit())
        import_menu.addSeparator()
        import_menu.addAction("Limpiar biblioteca y reimportar…",
                              lambda: self.reimport_requested.emit())
        import_btn.setMenu(import_menu)
        toolbar_layout.addWidget(import_btn)

        export_lib_btn = QPushButton("⬇  Exportar Biblioteca")
        export_lib_btn.setObjectName("libraryExportLibBtn")
        export_lib_btn.clicked.connect(self.export_library_requested)
        toolbar_layout.addWidget(export_lib_btn)

        export_stats_btn = QPushButton("📈  Exportar Estadísticas")
        export_stats_btn.setObjectName("libraryExportStatsBtn")
        export_stats_btn.clicked.connect(self.export_stats_requested)
        toolbar_layout.addWidget(export_stats_btn)

        layout.addWidget(toolbar)

        # ── Barra de progreso de importación ─────────────────────── #
        self._progress = QProgressBar()
        self._progress.setObjectName("importProgress")
        self._progress.setVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(3)
        layout.addWidget(self._progress)

        # ── Stack principal: biblioteca | estadísticas ────────────── #
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        # Página 0: Splitter biblioteca
        self._library_page = self._build_library_page()
        self._stack.addWidget(self._library_page)

        # Página 1: Panel de estadísticas
        self._stats_panel = StatsPanel()
        self._stack.addWidget(self._stats_panel)

        self._stack.setCurrentIndex(0)

    def _build_library_page(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("librarySplitter")
        splitter.setHandleWidth(1)

        # Árbol
        tree_container = QWidget()
        tree_container.setObjectName("treeContainer")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setObjectName("libraryTree")
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(14)
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        tree_layout.addWidget(self._tree)
        splitter.addWidget(tree_container)

        # Tabla
        table_container = QWidget()
        table_container.setObjectName("trackTableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self._context_label = QLabel("Toda la biblioteca")
        self._context_label.setObjectName("libraryContext")
        self._context_label.setContentsMargins(8, 4, 8, 4)
        table_layout.addWidget(self._context_label)

        self._model = TrackTableModel()
        self._table = QTableView()
        self._table.setObjectName("trackTable")
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.doubleClicked.connect(self._on_double_click)
        table_layout.addWidget(self._table)

        # Botones de acción
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(8, 8, 8, 8)
        action_bar.setSpacing(8)

        edit_btn = QPushButton("✏  Editar tags")
        edit_btn.setObjectName("libraryEditBtn")
        edit_btn.clicked.connect(self._on_edit_tags)
        action_bar.addWidget(edit_btn, stretch=1)

        identify_btn = QPushButton("🔍  Identificar")
        identify_btn.setObjectName("libraryIdentifyBtn")
        identify_btn.clicked.connect(self._on_identify)
        action_bar.addWidget(identify_btn, stretch=1)
        table_layout.addLayout(action_bar)

        splitter.addWidget(table_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 600])

        return splitter

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[Track]) -> None:
        self._all_tracks = tracks
        self._rebuild_tree(tracks)
        self._model.set_tracks(tracks)
        self._context_label.setText(f"Toda la biblioteca  ({len(tracks)} pistas)")

    def get_all_tracks(self) -> list[Track]:
        return self._all_tracks

    def set_scan_progress(self, processed: int, total: int) -> None:
        if total > 0:
            self._progress.setVisible(True)
            self._progress.setRange(0, total)
            self._progress.setValue(processed)
            if processed >= total:
                self._progress.setVisible(False)

    def show_stats_loading(self) -> None:
        self._stats_panel.show_loading()

    def set_stats(self, stats: LibraryStats) -> None:
        self._stats_panel.load(stats)

    # ------------------------------------------------------------------
    # Árbol
    # ------------------------------------------------------------------

    def _rebuild_tree(self, tracks: list[Track]) -> None:
        self._tree.blockSignals(True)
        self._tree.clear()

        all_item = QTreeWidgetItem(["Toda la biblioteca"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, None)
        self._tree.addTopLevelItem(all_item)

        artists: dict[str, dict[str, list[Track]]] = {}
        for t in tracks:
            artist = t.artist_name or "Artista desconocido"
            album  = t.album_title  or "Álbum desconocido"
            artists.setdefault(artist, {}).setdefault(album, []).append(t)

        for artist_name in sorted(artists):
            artist_item = QTreeWidgetItem([artist_name])
            artist_item.setData(0, Qt.ItemDataRole.UserRole, ("artist", artist_name))
            for album_name in sorted(artists[artist_name]):
                album_item = QTreeWidgetItem([album_name])
                album_item.setData(0, Qt.ItemDataRole.UserRole, ("album", artist_name, album_name))
                artist_item.addChild(album_item)
            self._tree.addTopLevelItem(artist_item)

        self._tree.setCurrentItem(all_item)
        self._tree.blockSignals(False)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_stats_toggled(self, checked: bool) -> None:
        self._in_stats_mode = checked
        if checked:
            self._stack.setCurrentIndex(1)
            self._stats_panel.show_loading()
            self.stats_requested.emit()
        else:
            self._stack.setCurrentIndex(0)

    def _on_tree_selection(self, current: QTreeWidgetItem | None, _) -> None:
        if current is None:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            filtered = self._all_tracks
            self._context_label.setText(f"Toda la biblioteca  ({len(filtered)} pistas)")
        elif data[0] == "artist":
            artist_name = data[1]
            filtered = [t for t in self._all_tracks if (t.artist_name or "Artista desconocido") == artist_name]
            self._context_label.setText(f"{artist_name}  ({len(filtered)} pistas)")
        else:
            _, artist_name, album_name = data
            filtered = [
                t for t in self._all_tracks
                if (t.artist_name or "Artista desconocido") == artist_name
                and (t.album_title or "Álbum desconocido") == album_name
            ]
            self._context_label.setText(f"{artist_name}  /  {album_name}  ({len(filtered)} pistas)")
        self._model.set_tracks(filtered)

    def _on_search_changed(self, query: str) -> None:
        self.search_changed.emit(query)
        if query.strip():
            filtered = [
                t for t in self._all_tracks
                if query.lower() in (t.title or "").lower()
                or query.lower() in (t.artist_name or "").lower()
                or query.lower() in (t.album_title or "").lower()
            ]
            self._model.set_tracks(filtered)
            self._context_label.setText(f"Búsqueda: \"{query}\"  ({len(filtered)} pistas)")
        else:
            self._on_tree_selection(self._tree.currentItem(), None)

    def _on_double_click(self, index) -> None:
        row = index.row()
        tracks = self._model.all_tracks()
        self.play_requested.emit(tracks, row)

    def _on_edit_tags(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        track = self._model.track_at(rows[0].row())
        if track:
            self.edit_tags_requested.emit(track)

    def _on_identify(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        track = self._model.track_at(rows[0].row())
        if track:
            self.identify_requested.emit(track)
