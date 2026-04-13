"""
PlaylistService — Gestiona playlists manuales e inteligentes.

Responsabilidades:
    - CRUD de playlists.
    - Agregar / quitar pistas de playlists.
    - Generar playlists inteligentes desde el repositorio de pistas.
    - Garantizar la existencia de playlists inteligentes predeterminadas.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject

from audiorep.core.interfaces import IPlaylistRepository, ITrackRepository
from audiorep.domain.playlist import Playlist
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)

_DEFAULT_SMART_PLAYLISTS = [
    {"name": "Más reproducidas", "query": {"type": "most_played", "limit": 25}},
    {"name": "Mejor valoradas",  "query": {"type": "highest_rated", "limit": 25}},
    {"name": "Añadidas recientemente", "query": {"type": "recently_added", "limit": 50}},
]


class PlaylistService(QObject):
    """
    Servicio de playlists.

    Args:
        playlist_repo: Repositorio de playlists.
        track_repo:    Repositorio de pistas (para playlists inteligentes).
    """

    def __init__(
        self,
        playlist_repo: IPlaylistRepository,
        track_repo: ITrackRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._playlist_repo = playlist_repo
        self._track_repo    = track_repo

    # ------------------------------------------------------------------
    # Smart playlists predeterminadas
    # ------------------------------------------------------------------

    def ensure_default_smart_playlists(self) -> None:
        """Crea las playlists inteligentes predeterminadas si no existen."""
        existing = {p.name for p in self._playlist_repo.get_all()}
        for definition in _DEFAULT_SMART_PLAYLISTS:
            if definition["name"] not in existing:
                pl = Playlist(
                    name=definition["name"],
                    is_smart=True,
                    smart_query=definition["query"],
                )
                self._playlist_repo.save(pl)
                logger.debug("Playlist inteligente creada: %s", pl.name)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def get_all_playlists(self) -> list[Playlist]:
        return self._playlist_repo.get_all()

    def get_playlist(self, playlist_id: int) -> Playlist | None:
        return self._playlist_repo.get_by_id(playlist_id)

    def create_playlist(self, name: str) -> Playlist:
        pl = Playlist(name=name)
        return self._playlist_repo.save(pl)

    def rename_playlist(self, playlist_id: int, new_name: str) -> None:
        pl = self._playlist_repo.get_by_id(playlist_id)
        if pl is None:
            return
        pl.name = new_name
        self._playlist_repo.save(pl)

    def delete_playlist(self, playlist_id: int) -> None:
        self._playlist_repo.delete(playlist_id)

    # ------------------------------------------------------------------
    # Gestión de pistas
    # ------------------------------------------------------------------

    def add_track(self, playlist_id: int, track_id: int) -> None:
        self._playlist_repo.add_track(playlist_id, track_id)

    def remove_track(self, playlist_id: int, track_id: int) -> None:
        self._playlist_repo.remove_track(playlist_id, track_id)

    # ------------------------------------------------------------------
    # Resolución de pistas
    # ------------------------------------------------------------------

    def get_tracks(self, playlist: Playlist) -> list[Track]:
        """
        Retorna las pistas de la playlist.
        Para playlists inteligentes aplica el query dinámico.
        """
        if playlist.is_smart:
            return self._resolve_smart(playlist.smart_query)
        tracks = []
        for entry in playlist.entries:
            track = self._track_repo.get_by_id(entry.track_id)
            if track is not None:
                tracks.append(track)
        return tracks

    def _resolve_smart(self, query: dict) -> list[Track]:
        kind  = query.get("type", "")
        limit = int(query.get("limit", 25))
        if kind == "most_played":
            return self._track_repo.get_most_played(limit)
        if kind == "highest_rated":
            return self._track_repo.get_highest_rated(limit)
        if kind == "recently_added":
            return self._track_repo.get_recently_added(limit)
        return []
