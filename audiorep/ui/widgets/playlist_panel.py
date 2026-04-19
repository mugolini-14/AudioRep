"""
PlaylistPanel — Panel de gestión de playlists.

Layout: lista de playlists a la izquierda, tabla de pistas a la derecha.

Signals:
    playlist_selected(Playlist):     El usuario selecciono una playlist.
    play_requested(Playlist):        El usuario quiere reproducir la playlist.
    create_requested(str):           El usuario quiere crear una playlist con nombre.
    rename_requested(int, str):      El usuario quiere renombrar (id, nuevo_nombre).
    delete_requested(int):           El usuario quiere eliminar la playlist.
    add_track_requested(int, int):   El usuario quiere aniadir pista (playlist_id, track_id).
    remove_track_requested(int, int): El usuario quiere quitar pista (playlist_id, track_id).
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.playlist import Playlist
from audiorep.domain.track import Track
from audiorep.ui.qt_models.track_table_model import TrackTableModel

logger = logging.getLogger(__name__)


class PlaylistPanel(QWidget):
    """Panel de playlists."""

    playlist_selected      = pyqtSignal(object)      # Playlist
    play_requested         = pyqtSignal(object, int) # Playlist, start_index
    create_requested       = pyqtSignal(str)
    rename_requested       = pyqtSignal(int, str)
    delete_requested       = pyqtSignal(int)
    add_track_requested    = pyqtSignal(int, int)
    remove_track_requested = pyqtSignal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playlistPanel")
        self._playlists: list[Playlist] = []
        self._current_playlist: Playlist | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("playlistSplitter")

        # Left: playlist list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)
        left_layout.setSpacing(4)

        self._playlist_list = QListWidget()
        self._playlist_list.setObjectName("playlistList")
        self._playlist_list.currentItemChanged.connect(self._on_playlist_selected)
        left_layout.addWidget(self._playlist_list)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("Nuevo")
        new_btn.setObjectName("playlistNewBtn")
        new_btn.clicked.connect(self._on_new_playlist)
        btn_row.addWidget(new_btn)

        rename_btn = QPushButton("Renombrar")
        rename_btn.setObjectName("playlistRenameBtn")
        rename_btn.clicked.connect(self._on_rename)
        btn_row.addWidget(rename_btn)

        del_btn = QPushButton("Eliminar")
        del_btn.setObjectName("playlistDeleteBtn")
        del_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)

        # Right: track table
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)
        right_layout.setSpacing(4)

        self._track_model = TrackTableModel()
        self._track_table = QTableView()
        self._track_table.setObjectName("trackTable")
        self._track_table.setModel(self._track_model)
        self._track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._track_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._track_table.setAlternatingRowColors(True)
        self._track_table.verticalHeader().setVisible(False)
        self._track_table.horizontalHeader().setStretchLastSection(True)
        self._track_table.setSortingEnabled(True)
        self._track_table.doubleClicked.connect(self._on_track_double_clicked)
        right_layout.addWidget(self._track_table)

        action_row = QHBoxLayout()
        play_btn = QPushButton("Reproducir")
        play_btn.setObjectName("playlistPlayBtn")
        play_btn.clicked.connect(self._on_play)
        action_row.addWidget(play_btn, stretch=1)

        remove_btn = QPushButton("Quitar pista")
        remove_btn.setObjectName("playlistRemoveBtn")
        remove_btn.clicked.connect(self._on_remove_track)
        action_row.addWidget(remove_btn, stretch=1)
        right_layout.addLayout(action_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([180, 500])
        layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    @property
    def current_playlist(self) -> Playlist | None:
        return self._current_playlist

    def set_playlists(self, playlists: list[Playlist]) -> None:
        self._playlists = playlists
        current_id = self._current_playlist.id if self._current_playlist else None
        self._playlist_list.blockSignals(True)
        self._playlist_list.clear()
        new_row = 0
        for i, pl in enumerate(playlists):
            prefix = "* " if pl.is_smart else ""
            item = QListWidgetItem(f"{prefix}{pl.name}")
            item.setData(Qt.ItemDataRole.UserRole, pl)
            self._playlist_list.addItem(item)
            if pl.id == current_id:
                new_row = i
        self._playlist_list.blockSignals(False)
        if playlists:
            self._playlist_list.setCurrentRow(new_row)

    def set_playlist_tracks(self, tracks: list[Track]) -> None:
        self._track_model.set_tracks(tracks)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_playlist_selected(self, current: QListWidgetItem | None, _) -> None:
        if current is None:
            return
        playlist: Playlist = current.data(Qt.ItemDataRole.UserRole)
        self._current_playlist = playlist
        self.playlist_selected.emit(playlist)

    def _on_play(self) -> None:
        if self._current_playlist:
            self.play_requested.emit(self._current_playlist, 0)

    def _on_new_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "Nueva playlist", "Nombre:")
        if ok and name.strip():
            self.create_requested.emit(name.strip())

    def _on_rename(self) -> None:
        if self._current_playlist is None:
            return
        name, ok = QInputDialog.getText(
            self, "Renombrar playlist", "Nuevo nombre:",
            text=self._current_playlist.name,
        )
        if ok and name.strip() and self._current_playlist.id is not None:
            self.rename_requested.emit(self._current_playlist.id, name.strip())

    def _on_delete(self) -> None:
        if self._current_playlist is None:
            return
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"Eliminar la playlist {self._current_playlist.name!r}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._current_playlist.id is not None:
            self.delete_requested.emit(self._current_playlist.id)

    def _on_track_double_clicked(self, index) -> None:
        if self._current_playlist:
            self.play_requested.emit(self._current_playlist, index.row())

    def _on_remove_track(self) -> None:
        if self._current_playlist is None or self._current_playlist.id is None:
            return
        rows = self._track_table.selectionModel().selectedRows()
        if not rows:
            return
        track = self._track_model.track_at(rows[0].row())
        if track and track.id is not None:
            self.remove_track_requested.emit(self._current_playlist.id, track.id)
