"""
PlayerBar — Barra de controles de reproducción.

Contiene:
    - Botones: Anterior, Play/Pausa, Siguiente, Detener
    - Slider de progreso con etiquetas de tiempo
    - Botones de Shuffle y Repeat (cicla entre modos)
    - Slider de volumen

Responsabilidad de este widget: SOLO la presentación.
No llama a ningún service directamente; emite señales.
El PlayerController conecta esas señales con el PlayerService.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from audiorep.core.utils import format_duration
from audiorep.services.player_service import RepeatMode


class PlayerBar(QWidget):
    """
    Barra inferior de controles de reproducción.

    Señales emitidas (el Controller las conecta al Service):
        play_pause_clicked  — el usuario presionó Play o Pausa
        stop_clicked        — el usuario presionó Detener
        next_clicked        — el usuario presionó Siguiente
        previous_clicked    — el usuario presionó Anterior
        seek_requested      — el usuario movió el slider de progreso (pos en ms)
        volume_changed      — el usuario movió el slider de volumen (0–100)
        shuffle_toggled     — el usuario activó/desactivó shuffle
        repeat_changed      — el usuario cambió el modo de repeat
    """

    play_pause_clicked = pyqtSignal()
    stop_clicked       = pyqtSignal()
    next_clicked       = pyqtSignal()
    previous_clicked   = pyqtSignal()
    seek_requested     = pyqtSignal(int)   # milisegundos
    volume_changed     = pyqtSignal(int)   # 0–100
    shuffle_toggled    = pyqtSignal(bool)
    repeat_changed     = pyqtSignal(str)   # valor de RepeatMode

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_playing  = False
        self._is_seeking  = False   # True mientras el usuario arrastra el slider
        self._repeat_mode = RepeatMode.NONE

        self._build_ui()
        self._connect_internal()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        root.addLayout(self._build_progress_row())
        root.addLayout(self._build_controls_row())

    def _build_progress_row(self) -> QHBoxLayout:
        """Slider de progreso + etiquetas de tiempo."""
        row = QHBoxLayout()
        row.setSpacing(8)

        self._lbl_elapsed = QLabel("0:00")
        self._lbl_elapsed.setFixedWidth(42)
        self._lbl_elapsed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_elapsed.setObjectName("timeLabel")

        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setRange(0, 1000)   # se escala dinámicamente
        self._progress_slider.setValue(0)
        self._progress_slider.setObjectName("progressSlider")

        self._lbl_total = QLabel("0:00")
        self._lbl_total.setFixedWidth(42)
        self._lbl_total.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_total.setObjectName("timeLabel")

        row.addWidget(self._lbl_elapsed)
        row.addWidget(self._progress_slider, 1)
        row.addWidget(self._lbl_total)
        return row

    def _build_controls_row(self) -> QHBoxLayout:
        """Botones de transporte + shuffle/repeat + volumen."""
        row = QHBoxLayout()
        row.setSpacing(4)

        # ── Shuffle ────────────────────────────────────────────────────
        self._btn_shuffle = QPushButton("⇄")
        self._btn_shuffle.setToolTip("Aleatorio")
        self._btn_shuffle.setCheckable(True)
        self._btn_shuffle.setFixedSize(36, 36)
        self._btn_shuffle.setObjectName("modeButton")

        # ── Transporte ─────────────────────────────────────────────────
        self._btn_previous = QPushButton("⏮")
        self._btn_previous.setToolTip("Anterior")
        self._btn_previous.setFixedSize(36, 36)
        self._btn_previous.setObjectName("transportButton")

        self._btn_play_pause = QPushButton("▶")
        self._btn_play_pause.setToolTip("Reproducir")
        self._btn_play_pause.setFixedSize(48, 48)
        self._btn_play_pause.setObjectName("playButton")

        self._btn_stop = QPushButton("⏹")
        self._btn_stop.setToolTip("Detener")
        self._btn_stop.setFixedSize(36, 36)
        self._btn_stop.setObjectName("transportButton")

        self._btn_next = QPushButton("⏭")
        self._btn_next.setToolTip("Siguiente")
        self._btn_next.setFixedSize(36, 36)
        self._btn_next.setObjectName("transportButton")

        # ── Repeat ─────────────────────────────────────────────────────
        self._btn_repeat = QPushButton("↺")
        self._btn_repeat.setToolTip("Repetir: desactivado")
        self._btn_repeat.setFixedSize(36, 36)
        self._btn_repeat.setObjectName("modeButton")

        # ── Espaciador central ─────────────────────────────────────────
        spacer_left  = QWidget(); spacer_left.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        spacer_right = QWidget(); spacer_right.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        # ── Volumen ────────────────────────────────────────────────────
        lbl_vol = QLabel("🔊")
        lbl_vol.setObjectName("volumeIcon")

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.setObjectName("volumeSlider")

        # ── Armar fila ─────────────────────────────────────────────────
        row.addWidget(self._btn_shuffle)
        row.addWidget(spacer_left)
        row.addWidget(self._btn_previous)
        row.addWidget(self._btn_play_pause)
        row.addWidget(self._btn_stop)
        row.addWidget(self._btn_next)
        row.addWidget(self._btn_repeat)
        row.addWidget(spacer_right)
        row.addWidget(lbl_vol)
        row.addWidget(self._volume_slider)
        return row

    def _connect_internal(self) -> None:
        """Conexiones internas del widget (sin salir al exterior)."""
        self._btn_play_pause.clicked.connect(self.play_pause_clicked)
        self._btn_stop.clicked.connect(self.stop_clicked)
        self._btn_next.clicked.connect(self.next_clicked)
        self._btn_previous.clicked.connect(self.previous_clicked)
        self._btn_shuffle.clicked.connect(self._on_shuffle_clicked)
        self._btn_repeat.clicked.connect(self._on_repeat_clicked)

        # Slider de progreso: distinguir arrastre de usuario vs. actualización por código
        self._progress_slider.sliderPressed.connect(self._on_progress_pressed)
        self._progress_slider.sliderReleased.connect(self._on_progress_released)

        self._volume_slider.valueChanged.connect(self.volume_changed)

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_progress_pressed(self) -> None:
        self._is_seeking = True

    def _on_progress_released(self) -> None:
        self._is_seeking = False
        duration_ms = self._current_duration_ms
        if duration_ms > 0:
            position_ms = int(
                self._progress_slider.value() / self._progress_slider.maximum() * duration_ms
            )
            self.seek_requested.emit(position_ms)

    def _on_shuffle_clicked(self, checked: bool) -> None:
        self.shuffle_toggled.emit(checked)

    def _on_repeat_clicked(self) -> None:
        """Cicla entre los modos: NONE → ONE → ALL → NONE."""
        if self._repeat_mode == RepeatMode.NONE:
            self._repeat_mode = RepeatMode.ONE
        elif self._repeat_mode == RepeatMode.ONE:
            self._repeat_mode = RepeatMode.ALL
        else:
            self._repeat_mode = RepeatMode.NONE
        self._update_repeat_button()
        self.repeat_changed.emit(self._repeat_mode.value)

    def _update_repeat_button(self) -> None:
        tooltips = {
            RepeatMode.NONE: "Repetir: desactivado",
            RepeatMode.ONE:  "Repetir: esta pista",
            RepeatMode.ALL:  "Repetir: toda la cola",
        }
        labels = {
            RepeatMode.NONE: "↺",
            RepeatMode.ONE:  "↺¹",
            RepeatMode.ALL:  "↻",
        }
        self._btn_repeat.setToolTip(tooltips[self._repeat_mode])
        self._btn_repeat.setText(labels[self._repeat_mode])
        self._btn_repeat.setProperty("active", self._repeat_mode != RepeatMode.NONE)
        self._btn_repeat.style().unpolish(self._btn_repeat)
        self._btn_repeat.style().polish(self._btn_repeat)

    # ------------------------------------------------------------------
    # API pública — actualización desde el Controller
    # ------------------------------------------------------------------

    def set_playing(self, playing: bool) -> None:
        """Actualiza el ícono de Play/Pausa."""
        self._is_playing = playing
        self._btn_play_pause.setText("⏸" if playing else "▶")
        self._btn_play_pause.setToolTip("Pausar" if playing else "Reproducir")

    def update_position(self, position_ms: int, duration_ms: int) -> None:
        """
        Actualiza el slider de progreso y las etiquetas de tiempo.
        No hace nada si el usuario está arrastrando el slider.
        """
        self._current_duration_ms = duration_ms

        self._lbl_elapsed.setText(format_duration(position_ms))
        self._lbl_total.setText(format_duration(duration_ms))

        if not self._is_seeking and duration_ms > 0:
            self._progress_slider.blockSignals(True)
            self._progress_slider.setValue(
                int(position_ms / duration_ms * self._progress_slider.maximum())
            )
            self._progress_slider.blockSignals(False)

    def reset(self) -> None:
        """Resetea la barra al estado inicial (sin pista)."""
        self._is_playing = False
        self._current_duration_ms = 0
        self._btn_play_pause.setText("▶")
        self._progress_slider.blockSignals(True)
        self._progress_slider.setValue(0)
        self._progress_slider.blockSignals(False)
        self._lbl_elapsed.setText("0:00")
        self._lbl_total.setText("0:00")

    # Almacenamos la duración actual para el cálculo en _on_progress_released
    _current_duration_ms: int = 0
