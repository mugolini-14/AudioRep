"""
AudioRep — Contratos (Interfaces / Protocols).

Todos los contratos del sistema se definen aquí como Protocol de Python.
Los services dependen únicamente de estas abstracciones; nunca importan
clases concretas de infrastructure/.

Regla: si un service necesita una nueva dependencia externa, primero se
define el Protocol aquí y luego se implementa en infrastructure/.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.cd_disc import CDDisc
from audiorep.domain.label import Label
from audiorep.domain.playlist import Playlist
from audiorep.domain.eq_preset import EqPreset
from audiorep.domain.radio_station import RadioStation
from audiorep.domain.track import Track


# ==================================================================
# Reproducción de audio
# ==================================================================

@runtime_checkable
class IAudioPlayer(Protocol):
    """Reproductor de audio. Implementado por VLCPlayer."""

    def play(self, track: Track) -> None: ...
    def play_url(self, url: str) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def seek(self, position_ms: int) -> None: ...
    def get_position_ms(self) -> int: ...
    def get_duration_ms(self) -> int: ...
    def set_volume(self, volume: int) -> None: ...
    def get_volume(self) -> int: ...

    @property
    def is_playing(self) -> bool: ...

    @property
    def is_paused(self) -> bool: ...


# ==================================================================
# Repositories
# ==================================================================

class ITrackRepository(Protocol):
    """Acceso a datos de pistas. Implementado por TrackRepository."""

    def get_by_id(self, track_id: int) -> Track | None: ...
    def get_all(self) -> list[Track]: ...
    def search(self, query: str) -> list[Track]: ...
    def save(self, track: Track) -> Track: ...
    def delete(self, track_id: int) -> None: ...
    def update_tags(self, track: Track) -> None: ...
    def get_most_played(self, limit: int = 25) -> list[Track]: ...
    def get_highest_rated(self, limit: int = 25) -> list[Track]: ...
    def get_recently_added(self, limit: int = 50) -> list[Track]: ...
    def increment_play_count(self, track_id: int) -> None: ...


class IAlbumRepository(Protocol):
    """Acceso a datos de álbumes. Implementado por AlbumRepository."""

    def get_by_id(self, album_id: int) -> Album | None: ...
    def get_all(self) -> list[Album]: ...
    def search(self, query: str) -> list[Album]: ...
    def save(self, album: Album) -> Album: ...
    def delete(self, album_id: int) -> None: ...
    def get_or_create(self, title: str, artist_id: int, artist_name: str) -> Album: ...


class IArtistRepository(Protocol):
    """Acceso a datos de artistas. Implementado por ArtistRepository."""

    def get_by_id(self, artist_id: int) -> Artist | None: ...
    def get_all(self) -> list[Artist]: ...
    def search(self, query: str) -> list[Artist]: ...
    def save(self, artist: Artist) -> Artist: ...
    def delete(self, artist_id: int) -> None: ...
    def get_or_create(self, name: str) -> Artist: ...


class IPlaylistRepository(Protocol):
    """Acceso a datos de playlists. Implementado por PlaylistRepository."""

    def get_by_id(self, playlist_id: int) -> Playlist | None: ...
    def get_all(self) -> list[Playlist]: ...
    def save(self, playlist: Playlist) -> Playlist: ...
    def delete(self, playlist_id: int) -> None: ...
    def add_track(self, playlist_id: int, track_id: int) -> None: ...
    def remove_track(self, playlist_id: int, track_id: int) -> None: ...


class IRadioStationRepository(Protocol):
    """Acceso a datos de emisoras guardadas. Implementado por RadioStationRepository."""

    def get_by_id(self, station_id: int) -> RadioStation | None: ...
    def get_all(self) -> list[RadioStation]: ...
    def get_favorites(self) -> list[RadioStation]: ...
    def save(self, station: RadioStation) -> RadioStation: ...
    def delete(self, station_id: int) -> None: ...
    def set_favorite(self, station_id: int, is_favorite: bool) -> None: ...


class ILabelRepository(Protocol):
    """Acceso a datos de sellos discográficos. Implementado por LabelRepository."""

    def get_by_id(self, label_id: int) -> Label | None: ...
    def get_by_name(self, name: str) -> Label | None: ...
    def get_all(self) -> list[Label]: ...
    def save(self, label: Label) -> Label: ...
    def delete(self, label_id: int) -> None: ...
    def upsert_country(self, name: str, country: str) -> None: ...
    def get_country_map(self) -> dict[str, str]: ...


# ==================================================================
# Proveedores externos
# ==================================================================

class IMetadataProvider(Protocol):
    """
    Proveedor de metadatos musicales online.
    Implementado por MusicBrainzClient.
    """

    def search_by_disc_id(self, disc_id: str) -> list[dict]: ...
    def search_album(self, artist: str, title: str) -> list[dict]: ...
    def get_track_info(self, recording_id: str) -> dict | None: ...
    def get_cover_url(self, release_id: str) -> str | None: ...


class IFingerprintProvider(Protocol):
    """
    Identificación de audio por huella cromática.
    Implementado por AcoustIDClient.
    """

    def identify(self, file_path: str) -> list[dict]: ...


class IRadioSearchProvider(Protocol):
    """
    Búsqueda de emisoras de radio en un directorio online.
    Implementado por RadioBrowserClient.
    """

    def search(
        self,
        query: str = "",
        country: str = "",
        genre: str = "",
        limit: int = 50,
    ) -> list[RadioStation]: ...

    def get_by_id(self, radio_browser_id: str) -> RadioStation | None: ...


# ==================================================================
# Filesystem
# ==================================================================

class IFileTagger(Protocol):
    """
    Lectura y escritura de tags en archivos de audio.
    Implementado por FileTagger (mutagen).
    """

    def read_tags(self, file_path: str) -> dict: ...
    def write_tags(self, file_path: str, tags: dict) -> None: ...
    def read_embedded_cover(self, file_path: str) -> bytes | None: ...
    def write_embedded_cover(self, file_path: str, image_data: bytes) -> None: ...


class ILibraryScanner(Protocol):
    """
    Escáner de directorios para encontrar archivos de audio.
    Implementado por FileScanner.
    """

    def scan(self, directory: str) -> list[str]: ...


# ==================================================================
# CD
# ==================================================================

class ICDReader(Protocol):
    """
    Lectura de CD físico (Disc ID).
    Implementado por CDReader (discid).
    """

    def read_disc(self, drive: str = "") -> CDDisc: ...
    def list_drives(self) -> list[str]: ...


class ICDLookupProvider(Protocol):
    """
    Proveedor de metadatos de CD para búsqueda manual.
    Implementado por MusicBrainzClient y GnuDBClient.

    Formato normalizado de resultado:
        {
            "album": str, "artist": str, "year": str, "genre": str,
            "release_id": str,
            "tracks": [{"number": int, "title": str, "recording_id": str, "duration_ms": int}]
        }
    """

    name: str   # Nombre para mostrar en el desplegable "Servicio"

    def search_disc(self, disc: CDDisc) -> list[dict]: ...


class ICDRipper(Protocol):
    """
    Extracción de pistas de CD a archivos de audio.
    Implementado por CDRipper (libVLC sout).
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


# ==================================================================
# Ecualizador
# ==================================================================

class IEqPresetRepository(Protocol):
    """
    Repositorio de presets de usuario del ecualizador.
    Implementado por EqPresetRepository (SQLite).
    """

    def get_all(self) -> list[EqPreset]: ...
    def save(self, preset: EqPreset) -> None: ...
    def delete(self, name: str) -> None: ...
