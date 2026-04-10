"""
Modelo de dominio: Track.

Representa una pista de audio individual, ya sea un archivo local o
una pista de CD. Es la entidad central del sistema.
No tiene dependencias externas; es un dato puro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AudioFormat(str, Enum):
    """Formatos de audio soportados."""
    MP3  = "mp3"
    FLAC = "flac"
    OGG  = "ogg"
    AAC  = "aac"
    WAV  = "wav"
    WMA  = "wma"
    OPUS = "opus"
    CD   = "cd"       # Pista de CD sin ripear
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> AudioFormat:
        """Devuelve el formato a partir de la extensión de archivo."""
        return cls._value2member_map_.get(ext.lower().lstrip("."), cls.UNKNOWN)


class TrackSource(str, Enum):
    """Origen de la pista."""
    LOCAL = "local"    # Archivo en disco
    CD    = "cd"       # Pista de CD en tiempo real
    RIPPED = "ripped"  # Ripeada desde CD y guardada localmente


@dataclass
class Track:
    """
    Pista de audio.

    Attributes:
        id:              Identificador interno en base de datos local.
        title:           Título de la pista.
        artist_id:       FK al Artist.
        artist_name:     Nombre desnormalizado del artista.
        album_id:        FK al Album.
        album_title:     Título desnormalizado del álbum.
        track_number:    Número de pista dentro del disco.
        disc_number:     Número de disco (para álbumes dobles, etc.).
        duration_ms:     Duración en milisegundos.
        year:            Año de grabación/lanzamiento.
        genre:           Género musical.
        file_path:       Ruta absoluta al archivo de audio (None si es pista CD no ripeada).
        format:          Formato del archivo (AudioFormat).
        source:          Origen de la pista (TrackSource).
        bitrate_kbps:    Bitrate en kbps (0 si es FLAC/lossless).
        sample_rate_hz:  Frecuencia de muestreo en Hz.
        channels:        Número de canales (1=mono, 2=stereo).
        file_size_bytes: Tamaño del archivo en bytes.
        musicbrainz_id:  MBID de la recording en MusicBrainz.
        acoustid:        Huella AcoustID (para identificación automática).
        play_count:      Cantidad de veces reproducida.
        rating:          Puntuación del usuario (0-5, 0 = sin puntuar).
        comment:         Comentario libre en el tag.
        lyrics:          Letra de la canción (opcional).
    """

    title: str
    id: int | None = None
    artist_id: int | None = None
    artist_name: str = ""
    album_id: int | None = None
    album_title: str = ""
    track_number: int = 0
    disc_number: int = 1
    duration_ms: int = 0
    year: int | None = None
    genre: str = ""
    file_path: str | None = None
    format: AudioFormat = AudioFormat.UNKNOWN
    source: TrackSource = TrackSource.LOCAL
    bitrate_kbps: int = 0
    sample_rate_hz: int = 0
    channels: int = 2
    file_size_bytes: int = 0
    musicbrainz_id: str | None = None
    acoustid: str | None = None
    play_count: int = 0
    rating: int = 0
    comment: str = ""
    lyrics: str = ""

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def duration_seconds(self) -> int:
        """Duración redondeada en segundos."""
        return self.duration_ms // 1000

    @property
    def duration_display(self) -> str:
        """Duración formateada como mm:ss."""
        total = self.duration_seconds
        minutes, seconds = divmod(total, 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def path(self) -> Path | None:
        """Ruta como objeto Path, o None si no hay archivo."""
        return Path(self.file_path) if self.file_path else None

    def is_available(self) -> bool:
        """
        Indica si la pista se puede reproducir ahora mismo.
        - LOCAL/RIPPED: el archivo debe existir en disco.
        - CD: siempre True (se asume CD presente si la instancia existe).
        """
        if self.source == TrackSource.CD:
            return True
        if self.file_path is None:
            return False
        return Path(self.file_path).exists()

    def is_lossless(self) -> bool:
        """Indica si el formato es sin pérdida."""
        return self.format in (AudioFormat.FLAC, AudioFormat.WAV, AudioFormat.CD)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        num = f"{self.track_number:02d}. " if self.track_number else ""
        return f"{num}{self.title}"

    def __repr__(self) -> str:
        return (
            f"Track(id={self.id!r}, title={self.title!r}, "
            f"artist={self.artist_name!r}, album={self.album_title!r})"
        )
