"""EqPreset — Preset del ecualizador gráfico."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EqPreset:
    """Representa un preset del ecualizador (usuario o predefinido)."""

    name:       str
    preamp:     float        = 0.0
    bands:      list[float]  = field(default_factory=lambda: [0.0] * 10)
    is_builtin: bool         = False
