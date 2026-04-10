"""
Modelo de dominio: CDDisc y CDTrack.

Representa un disco compacto físico y sus pistas tal como son leídas
por la unidad lectora, antes de ser ripeadas o identificadas.
No tiene dependencias externas; es un dato puro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RipStatus(str, Enum):
    """Estado de ripeo de una pista de CD."""
    PENDING   = "pending"    # No iniciado
    RIPPING   = "ripping"    # En proceso
    DONE      = "done"       # Completado correctamente
    ERROR     = "error"      # Falló el ripeo
    SKIPPED   = "skipped"    # Omitido por el usuario


@dataclass
class CDTrack:
    """
    Pista física de un CD.

    Attributes:
        number:        Número de pista (base 1).
        duration_ms:   Duración en milisegundos.
        offset:        Offset en sectores CD (usado para calcular Disc ID).
        title:         Título (vacío hasta que se identifique el disco).
        artist_name:   Artista de la pista (puede diferir del álbum en recopilaciones).
        rip_status:    Estado del proceso de ripeo.
        ripped_path:   Ruta del archivo resultante tras el ripeo (None si no ripeada).
        isrc:          International Standard Recording Code (si está en el CD).
    """

    number: int
    duration_ms: int = 0
    offset: int = 0
    title: str = ""
    artist_name: str = ""
    rip_status: RipStatus = RipStatus.PENDING
    ripped_path: str | None = None
    isrc: str | None = None

    @property
    def duration_seconds(self) -> int:
        return self.duration_ms // 1000

    @property
    def duration_display(self) -> str:
        total = self.duration_seconds
        minutes, seconds = divmod(total, 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def is_ripped(self) -> bool:
        return self.rip_status == RipStatus.DONE and self.ripped_path is not None

    def __str__(self) -> str:
        title = self.title or f"Pista {self.number:02d}"
        return f"{self.number:02d}. {title} [{self.duration_display}]"

    def __repr__(self) -> str:
        return f"CDTrack(number={self.number}, title={self.title!r}, status={self.rip_status})"


@dataclass
class CDDisc:
    """
    Disco compacto físico en la lectora.

    Attributes:
        disc_id:          Disc ID calculado (formato MusicBrainz / FreeDB).
        musicbrainz_id:   MBID del release identificado en MusicBrainz (None si no identificado).
        album_title:      Título del álbum (vacío hasta identificación).
        artist_name:      Artista principal.
        year:             Año de lanzamiento.
        genre:            Género principal.
        tracks:           Lista de pistas del CD.
        cover_url:        URL de la portada encontrada online.
        cover_data:       Bytes de la imagen de portada (cacheada en memoria).
        drive_path:       Ruta de la unidad lectora (ej. "D:" en Windows, "/dev/cdrom" en Linux).
        total_duration_ms: Duración total calculada.
        identified:       True si el disco fue reconocido en algún servicio online.
    """

    disc_id: str
    drive_path: str = ""
    tracks: list[CDTrack] = field(default_factory=list)
    musicbrainz_id: str | None = None
    album_title: str = ""
    artist_name: str = ""
    year: int | None = None
    genre: str = ""
    cover_url: str | None = None
    cover_data: bytes | None = None
    identified: bool = False

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    @property
    def total_duration_ms(self) -> int:
        return sum(t.duration_ms for t in self.tracks)

    @property
    def total_duration_display(self) -> str:
        total = self.total_duration_ms // 1000
        minutes, seconds = divmod(total, 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def ripped_count(self) -> int:
        """Cuántas pistas han sido ripeadas correctamente."""
        return sum(1 for t in self.tracks if t.is_ripped)

    @property
    def all_ripped(self) -> bool:
        return self.track_count > 0 and self.ripped_count == self.track_count

    # ------------------------------------------------------------------
    # Mutaciones
    # ------------------------------------------------------------------

    def get_track(self, number: int) -> CDTrack | None:
        """Retorna la pista con el número indicado, o None."""
        return next((t for t in self.tracks if t.number == number), None)

    def apply_metadata(self, metadata: dict) -> None:
        """
        Aplica metadatos obtenidos de un servicio online (ej. MusicBrainz).

        Args:
            metadata: dict con claves: title, artist, year, genre, tracks
                      donde tracks es una lista de {number, title, artist, isrc}
        """
        self.album_title  = metadata.get("title", self.album_title)
        self.artist_name  = metadata.get("artist", self.artist_name)
        self.year         = metadata.get("year", self.year)
        self.genre        = metadata.get("genre", self.genre)
        self.cover_url    = metadata.get("cover_url", self.cover_url)
        self.identified   = True

        for track_meta in metadata.get("tracks", []):
            track = self.get_track(track_meta.get("number", 0))
            if track:
                track.title       = track_meta.get("title", track.title)
                track.artist_name = track_meta.get("artist", self.artist_name)
                track.isrc        = track_meta.get("isrc", track.isrc)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        if self.album_title:
            return f"{self.artist_name} — {self.album_title} ({self.track_count} pistas)"
        return f"CD [{self.disc_id}] ({self.track_count} pistas)"

    def __repr__(self) -> str:
        return (
            f"CDDisc(disc_id={self.disc_id!r}, album={self.album_title!r}, "
            f"tracks={self.track_count}, identified={self.identified})"
        )
