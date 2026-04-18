"""
PlayerBar — Barra inferior de controles de reproducción.

Layout (2 filas, min-height 90px):
    Fila 1: [transportFrame: shuffle | prev | stop | PLAY | next | repeat]
            | track info | [vol icon] [vol]
    Fila 2: [time elapsed] [====progress====] [time total]

objectNames alineados con dark.qss:
    transportFrame, transportButton, playButton, stopButton, modeButton,
    timeLabel, progressSlider, volumeSlider, volumeIcon

Signals:
    play_pause_clicked, stop_clicked, next_clicked, previous_clicked,
    seek_requested(int), volume_changed(int)
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
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
        self._last_volume: int = 100
        self._muted: bool = False
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 8, 16, 8)
        outer.setSpacing(4)

        # ── Fila 1: controles + track info + volumen ──────────────── #
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # Contenedor redondeado para todos los botones de transporte
        transport_frame = QFrame()
        transport_frame.setObjectName("transportFrame")
        transport_layout = QHBoxLayout(transport_frame)
        transport_layout.setContentsMargins(14, 6, 14, 6)
        transport_layout.setSpacing(4)

        # Shuffle (modo)
        self._shuffle_btn = QPushButton("⇄")
        self._shuffle_btn.setObjectName("modeButton")
        self._shuffle_btn.setFixedSize(46, 46)
        self._shuffle_btn.setCheckable(True)
        self._shuffle_btn.setToolTip("Aleatorio")
        transport_layout.addWidget(self._shuffle_btn)

        # Anterior
        self._prev_btn = QPushButton("⏮")
        self._prev_btn.setObjectName("transportButton")
        self._prev_btn.setFixedSize(46, 46)
        self._prev_btn.setToolTip("Anterior")
        self._prev_btn.clicked.connect(self.previous_clicked)
        transport_layout.addWidget(self._prev_btn)

        # Stop
        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setObjectName("transportButton")
        self._stop_btn.setFixedSize(46, 46)
        self._stop_btn.setToolTip("Detener")
        self._stop_btn.clicked.connect(self.stop_clicked)
        transport_layout.addWidget(self._stop_btn)

        # Play / Pause (botón principal)
        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("playButton")
        self._play_btn.setFixedSize(46, 46)
        self._play_btn.clicked.connect(self.play_pause_clicked)
        transport_layout.addWidget(self._play_btn)

        # Siguiente
        self._next_btn = QPushButton("⏭")
        self._next_btn.setObjectName("transportButton")
        self._next_btn.setFixedSize(46, 46)
        self._next_btn.setToolTip("Siguiente")
        self._next_btn.clicked.connect(self.next_clicked)
        transport_layout.addWidget(self._next_btn)

        # Repetir (modo)
        self._repeat_btn = QPushButton("↺")
        self._repeat_btn.setObjectName("modeButton")
        self._repeat_btn.setFixedSize(46, 46)
        self._repeat_btn.setCheckable(True)
        self._repeat_btn.setToolTip("Repetir")
        transport_layout.addWidget(self._repeat_btn)

        row1.addWidget(transport_frame)
        row1.addSpacing(8)

        # Tiempo transcurrido (antes del track label)
        self._pos_label = QLabel("0:00")
        self._pos_label.setObjectName("timeLabel")
        self._pos_label.setFixedWidth(52)
        self._pos_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self._pos_label)

        row1.addSpacing(4)

        # Info de pista (centro, expande)
        self._track_label = QLabel("")
        self._track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._track_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        row1.addWidget(self._track_label, stretch=1)

        row1.addSpacing(4)

        # Duración total (después del track label)
        self._dur_label = QLabel("0:00")
        self._dur_label.setObjectName("timeLabel")
        self._dur_label.setFixedWidth(52)
        self._dur_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self._dur_label)

        row1.addSpacing(8)

        # Volumen
        self._vol_icon_btn = QPushButton("🔊")
        self._vol_icon_btn.setObjectName("volumeIcon")
        self._vol_icon_btn.setFixedSize(46, 46)
        self._vol_icon_btn.setToolTip("Silenciar / Activar sonido")
        self._vol_icon_btn.clicked.connect(self._toggle_mute)
        row1.addWidget(self._vol_icon_btn)

        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setObjectName("volumeSlider")
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(70)
        self._vol_slider.setMinimumWidth(180)
        self._vol_slider.setMaximumWidth(280)
        self._vol_slider.valueChanged.connect(self.volume_changed)
        row1.addWidget(self._vol_slider)

        outer.addLayout(row1)

        # ── Fila 2: barra de progreso a ancho completo ────────────── #
        row2 = QHBoxLayout()
        row2.setSpacing(0)
        row2.setContentsMargins(0, 0, 0, 0)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setObjectName("progressSlider")
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self._seek_slider.sliderReleased.connect(self._on_seek_released)
        row2.addWidget(self._seek_slider, stretch=1)

        outer.addLayout(row2)

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
        self._dur_label.setText("0:00")

    def set_volume(self, volume: int) -> None:
        self._vol_slider.blockSignals(True)
        self._vol_slider.setValue(volume)
        self._vol_slider.blockSignals(False)
        if volume > 0:
            self._last_volume = volume
            if self._muted:
                self._muted = False
                self._vol_icon_btn.setText("🔊")

    # ------------------------------------------------------------------
    # Mute toggle
    # ------------------------------------------------------------------

    def _toggle_mute(self) -> None:
        if self._muted:
            self._muted = False
            self._vol_icon_btn.setText("🔊")
            self._vol_slider.setValue(self._last_volume)
        else:
            current = self._vol_slider.value()
            if current > 0:
                self._last_volume = current
            self._muted = True
            self._vol_icon_btn.setText("🔇")
            self._vol_slider.setValue(0)

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
