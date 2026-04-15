"""CDDisc — Entidad de dominio que representa un CD físico en la lectora."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RipStatus(str, Enum):
    PENDING  = "PENDING"
    RIPPING  = "RIPPING"
    DONE     = "DONE"
    ERROR    = "ERROR"
    SKIPPED  = "SKIPPED"


@dataclass
class CDTrack:
    """Pista de un CD físico."""

    number:         int
    duration_ms:    int             = 0
    offset:         int             = 0        # offset en sectores (para Disc ID)
    rip_status:     RipStatus       = RipStatus.PENDING
    ripped_path:    str | None      = None
    title:          str             = ""
    artist_name:    str             = ""
    musicbrainz_id: str | None      = None


@dataclass
class CDDisc:
    """
    CD físico en la unidad lectora.

    Es efímero: no se persiste en la base de datos.
    Tras el ripeo se generan entidades Track normales.
    """

    disc_id:        str
    drive_path:     str                 = ""
    tracks:         list[CDTrack]       = field(default_factory=list)
    musicbrainz_id: str | None          = None
    freedb_id:      str | None          = None   # ID CDDB/FreeDB/GnuDB (8 hex)
    album_title:    str                 = ""
    artist_name:    str                 = ""
    year:           int | None          = None
    genre:          str                 = ""
    cover_data:     bytes | None        = None
    identified:     bool                = False

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    def __str__(self) -> str:
        if self.album_title:
            return f"{self.artist_name} — {self.album_title}"
        return f"CD ({self.disc_id[:8]}…)"
