"""Playlist — Entidad de dominio que representa una lista de reproducción."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PlaylistEntry:
    """Entrada en una playlist: referencia a una pista con posición."""

    track_id:   int
    position:   int             = 0
    added_at:   datetime        = field(default_factory=datetime.now)
    id:         int | None      = None


@dataclass
class Playlist:
    """Lista de reproducción (manual o inteligente)."""

    name:        str
    entries:     list[PlaylistEntry] = field(default_factory=list)
    is_smart:    bool                = False
    smart_query: dict                = field(default_factory=dict)
    id:          int | None          = None

    def __str__(self) -> str:
        return self.name

    @property
    def track_count(self) -> int:
        return len(self.entries)
