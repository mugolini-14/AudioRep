"""
CDPanel — Panel del CD físico.

Muestra el estado del disco, la lista de pistas y controles de ripeo.

Signals:
    detect_requested:          El usuario quiere detectar el CD.
    identify_requested:        El usuario quiere identificar el CD en MusicBrainz.
    play_cd_requested:         El usuario quiere reproducir todo el CD.
    play_track_requested(int): El usuario quiere reproducir una pista.
    rip_all_requested:         El usuario quiere ripear todo el CD.
    rip_track_requested(int):  El usuario quiere ripear una pista.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.cd_disc import CDDisc, RipStatus

logger = logging.getLogger(__name__)

_STATUS_ICON = {
    RipStatus.PENDING: "⬜",
    RipStatus.DONE:    "✅",
    RipStatus.ERROR:   "❌",
}


class CDPanel(QWidget):
    """Panel de control de CD."""

    detect_requested    = pyqtSignal()
    identify_requested  = pyqtSignal()
    play_cd_requested   = pyqtSignal()
    play_track_requested = pyqtSignal(int)
    rip_all_requested   = pyqtSignal()
    rip_track_requested = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cdPanel")
        self._disc: CDDisc | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Info del disco ────────────────────────────────────────── #
        info_row = QHBoxLayout()

        self._cover_label = QLabel()
        self._cover_label.setObjectName("cdCover")
        self._cover_label.setFixedSize(80, 80)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setText("💿")
        info_row.addWidget(self._cover_label)

        disc_info = QVBoxLayout()
        self._status_label = QLabel("No hay CD en la unidad.")
        self._status_label.setObjectName("cdStatus")
        disc_info.addWidget(self._status_label)

        self._album_label = QLabel("")
        self._album_label.setObjectName("cdAlbum")
        disc_info.addWidget(self._album_label)

        self._artist_label = QLabel("")
        self._artist_label.setObjectName("cdArtist")
        disc_info.addWidget(self._artist_label)
        disc_info.addStretch()
        info_row.addLayout(disc_info, stretch=1)
        layout.addLayout(info_row)

        # ── Botones de control ────────────────────────────────────── #
        btn_row = QHBoxLayout()

        detect_btn = QPushButton("🔍 Detectar")
        detect_btn.setObjectName("cdDetectBtn")
        detect_btn.clicked.connect(self.detect_requested)
        btn_row.addWidget(detect_btn)

        identify_btn = QPushButton("🌐 Identificar")
        identify_btn.setObjectName("cdIdentifyBtn")
        identify_btn.clicked.connect(self.identify_requested)
        btn_row.addWidget(identify_btn)

        play_btn = QPushButton("▶ Reproducir CD")
        play_btn.setObjectName("cdPlayBtn")
        play_btn.clicked.connect(self.play_cd_requested)
        btn_row.addWidget(play_btn)

        rip_btn = QPushButton("💾 Ripear todo")
        rip_btn.setObjectName("cdRipAllBtn")
        rip_btn.clicked.connect(self.rip_all_requested)
        btn_row.addWidget(rip_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Lista de pistas ───────────────────────────────────────── #
        self._track_list = QListWidget()
        self._track_list.setObjectName("cdTrackList")
        self._track_list.setAlternatingRowColors(True)
        self._track_list.doubleClicked.connect(self._on_track_double_clicked)
        layout.addWidget(self._track_list)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def show_no_cd(self) -> None:
        self._status_label.setText("No hay CD en la unidad.")
        self._album_label.setText("")
        self._artist_label.setText("")
        self._cover_label.setText("💿")
        self._track_list.clear()

    def show_reading(self) -> None:
        self._status_label.setText("Leyendo CD…")

    def show_disc(self, disc: CDDisc) -> None:
        self._disc = disc
        self._status_label.setText(f"Disco detectado — {len(disc.tracks)} pistas")
        self._album_label.setText(disc.album_title or "Álbum desconocido")
        self._artist_label.setText(disc.artist_name or "Artista desconocido")
        self._update_track_list(disc)

    def show_identified(self, disc: CDDisc) -> None:
        self._disc = disc
        self._status_label.setText("Disco identificado")
        self._album_label.setText(disc.album_title or "")
        self._artist_label.setText(disc.artist_name or "")
        self._update_track_list(disc)

    def update_cover(self, image_data: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            scaled = pixmap.scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cover_label.setPixmap(scaled)

    def update_track_rip_status(self, track_number: int, status: RipStatus) -> None:
        for i in range(self._track_list.count()):
            item = self._track_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == track_number:
                title = item.text().split("  ", 1)[-1]  # strip old icon
                icon  = _STATUS_ICON.get(status, "")
                item.setText(f"{icon}  {title}" if icon else title)
                break

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update_track_list(self, disc: CDDisc) -> None:
        self._track_list.clear()
        for t in disc.tracks:
            icon  = _STATUS_ICON.get(t.rip_status, "")
            label = f"{icon}  {t.number:02d}. {t.title or 'Pista ' + str(t.number)}"
            item  = QListWidgetItem(label.strip())
            item.setData(Qt.ItemDataRole.UserRole, t.number)
            self._track_list.addItem(item)

    def _on_track_double_clicked(self, index) -> None:
        item = self._track_list.item(index.row())
        if item:
            track_number = item.data(Qt.ItemDataRole.UserRole)
            self.play_track_requested.emit(track_number)
