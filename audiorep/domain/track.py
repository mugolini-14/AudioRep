"""
Track — Entidad de dominio que representa una pista de audio.

Puede ser un archivo local, una pista de CD o una pista ripeada.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AudioFormat(str, Enum):
    MP3     = "MP3"
    FLAC    = "FLAC"
    OGG     = "OGG"
    AAC     = "AAC"
    WAV     = "WAV"
    WMA     = "WMA"
    OPUS    = "OPUS"
    CD      = "CD"
    UNKNOWN = "UNKNOWN"


class TrackSource(str, Enum):
    LOCAL  = "LOCAL"
    CD     = "CD"
    RIPPED = "RIPPED"


@dataclass
class Track:
    """Pista de audio (archivo local, CD o ripeada)."""

    title:          str
    artist_name:    str             = ""
    album_title:    str             = ""
    track_number:   int             = 0
    disc_number:    int             = 1
    duration_ms:    int             = 0
    year:           int | None      = None
    genre:          str             = ""
    file_path:      str | None      = None
    format:         AudioFormat     = AudioFormat.UNKNOWN
    source:         TrackSource     = TrackSource.LOCAL
    bitrate_kbps:   int             = 0
    musicbrainz_id: str | None      = None
    acoustid:       str | None      = None
    play_count:     int             = 0
    rating:         int             = 0
    album_id:       int | None      = None
    artist_id:      int | None      = None
    id:             int | None      = None

    def __str__(self) -> str:
        return f"{self.artist_name} — {self.title}"

    @property
    def duration_str(self) -> str:
        """Duración formateada como MM:SS."""
        total_s = self.duration_ms // 1000
        return f"{total_s // 60}:{total_s % 60:02d}"
