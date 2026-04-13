"""
LibraryPanel — Panel de la biblioteca musical.

Muestra una tabla de pistas con buscador y botones de acción.

Signals:
    import_requested:    El usuario quiere importar un directorio.
    play_requested(list[Track], int): El usuario quiere reproducir (cola, índice).
    search_changed(str): El texto de búsqueda cambió.
    edit_tags_requested(Track): El usuario quiere editar tags.
    identify_requested(Track):  El usuario quiere identificar por huella.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.track import Track
from audiorep.ui.qt_models.track_table_model import TrackTableModel


class LibraryPanel(QWidget):
    """Panel de la biblioteca musical."""

    import_requested   = pyqtSignal()
    play_requested     = pyqtSignal(list, int)
    search_changed     = pyqtSignal(str)
    edit_tags_requested  = pyqtSignal(object)  # Track
    identify_requested   = pyqtSignal(object)  # Track

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("libraryPanel")
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Toolbar ─────────────────────────────────────────────── #
        toolbar = QHBoxLayout()

        self._search_edit = QLineEdit()
        self._search_edit.setObjectName("librarySearch")
        self._search_edit.setPlaceholderText("Buscar pistas…")
        self._search_edit.textChanged.connect(self.search_changed)
        toolbar.addWidget(self._search_edit, stretch=1)

        import_btn = QPushButton("Importar carpeta")
        import_btn.setObjectName("libraryImportBtn")
        import_btn.clicked.connect(self.import_requested)
        toolbar.addWidget(import_btn)

        layout.addLayout(toolbar)

        # ── Progreso de escaneo ──────────────────────────────────── #
        self._progress = QProgressBar()
        self._progress.setObjectName("libraryScanProgress")
        self._progress.setVisible(False)
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        # ── Tabla ────────────────────────────────────────────────── #
        self._model = TrackTableModel()
        self._table = QTableView()
        self._table.setObjectName("libraryTable")
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch  # título
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # ── Barra de info ─────────────────────────────────────────── #
        self._count_label = QLabel("0 pistas")
        self._count_label.setObjectName("libraryCountLabel")
        layout.addWidget(self._count_label)

        # ── Botones de acción ─────────────────────────────────────── #
        action_bar = QHBoxLayout()
        play_btn = QPushButton("▶  Reproducir selección")
        play_btn.setObjectName("libraryPlayBtn")
        play_btn.clicked.connect(self._on_play_selection)
        action_bar.addWidget(play_btn)

        edit_btn = QPushButton("✏  Editar tags")
        edit_btn.setObjectName("libraryEditBtn")
        edit_btn.clicked.connect(self._on_edit_tags)
        action_bar.addWidget(edit_btn)

        identify_btn = QPushButton("🔍  Identificar")
        identify_btn.setObjectName("libraryIdentifyBtn")
        identify_btn.clicked.connect(self._on_identify)
        action_bar.addWidget(identify_btn)

        action_bar.addStretch()
        layout.addLayout(action_bar)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[Track]) -> None:
        self._model.set_tracks(tracks)
        self._count_label.setText(f"{len(tracks)} pistas")

    def set_scan_progress(self, processed: int, total: int) -> None:
        if total > 0:
            self._progress.setVisible(True)
            self._progress.setRange(0, total)
            self._progress.setValue(processed)
            if processed >= total:
                self._progress.setVisible(False)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_double_click(self, index) -> None:
        row = index.row()
        tracks = self._model.all_tracks()
        self.play_requested.emit(tracks, row)

    def _on_play_selection(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
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
