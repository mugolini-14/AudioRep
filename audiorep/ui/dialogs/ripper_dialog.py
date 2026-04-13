"""
RipperDialog — Diálogo de progreso de ripeo de CD.

Muestra el progreso en tiempo real mientras se ripean las pistas.
Se conecta a app_events de rip_progress, rip_track_done, rip_track_error, rip_finished.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from audiorep.core.events import app_events
from audiorep.domain.cd_disc import CDDisc

logger = logging.getLogger(__name__)


class RipperDialog(QDialog):
    """
    Diálogo de progreso de ripeo.

    Args:
        ripper_service: RipperService activo.
        disc:           Disco que se está ripeando.
        parent:         Widget padre.
    """

    def __init__(
        self,
        ripper_service: object,
        disc: CDDisc,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._disc = disc
        self._finished = False

        self.setWindowTitle("Ripeando CD…")
        self.setMinimumWidth(400)
        self.setModal(False)
        self.setObjectName("RipperDialog")

        layout = QVBoxLayout(self)

        album  = disc.album_title or "CD"
        artist = disc.artist_name or "Desconocido"
        self._title_label = QLabel(f"<b>{artist}</b> — {album}")
        self._title_label.setObjectName("RipperDialogTitle")
        layout.addWidget(self._title_label)

        self._track_label = QLabel("Preparando…")
        self._track_label.setObjectName("RipperDialogTrack")
        layout.addWidget(self._track_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setObjectName("RipperDialogProgress")
        layout.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setObjectName("RipperDialogLog")
        layout.addWidget(self._log)

        self._close_btn = QPushButton("Cerrar")
        self._close_btn.setObjectName("RipperDialogClose")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.accept)
        layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._connect_events()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def _connect_events(self) -> None:
        app_events.rip_progress.connect(self._on_progress)
        app_events.rip_track_done.connect(self._on_track_done)
        app_events.rip_track_error.connect(self._on_track_error)
        app_events.rip_finished.connect(self._on_finished)

    def _on_progress(self, current: int, total: int, percent: int) -> None:
        self._track_label.setText(f"Pista {current} de {total}")
        if percent > 0:
            self._progress.setValue(percent)
        else:
            overall = int((current - 1) / total * 100)
            self._progress.setValue(overall)

    def _on_track_done(self, track_number: int, path: str) -> None:
        self._log.append(f"✓ Pista {track_number}: {path}")

    def _on_track_error(self, track_number: int, message: str) -> None:
        self._log.append(f"✗ Pista {track_number}: {message}")

    def _on_finished(self) -> None:
        self._track_label.setText("¡Ripeo completado!")
        self._progress.setValue(100)
        self._close_btn.setEnabled(True)
        self._finished = True
        logger.info("Ripeo completado.")
