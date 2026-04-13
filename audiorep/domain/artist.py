"""Artist — Entidad de dominio que representa un artista o banda."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Artist:
    """Artista o banda musical."""

    name:           str
    sort_name:      str             = ""
    musicbrainz_id: str | None      = None
    genres:         list[str]       = field(default_factory=list)
    id:             int | None      = None

    def __str__(self) -> str:
        return self.name
