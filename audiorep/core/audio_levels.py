"""
audio_levels — Buffer thread-safe de niveles de audio en tiempo real.

Módulo de core compartido entre infrastructure (VLCPlayer lo escribe)
y UI (VUMeterWidget lo lee). No depende de Qt ni de VLC.

Uso:
    # Escribir (desde el callback de audio de VLC, en un thread de VLC)
    from audiorep.core import audio_levels
    audio_levels.update(left_rms, right_rms)

    # Leer (desde el timer de VUMeterWidget, en el thread principal de Qt)
    left, right = audio_levels.read()
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_left: float = 0.0
_right: float = 0.0
_real_analysis: bool = False   # True cuando hay análisis PCM real activo


def update(left: float, right: float) -> None:
    """Actualiza los niveles desde el callback de audio (thread de VLC)."""
    global _left, _right, _real_analysis
    with _lock:
        _left = left
        _right = right
        _real_analysis = True


def read() -> tuple[float, float]:
    """Lee los niveles actuales (thread del timer de Qt)."""
    with _lock:
        return _left, _right


def reset() -> None:
    """Pone los niveles a cero (ej. al buscar o detener)."""
    global _left, _right
    with _lock:
        _left = 0.0
        _right = 0.0


def is_real() -> bool:
    """Retorna True si el análisis PCM real está activo."""
    with _lock:
        return _real_analysis
