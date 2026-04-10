"""
Contratos (interfaces) de AudioRep.

Define los Protocols que separan la lógica de negocio (services)
de las implementaciones concretas (infrastructure).

Regla: los Services importan solo de este módulo, nunca de infrastructure.
Las implementaciones concretas en infrastructure/ implementan estos Protocols.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.cd_disc import CDDisc
from audiorep.domain.playlist import Playlist
from audiorep.domain.track import Track


# ==================================================================
# Audio playback
# ==================================================================

@runtime_checkable
class IAudioPlayer(Protocol):
    """Contrato del backend de reproducción de audio."""

    def play(self, track: Track) -> None:
        """Inicia la reproducción de una pista."""
        ...

    def pause(self) -> None:
        """Pausa la reproducción en curso."""
        ...

    def resume(self) -> None:
        """Reanuda la reproducción pausada."""
        ...

    def stop(self) -> None:
        """Detiene la reproducción y libera el recurso."""
        ...

    def seek(self, position_ms: int) -> None:
        """Salta a la posición indicada en milisegundos."""
        ...

    def get_position_ms(self) -> int:
        """Retorna la posición actual de reproducción en milisegundos."""
        ...

    def get_duration_ms(self) -> int:
        """Retorna la duración total de la pista en reproducción."""
        ...

    def set_volume(self, volume: int) -> None:
        """Ajusta el volumen (0–100)."""
        ...

    def get_volume(self) -> int:
        """Retorna el volumen actual (0–100)."""
        ...

    @property
    def is_playing(self) -> bool:
        """True si hay reproducción activa."""
        ...

    @property
    def is_paused(self) -> bool:
        """True si la reproducción está pausada."""
        ...


# ==================================================================
# Repositories
# ==================================================================

@runtime_checkable
class ITrackRepository(Protocol):
    """Contrato de acceso a datos de pistas."""

    def get_by_id(self, track_id: int) -> Track | None: ...
    def get_all(self) -> list[Track]: ...
    def search(self, query: str) -> list[Track]: ...
    def get_by_album(self, album_id: int) -> list[Track]: ...
    def get_by_artist(self, artist_id: int) -> list[Track]: ...
    def save(self, track: Track) -> Track: ...
    def delete(self, track_id: int) -> None: ...
    def exists_by_path(self, file_path: str) -> bool: ...


@runtime_checkable
class IAlbumRepository(Protocol):
    """Contrato de acceso a datos de álbumes."""

    def get_by_id(self, album_id: int) -> Album | None: ...
    def get_all(self) -> list[Album]: ...
    def search(self, query: str) -> list[Album]: ...
    def get_by_artist(self, artist_id: int) -> list[Album]: ...
    def save(self, album: Album) -> Album: ...
    def delete(self, album_id: int) -> None: ...


@runtime_checkable
class IArtistRepository(Protocol):
    """Contrato de acceso a datos de artistas."""

    def get_by_id(self, artist_id: int) -> Artist | None: ...
    def get_all(self) -> list[Artist]: ...
    def search(self, query: str) -> list[Artist]: ...
    def save(self, artist: Artist) -> Artist: ...
    def delete(self, artist_id: int) -> None: ...


@runtime_checkable
class IPlaylistRepository(Protocol):
    """Contrato de acceso a datos de playlists."""

    def get_by_id(self, playlist_id: int) -> Playlist | None: ...
    def get_all(self) -> list[Playlist]: ...
    def save(self, playlist: Playlist) -> Playlist: ...
    def delete(self, playlist_id: int) -> None: ...


# ==================================================================
# Metadata providers (APIs externas)
# ==================================================================

@runtime_checkable
class IMetadataProvider(Protocol):
    """
    Proveedor de metadatos musicales online.
    Implementado por: MusicBrainzClient, DiscogsClient, etc.
    """

    def search_by_disc_id(self, disc_id: str) -> list[dict]: ...
    def search_album(self, artist: str, title: str) -> list[dict]: ...
    def get_track_info(self, recording_id: str) -> dict | None: ...
    def get_cover_url(self, release_id: str) -> str | None: ...


@runtime_checkable
class IFingerprintProvider(Protocol):
    """
    Proveedor de identificación por huella de audio (AcoustID, etc.).
    """

    def identify(self, file_path: str) -> list[dict]: ...


# ==================================================================
# File operations
# ==================================================================

@runtime_checkable
class IFileTagger(Protocol):
    """
    Lector/escritor de tags en archivos de audio.
    Implementado por: FileTagger (mutagen).
    """

    def read_tags(self, file_path: str) -> dict: ...
    def write_tags(self, file_path: str, tags: dict) -> None: ...
    def read_embedded_cover(self, file_path: str) -> bytes | None: ...
    def write_embedded_cover(self, file_path: str, image_data: bytes) -> None: ...


@runtime_checkable
class ILibraryScanner(Protocol):
    """
    Escaneador de directorios para importar archivos de audio.
    """

    def scan(self, directory: str) -> list[str]:
        """Retorna rutas de todos los archivos de audio encontrados."""
        ...


# ==================================================================
# CD operations
# ==================================================================

@runtime_checkable
class ICDReader(Protocol):
    """
    Lector de información básica del CD físico.
    Implementado por: CDReader (discid).
    """

    def read_disc(self, drive: str = "") -> CDDisc: ...
    def list_drives(self) -> list[str]: ...


@runtime_checkable
class ICDRipper(Protocol):
    """
    Ripeador de CD a archivos de audio.
    """

    def rip_track(
        self,
        disc: CDDisc,
        track_number: int,
        output_path: str,
        format: str = "flac",
    ) -> None: ...

    def rip_all(
        self,
        disc: CDDisc,
        output_dir: str,
        format: str = "flac",
    ) -> None: ...
