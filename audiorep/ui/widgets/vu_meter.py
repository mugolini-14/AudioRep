"""
VUMeterWidget — VU Metro estéreo con análisis de audio real.

Diseño:
  - 12 barras para el canal L (izquierda) + 12 barras para el canal R (derecha).
  - Cada grupo muestra el nivel RMS del canal correspondiente con peak hold.
  - Separación visual en el centro.
  - Los niveles se leen de audiorep.core.audio_levels, que es escrito por
    VLCPlayer cuando el análisis PCM real está disponible.
  - Fallback: si audio_levels reporta (0, 0) durante la reproducción, se
    activa un modo de simulación suave para que el metro no quede en silencio.

Colores: verde (#34C378) → amarillo (#E8B928) → rojo (#DC3C3C).
"""
from __future__ import annotations

import random

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QSizePolicy, QWidget

from audiorep.core import audio_levels
from audiorep.core.events import app_events

# ── Parámetros visuales ────────────────────────────────────────────────── #
_BARS_PER_CH  = 12      # barras por canal (L y R)
_TICK_MS      = 40      # ~25 fps
_GAP_BAR      = 2       # separación entre barras (px)
_GAP_CENTER   = 8       # separación entre grupo L y grupo R (px)
_DECAY_PLAY   = 0.55    # suavizado de nivel durante reproducción
_DECAY_STOP   = 0.88    # decaimiento al detener
_PEAK_DROP    = 0.012   # velocidad de caída del peak hold

# Colores
_COLOR_LOW  = QColor(52,  195, 120)    # verde  #34C378
_COLOR_MID  = QColor(232, 185,  40)    # amarillo #E8B928
_COLOR_HIGH = QColor(220,  60,  60)    # rojo   #DC3C3C
_COLOR_BG   = QColor(18,  18,  30)     # fondo  #12121e
_COLOR_DIV  = QColor(42,  42,  62)     # divisor central


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    r  = int(a.red()   + (b.red()   - a.red())   * t)
    g  = int(a.green() + (b.green() - a.green()) * t)
    bl = int(a.blue()  + (b.blue()  - a.blue())  * t)
    return QColor(r, g, bl)


def _bar_color(level: float) -> QColor:
    if level < 0.6:
        return _lerp(_COLOR_LOW, _COLOR_MID, level / 0.6)
    return _lerp(_COLOR_MID, _COLOR_HIGH, (level - 0.6) / 0.4)


class VUMeterWidget(QWidget):
    """VU metro estéreo con análisis de audio real (PCM) y peak hold."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("vuMeter")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(100)

        n = _BARS_PER_CH * 2
        self._levels = [0.0] * n     # niveles mostrados (suavizados)
        self._peaks  = [0.0] * n     # peak hold por barra
        self._playing = False
        self._zero_ticks = 0         # ticks consecutivos con señal cero real

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
        self._zero_ticks = 0
        if not self._timer.isActive():
            self._timer.start()

    def _on_pause(self) -> None:
        self._playing = False

    def _on_stop(self) -> None:
        self._playing = False
        self._peaks = [0.0] * (_BARS_PER_CH * 2)
        audio_levels.reset()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        n = _BARS_PER_CH * 2

        if self._playing:
            raw_l, raw_r = audio_levels.read()
            real = audio_levels.is_real()

            # Detectar si la señal real lleva varios ticks en cero
            if real and raw_l < 0.001 and raw_r < 0.001:
                self._zero_ticks += 1
            else:
                self._zero_ticks = 0

            # Si hay análisis real y hay señal, usarla
            use_real = real and self._zero_ticks < 15

            for i in range(n):
                ch = i // _BARS_PER_CH          # 0 = L, 1 = R
                raw = raw_l if ch == 0 else raw_r

                if use_real:
                    # Añadir micro-variación per-barra para efecto visual
                    noise = random.gauss(0, 0.04)
                    target = max(0.0, min(1.0, raw + noise))
                else:
                    # Simulación de respaldo (señal real cero o no disponible)
                    target = max(0.0, min(1.0, random.gauss(0.42, 0.20)))

                self._levels[i] = self._levels[i] * _DECAY_PLAY + target * (1.0 - _DECAY_PLAY)

                if self._levels[i] > self._peaks[i]:
                    self._peaks[i] = self._levels[i]
                else:
                    self._peaks[i] = max(0.0, self._peaks[i] - _PEAK_DROP)

        else:
            # Apagado gradual
            all_zero = True
            for i in range(n):
                self._levels[i] *= _DECAY_STOP
                self._peaks[i]  *= _DECAY_STOP
                if self._levels[i] > 0.004:
                    all_zero = False
            if all_zero:
                self._levels = [0.0] * n
                self._peaks  = [0.0] * n
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

        # Fondo
        painter.fillRect(0, 0, w, h, _COLOR_BG)

        n   = _BARS_PER_CH * 2
        gap = _GAP_BAR
        # Ancho disponible descontando el separador central y los gaps entre barras
        avail = w - _GAP_CENTER - gap * (n - 2)   # n-2 gaps (n barras, sin el gap central)
        bar_w = max(2.0, avail / n)

        for i in range(n):
            # Posición X teniendo en cuenta el gap central entre grupos
            if i < _BARS_PER_CH:
                x = int(i * (bar_w + gap))
            else:
                x = int(i * (bar_w + gap) + _GAP_CENTER)

            level = self._levels[i]
            bar_h = max(2, int(level * h))
            y = h - bar_h

            painter.fillRect(x, y, int(bar_w), bar_h, _bar_color(level))

            # Peak hold
            peak = self._peaks[i]
            if peak > 0.02:
                peak_y = max(0, int((1.0 - peak) * h))
                painter.fillRect(x, peak_y, int(bar_w), 2, _bar_color(peak))

        # Divisor central
        cx = int(_BARS_PER_CH * (bar_w + gap) + _GAP_CENTER // 2 - 1)
        painter.fillRect(cx, 0, 2, h, _COLOR_DIV)

        painter.end()
