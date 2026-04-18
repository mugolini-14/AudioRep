"""
CDPanel — Panel del CD físico.

Muestra el estado del disco, selector de lectora, lista de pistas y controles.

Layout:
    [Lectora:] [drive_combo] [status] [disc_info ── stretch ──]
    [Tabla de pistas (expande)]
    [Detectar ──] [Identificar ──] [▶ Reproducir CD ──] [Ripear todo ──]

Signals:
    detect_requested:           El usuario quiere detectar el CD.
    identify_requested:         El usuario quiere identificar el CD en MusicBrainz.
    play_cd_requested:          El usuario quiere reproducir todo el CD.
    play_track_requested(int):  El usuario quiere reproducir una pista.
    rip_all_requested:          El usuario quiere ripear todo el CD.
    rip_track_requested(int):   El usuario quiere ripear una pista.
    drive_changed(str):         El usuario cambió la lectora seleccionada.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.cd_disc import CDDisc, RipStatus

logger = logging.getLogger(__name__)

_STATUS_ICON = {
    RipStatus.PENDING: "",
    RipStatus.DONE:    "✔",
    RipStatus.ERROR:   "✖",
}

_COL_NUM    = 0
_COL_TITLE  = 1
_COL_STATUS = 2


class CDPanel(QWidget):
    """Panel de control de CD."""

    detect_requested     = pyqtSignal()
    identify_requested   = pyqtSignal()
    play_cd_requested    = pyqtSignal()
    play_track_requested = pyqtSignal(int)
    rip_all_requested    = pyqtSignal()
    rip_track_requested  = pyqtSignal(int)
    drive_changed        = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cdPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._disc: CDDisc | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Fila única: lectora + estado + info del disco ─────────── #
        drive_row = QHBoxLayout()
        drive_row.setSpacing(8)

        drive_label = QLabel("Lectora:")
        drive_label.setObjectName("cdDriveLabel")
        drive_label.setFixedWidth(52)
        drive_row.addWidget(drive_label)

        self._drive_combo = QComboBox()
        self._drive_combo.setObjectName("cdDriveCombo")
        self._drive_combo.setToolTip("Seleccionar unidad de CD")
        self._drive_combo.setFixedWidth(120)
        self._drive_combo.currentTextChanged.connect(self._on_drive_changed)
        drive_row.addWidget(self._drive_combo)

        self._status_label = QLabel("No hay CD en la unidad.")
        self._status_label.setObjectName("cdStatus")
        drive_row.addWidget(self._status_label)

        self._disc_info_label = QLabel("Sin información.")
        self._disc_info_label.setObjectName("cdDiscInfo")
        self._disc_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        drive_row.addWidget(self._disc_info_label, stretch=1)

        layout.addLayout(drive_row)

        # ── Tabla de pistas ───────────────────────────────────────── #
        self._track_table = QTableWidget()
        self._track_table.setObjectName("cdTrackTable")
        self._track_table.setColumnCount(3)
        self._track_table.setHorizontalHeaderLabels(["#", "Título", ""])
        self._track_table.setAlternatingRowColors(True)
        self._track_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._track_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._track_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._track_table.verticalHeader().setVisible(False)
        self._track_table.setShowGrid(False)
        self._track_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Columnas: # fijo, Título expansible, Estado fijo
        header = self._track_table.horizontalHeader()
        header.setSectionResizeMode(_COL_NUM,    QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_TITLE,  QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_STATUS, QHeaderView.ResizeMode.Fixed)
        self._track_table.setColumnWidth(_COL_NUM,    36)
        self._track_table.setColumnWidth(_COL_STATUS, 32)

        self._track_table.doubleClicked.connect(self._on_track_double_clicked)
        layout.addWidget(self._track_table, stretch=1)

        # ── Botones de control ────────────────────────────────────── #
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        detect_btn = QPushButton("🔍 Detectar")
        detect_btn.setObjectName("cdDetectBtn")
        detect_btn.clicked.connect(self.detect_requested)
        btn_row.addWidget(detect_btn, stretch=1)

        identify_btn = QPushButton("🌐 Identificar")
        identify_btn.setObjectName("cdIdentifyBtn")
        identify_btn.clicked.connect(self.identify_requested)
        btn_row.addWidget(identify_btn, stretch=1)

        play_btn = QPushButton("▶ Reproducir CD")
        play_btn.setObjectName("cdPlayBtn")
        play_btn.clicked.connect(self.play_cd_requested)
        btn_row.addWidget(play_btn, stretch=1)

        rip_btn = QPushButton("💾 Ripear todo")
        rip_btn.setObjectName("cdRipAllBtn")
        rip_btn.clicked.connect(self.rip_all_requested)
        btn_row.addWidget(rip_btn, stretch=1)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_drives(self, drives: list[str]) -> None:
        """Puebla el selector con las lectoras disponibles."""
        self._drive_combo.blockSignals(True)
        self._drive_combo.clear()
        for drive in drives:
            self._drive_combo.addItem(drive)
        self._drive_combo.blockSignals(False)
        if drives:
            self.drive_changed.emit(drives[0])

    def current_drive(self) -> str:
        """Retorna la lectora seleccionada actualmente."""
        return self._drive_combo.currentText()

    def show_no_cd(self) -> None:
        self._status_label.setText("No hay CD en la unidad.")
        self._disc_info_label.setText("Sin información.")
        self._track_table.setRowCount(0)

    def show_reading(self) -> None:
        self._status_label.setText("Leyendo CD…")

    def show_disc(self, disc: CDDisc) -> None:
        self._disc = disc
        self._status_label.setText(f"Disco detectado  ·  {len(disc.tracks)} pistas")
        self._disc_info_label.setText(self._format_disc_info(disc))
        self._update_track_table(disc)

    def show_identified(self, disc: CDDisc) -> None:
        self._disc = disc
        self._status_label.setText("Disco identificado")
        self._disc_info_label.setText(self._format_disc_info(disc))
        self._update_track_table(disc)

    def update_cover(self, image_data: bytes) -> None:
        """No-op: la portada se muestra en el panel NowPlaying."""

    @staticmethod
    def _format_disc_info(disc: CDDisc) -> str:
        artist = disc.artist_name or "Artista desconocido"
        album  = disc.album_title  or "Álbum desconocido"
        year   = f"  ({disc.year})" if disc.year else ""
        return f"{artist}  —  {album}{year}"

    def update_track_rip_status(self, track_number: int, status: RipStatus) -> None:
        for row in range(self._track_table.rowCount()):
            num_item = self._track_table.item(row, _COL_NUM)
            if num_item and num_item.data(Qt.ItemDataRole.UserRole) == track_number:
                icon = _STATUS_ICON.get(status, "")
                status_item = QTableWidgetItem(icon)
                status_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                self._track_table.setItem(row, _COL_STATUS, status_item)
                break

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update_track_table(self, disc: CDDisc) -> None:
        self._track_table.setRowCount(0)
        self._track_table.setRowCount(len(disc.tracks))
        for row, t in enumerate(disc.tracks):
            # Columna #
            num_item = QTableWidgetItem(f"{t.number:02d}")
            num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            num_item.setData(Qt.ItemDataRole.UserRole, t.number)
            self._track_table.setItem(row, _COL_NUM, num_item)

            # Columna Título
            title_item = QTableWidgetItem(t.title or f"Pista {t.number}")
            title_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self._track_table.setItem(row, _COL_TITLE, title_item)

            # Columna Estado
            icon = _STATUS_ICON.get(t.rip_status, "")
            status_item = QTableWidgetItem(icon)
            status_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._track_table.setItem(row, _COL_STATUS, status_item)

        self._track_table.resizeRowsToContents()

    def _on_track_double_clicked(self, index) -> None:
        num_item = self._track_table.item(index.row(), _COL_NUM)
        if num_item:
            track_number = num_item.data(Qt.ItemDataRole.UserRole)
            self.play_track_requested.emit(track_number)

    def _on_drive_changed(self, drive: str) -> None:
        if drive:
            self.drive_changed.emit(drive)
