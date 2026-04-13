"""Album — Entidad de dominio que representa un álbum musical."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Album:
    """Álbum musical. Agrupa pistas bajo un lanzamiento."""

    title:          str
    artist_id:      int | None      = None
    artist_name:    str             = ""
    year:           int | None      = None
    release_date:   date | None     = None
    genre:          str             = ""
    label:          str             = ""
    musicbrainz_id: str | None      = None
    cover_path:     str | None      = None
    total_tracks:   int             = 0
    total_discs:    int             = 1
    id:             int | None      = None

    def __str__(self) -> str:
        return f"{self.artist_name} — {self.title}"
