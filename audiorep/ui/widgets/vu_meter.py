"""
VUMeterWidget — Visualización de vúmetro animado.

Muestra barras verticales que se animan durante la reproducción.
Colores: verde (bajo) → amarillo (medio) → rojo (alto).

Se conecta a los app_events de reproducción para iniciar/detener la animación.
"""
from __future__ import annotations

import random

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from audiorep.core.events import app_events

_NUM_BARS   = 24
_TICK_MS    = 55          # ~18 fps
_DECAY      = 0.65        # factor de suavizado al actualizar
_FADE_RATE  = 0.88        # factor de decaimiento al parar

# Colores por nivel (RGB)
_COLOR_LOW    = QColor(52,  195, 120)   # verde  #34C378
_COLOR_MID    = QColor(232, 185,  40)   # amarillo #E8B928
_COLOR_HIGH   = QColor(220,  60,  60)   # rojo   #DC3C3C
_COLOR_BG     = QColor(18,  18,  30)    # fondo  #12121e


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    """Interpolación lineal entre dos colores."""
    r = int(a.red()   + (b.red()   - a.red())   * t)
    g = int(a.green() + (b.green() - a.green()) * t)
    bl = int(a.blue()  + (b.blue()  - a.blue())  * t)
    return QColor(r, g, bl)


def _bar_color(level: float) -> QColor:
    """Retorna el color de una barra según su nivel (0.0–1.0)."""
    if level < 0.6:
        return _lerp_color(_COLOR_LOW, _COLOR_MID, level / 0.6)
    return _lerp_color(_COLOR_MID, _COLOR_HIGH, (level - 0.6) / 0.4)


class VUMeterWidget(QWidget):
    """Vúmetro animado con barras verticales de colores."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vuMeter")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(70)

        self._levels  = [0.0] * _NUM_BARS
        self._peaks   = [0.0] * _NUM_BARS
        self._playing = False

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)

        app_events.playback_started.connect(self._on_play)
        app_events.playback_resumed.connect(self._on_play)
        app_events.playback_paused.connect(self._on_pause)
        app_events.playback_stopped.connect(self._on_stop)

    # ------------------------------------------------------------------
    # Handlers de eventos de reproducción
    # ------------------------------------------------------------------

    def _on_play(self) -> None:
        self._playing = True
        if not self._timer.isActive():
            self._timer.start()

    def _on_pause(self) -> None:
        self._playing = False

    def _on_stop(self) -> None:
        self._playing = False
        self._peaks = [0.0] * _NUM_BARS

    # ------------------------------------------------------------------
    # Animación
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if self._playing:
            for i in range(_NUM_BARS):
                # Simular señal de audio con variaciones suaves
                target = random.gauss(0.45, 0.22)
                target = max(0.0, min(1.0, target))
                self._levels[i] = self._levels[i] * _DECAY + target * (1.0 - _DECAY)
                if self._levels[i] > self._peaks[i]:
                    self._peaks[i] = self._levels[i]
                else:
                    self._peaks[i] = max(0.0, self._peaks[i] - 0.015)
        else:
            # Apagado gradual
            all_zero = True
            for i in range(_NUM_BARS):
                self._levels[i] *= _FADE_RATE
                self._peaks[i]  *= _FADE_RATE
                if self._levels[i] > 0.005:
                    all_zero = False
            if all_zero:
                self._levels = [0.0] * _NUM_BARS
                self._peaks  = [0.0] * _NUM_BARS
                self._timer.stop()

        self.update()

    # ------------------------------------------------------------------
    # Pintura
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()
        n = _NUM_BARS
        gap = 3
        total_gap = gap * (n - 1)
        bar_w = max(1.0, (w - total_gap) / n)

        # Fondo
        painter.fillRect(0, 0, w, h, _COLOR_BG)

        for i in range(n):
            x = int(i * (bar_w + gap))
            level = self._levels[i]
            bar_h = max(2, int(level * h))
            y = h - bar_h

            color = _bar_color(level)
            painter.fillRect(x, y, int(bar_w), bar_h, color)

            # Marca de pico
            peak = self._peaks[i]
            if peak > 0.02:
                peak_y = max(0, int((1.0 - peak) * h))
                peak_color = _bar_color(peak)
                painter.fillRect(x, peak_y, int(bar_w), 2, peak_color)

        painter.end()
