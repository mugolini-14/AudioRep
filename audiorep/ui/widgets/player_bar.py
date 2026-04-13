"""
PlayerBar — Barra inferior de controles de reproducción.

Controles: anterior, play/pause, siguiente, stop, barra de progreso, volumen.

Signals:
    play_pause_clicked: Botón de play/pause presionado.
    stop_clicked:       Botón de stop presionado.
    next_clicked:       Botón de siguiente presionado.
    previous_clicked:   Botón de anterior presionado.
    seek_requested(int): Barra de progreso arrastrada (posición en ms).
    volume_changed(int): Deslizador de volumen cambiado (0–100).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from audiorep.domain.track import Track


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class PlayerBar(QWidget):
    """Barra de controles de reproducción."""

    play_pause_clicked = pyqtSignal()
    stop_clicked       = pyqtSignal()
    next_clicked       = pyqtSignal()
    previous_clicked   = pyqtSignal()
    seek_requested     = pyqtSignal(int)
    volume_changed     = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playerBar")
        self._duration_ms = 0
        self._seeking = False
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # ── Controles de transporte ────────────────────────────── #
        self._prev_btn = QPushButton("⏮")
        self._prev_btn.setObjectName("playerBtnPrev")
        self._prev_btn.setFixedSize(36, 36)
        self._prev_btn.clicked.connect(self.previous_clicked)
        layout.addWidget(self._prev_btn)

        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("playerBtnPlay")
        self._play_btn.setFixedSize(40, 40)
        self._play_btn.clicked.connect(self.play_pause_clicked)
        layout.addWidget(self._play_btn)

        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setObjectName("playerBtnStop")
        self._stop_btn.setFixedSize(36, 36)
        self._stop_btn.clicked.connect(self.stop_clicked)
        layout.addWidget(self._stop_btn)

        self._next_btn = QPushButton("⏭")
        self._next_btn.setObjectName("playerBtnNext")
        self._next_btn.setFixedSize(36, 36)
        self._next_btn.clicked.connect(self.next_clicked)
        layout.addWidget(self._next_btn)

        # ── Info de pista ──────────────────────────────────────── #
        self._track_label = QLabel("")
        self._track_label.setObjectName("playerTrackLabel")
        self._track_label.setMinimumWidth(160)
        layout.addWidget(self._track_label)

        # ── Posición ───────────────────────────────────────────── #
        self._pos_label = QLabel("0:00")
        self._pos_label.setObjectName("playerPosLabel")
        layout.addWidget(self._pos_label)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setObjectName("playerSeekSlider")
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setTracking(True)
        self._seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self._seek_slider.sliderReleased.connect(self._on_seek_released)
        layout.addWidget(self._seek_slider, stretch=1)

        self._dur_label = QLabel("0:00")
        self._dur_label.setObjectName("playerDurLabel")
        layout.addWidget(self._dur_label)

        # ── Volumen ────────────────────────────────────────────── #
        vol_icon = QLabel("🔊")
        vol_icon.setObjectName("playerVolIcon")
        layout.addWidget(vol_icon)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setObjectName("playerVolSlider")
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(70)
        self._vol_slider.setFixedWidth(80)
        self._vol_slider.valueChanged.connect(self.volume_changed)
        layout.addWidget(self._vol_slider)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def update_track(self, track: Track) -> None:
        artist = track.artist_name or "Desconocido"
        self._track_label.setText(f"{track.title}  —  {artist}")

    def update_position(self, pos_ms: int, dur_ms: int) -> None:
        self._duration_ms = dur_ms
        if not self._seeking and dur_ms > 0:
            self._seek_slider.setValue(int(pos_ms / dur_ms * 1000))
        self._pos_label.setText(_ms_to_str(pos_ms))
        self._dur_label.setText(_ms_to_str(dur_ms))

    def set_playing(self, is_playing: bool) -> None:
        self._play_btn.setText("⏸" if is_playing else "▶")

    def reset_position(self) -> None:
        self._seek_slider.setValue(0)
        self._pos_label.setText("0:00")

    def set_volume(self, volume: int) -> None:
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(volume)
        self._vol_slider.blockSignals(False)

    # ------------------------------------------------------------------
    # Seek
    # ------------------------------------------------------------------

    def _on_seek_pressed(self) -> None:
        self._seeking = True

    def _on_seek_released(self) -> None:
        self._seeking = False
        if self._duration_ms > 0:
            pos = int(self._seek_slider.value() / 1000 * self._duration_ms)
            self.seek_requested.emit(pos)
