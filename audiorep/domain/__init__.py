"""
Capa de dominio de AudioRep.

Exporta los modelos principales para facilitar imports.
Esta capa NO tiene dependencias de infraestructura ni de UI.
"""
from audiorep.domain.artist import Artist
from audiorep.domain.album import Album
from audiorep.domain.track import Track, AudioFormat, TrackSource
from audiorep.domain.playlist import Playlist, PlaylistEntry
from audiorep.domain.cd_disc import CDDisc, CDTrack, RipStatus

__all__ = [
    "Artist",
    "Album",
    "Track",
    "AudioFormat",
    "TrackSource",
    "Playlist",
    "PlaylistEntry",
    "CDDisc",
    "CDTrack",
    "RipStatus",
]
