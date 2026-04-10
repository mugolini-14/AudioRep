"""
CDPanel — Panel de gestión del CD físico.

Muestra:
    - Estado de la unidad (sin CD / leyendo / identificando / listo)
    - Portada del álbum identificado
    - Metadatos: artista, álbum, año
    - Lista de pistas con número, título, duración y estado de ripeo
    - Botones: Reproducir CD / Ripear todo / Detectar CD

Señales emitidas (el CDController las conecta):
    detect_requested()          — el usuario presionó "Detectar CD"
    play_cd_requested()         — reproducir todas las pistas del CD
    play_track_requested(int)   — reproducir pista nro. N
    rip_all_requested()         — ripear todo el disco
    rip_track_requested(int)    — ripear pista nro. N
    identify_requested()        — re-identificar el disco online
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
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

from audiorep.domain.cd_disc import CDDisc, CDTrack, RipStatus

_COVER_SIZE = 100

# Iconos de estado de ripeo
_RIP_ICONS = {
    RipStatus.PENDING:  "—",
    RipStatus.RIPPING:  "⏳",
    RipStatus.DONE:     "✓",
    RipStatus.ERROR:    "✗",
    RipStatus.SKIPPED:  "↷",
}


class CDPanel(QWidget):
    """Panel de control del CD físico."""

    detect_requested      = pyqtSignal()
    play_cd_requested     = pyqtSignal()
    play_track_requested  = pyqtSignal(int)   # track number
    rip_all_requested     = pyqtSignal()
    rip_track_requested   = pyqtSignal(int)   # track number
    identify_requested    = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._disc: CDDisc | None = None
        self._build_ui()
        self._connect_internal()
        self._show_no_cd_state()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_info_area())
        root.addWidget(self._make_separator())
        root.addWidget(self._build_track_table(), stretch=1)
        root.addWidget(self._make_separator())
        root.addWidget(self._build_action_bar())

    def _build_info_area(self) -> QWidget:
        """Portada + metadatos del disco."""
        panel = QWidget()
        panel.setObjectName("cdInfoArea")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(14)

        # Portada
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(_COVER_SIZE, _COVER_SIZE)
        self._cover_label.setObjectName("cdCover")
        self._show_cd_placeholder()

        # Metadatos
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(3)

        self._lbl_status = QLabel("Sin disco")
        self._lbl_status.setObjectName("cdStatus")

        self._lbl_album = QLabel("—")
        self._lbl_album.setObjectName("cdAlbumTitle")
        self._lbl_album.setWordWrap(True)

        self._lbl_artist = QLabel("—")
        self._lbl_artist.setObjectName("cdArtist")

        self._lbl_details = QLabel("—")
        self._lbl_details.setObjectName("cdDetails")

        self._lbl_disc_id = QLabel("")
        self._lbl_disc_id.setObjectName("cdDiscId")

        meta_layout.addWidget(self._lbl_status)
        meta_layout.addWidget(self._lbl_album)
        meta_layout.addWidget(self._lbl_artist)
        meta_layout.addWidget(self._lbl_details)
        meta_layout.addWidget(self._lbl_disc_id)
        meta_layout.addStretch()

        layout.addWidget(self._cover_label)
        layout.addLayout(meta_layout, 1)
        return panel

    def _build_track_table(self) -> QTableWidget:
        """Tabla de pistas del CD."""
        self._track_table = QTableWidget()
        self._track_table.setObjectName("cdTrackTable")
        self._track_table.setColumnCount(4)
        self._track_table.setHorizontalHeaderLabels(["#", "Título", "Duración", "Estado"])
        self._track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._track_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._track_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._track_table.setAlternatingRowColors(True)
        self._track_table.setShowGrid(False)
        self._track_table.verticalHeader().setVisible(False)

        hh = self._track_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        return self._track_table

    def _build_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("cdActionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._btn_detect = QPushButton("🔍  Detectar CD")
        self._btn_detect.setObjectName("cdButton")
        self._btn_detect.setToolTip("Buscar CD en la unidad lectora")

        self._btn_identify = QPushButton("🌐  Identificar")
        self._btn_identify.setObjectName("cdButton")
        self._btn_identify.setToolTip("Buscar información del disco en internet")
        self._btn_identify.setEnabled(False)

        self._btn_play = QPushButton("▶  Reproducir CD")
        self._btn_play.setObjectName("cdPrimaryButton")
        self._btn_play.setToolTip("Reproducir todas las pistas del CD")
        self._btn_play.setEnabled(False)

        self._btn_rip = QPushButton("💾  Ripear todo")
        self._btn_rip.setObjectName("cdButton")
        self._btn_rip.setToolTip("Extraer el CD a archivos de audio")
        self._btn_rip.setEnabled(False)

        layout.addWidget(self._btn_detect)
        layout.addWidget(self._btn_identify)
        layout.addStretch()
        layout.addWidget(self._btn_play)
        layout.addWidget(self._btn_rip)
        return bar

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        return sep

    def _connect_internal(self) -> None:
        self._btn_detect.clicked.connect(self.detect_requested)
        self._btn_identify.clicked.connect(self.identify_requested)
        self._btn_play.clicked.connect(self.play_cd_requested)
        self._btn_rip.clicked.connect(self.rip_all_requested)
        self._track_table.doubleClicked.connect(self._on_track_double_clicked)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_track_double_clicked(self, index) -> None:
        row = index.row()
        if self._disc and 0 <= row < len(self._disc.tracks):
            self.play_track_requested.emit(self._disc.tracks[row].number)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def show_no_cd(self) -> None:
        self._disc = None
        self._show_no_cd_state()

    def show_reading(self) -> None:
        """Estado: leyendo el CD (antes de saber el disc_id)."""
        self._lbl_status.setText("Leyendo CD …")
        self._lbl_album.setText("—")
        self._lbl_artist.setText("—")

    def show_disc(self, disc: CDDisc) -> None:
        """Muestra el disco leído (antes de identificar)."""
        self._disc = disc
        self._lbl_status.setText(
            "🔍 Identificando…" if not disc.identified else "💿 Disco identificado"
        )
        self._lbl_disc_id.setText(f"Disc ID: {disc.disc_id[:16]}…")
        self._update_metadata_labels(disc)
        self._populate_track_table(disc.tracks)
        self._btn_play.setEnabled(True)
        self._btn_identify.setEnabled(True)
        self._btn_rip.setEnabled(True)

    def show_identified(self, disc: CDDisc) -> None:
        """Actualiza la UI con los metadatos identificados."""
        self._disc = disc
        self._lbl_status.setText("💿 Disco identificado")
        self._update_metadata_labels(disc)
        self._populate_track_table(disc.tracks)

    def update_cover(self, image_data: bytes) -> None:
        """Actualiza la portada desde bytes de imagen."""
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            self._apply_cover(pixmap)

    def update_track_rip_status(self, track_number: int, status: RipStatus) -> None:
        """Actualiza el estado de ripeo de una pista específica."""
        for row in range(self._track_table.rowCount()):
            num_item = self._track_table.item(row, 0)
            if num_item and int(num_item.text()) == track_number:
                status_item = QTableWidgetItem(_RIP_ICONS[status])
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._track_table.setItem(row, 3, status_item)
                break

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------

    def _show_no_cd_state(self) -> None:
        self._lbl_status.setText("Sin disco en la unidad")
        self._lbl_album.setText("—")
        self._lbl_artist.setText("—")
        self._lbl_details.setText("—")
        self._lbl_disc_id.setText("")
        self._track_table.setRowCount(0)
        self._btn_play.setEnabled(False)
        self._btn_rip.setEnabled(False)
        self._btn_identify.setEnabled(False)
        self._show_cd_placeholder()

    def _update_metadata_labels(self, disc: CDDisc) -> None:
        self._lbl_album.setText(disc.album_title or "Álbum desconocido")
        self._lbl_artist.setText(disc.artist_name or "Artista desconocido")
        details_parts = []
        if disc.year:
            details_parts.append(str(disc.year))
        details_parts.append(f"{disc.track_count} pistas")
        details_parts.append(disc.total_duration_display)
        self._lbl_details.setText("  ·  ".join(details_parts))

    def _populate_track_table(self, tracks: list[CDTrack]) -> None:
        self._track_table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            items = [
                QTableWidgetItem(str(track.number)),
                QTableWidgetItem(track.title or f"Pista {track.number:02d}"),
                QTableWidgetItem(track.duration_display),
                QTableWidgetItem(_RIP_ICONS[track.rip_status]),
            ]
            alignments = [
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter,
            ]
            for col, (item, align) in enumerate(zip(items, alignments)):
                item.setTextAlignment(align)
                self._track_table.setItem(row, col, item)

    def _apply_cover(self, pixmap: QPixmap) -> None:
        scaled = pixmap.scaled(
            _COVER_SIZE, _COVER_SIZE,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (scaled.width()  - _COVER_SIZE) // 2
        y = (scaled.height() - _COVER_SIZE) // 2
        scaled = scaled.copy(x, y, _COVER_SIZE, _COVER_SIZE)

        rounded = QPixmap(_COVER_SIZE, _COVER_SIZE)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, _COVER_SIZE, _COVER_SIZE, 6, 6)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self._cover_label.setPixmap(rounded)

    def _show_cd_placeholder(self) -> None:
        pixmap = QPixmap(_COVER_SIZE, _COVER_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, _COVER_SIZE, _COVER_SIZE, 6, 6)
        painter.fillPath(path, QColor("#2a2a3e"))
        painter.setPen(QColor("#555577"))
        font = painter.font()
        font.setPointSize(36)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "💿")
        painter.end()
        self._cover_label.setPixmap(pixmap)
