"""
PlaylistController — Bisagra entre PlaylistPanel y PlaylistService / PlayerService.

Responsabilidades:
    - Cargar playlists en el panel al iniciar.
    - Crear, renombrar y eliminar playlists.
    - Agregar / quitar pistas de playlists.
    - Iniciar la reproducción de una playlist.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.playlist import Playlist
from audiorep.domain.track import Track
from audiorep.services.player_service import PlayerService
from audiorep.services.playlist_service import PlaylistService
from audiorep.ui.widgets.library_panel import LibraryPanel
from audiorep.ui.widgets.playlist_panel import PlaylistPanel

logger = logging.getLogger(__name__)


class PlaylistController:
    """
    Controller de playlists.

    Args:
        playlist_service: Servicio de playlists.
        player_service:   Servicio de reproducción.
        playlist_panel:   Widget del panel de playlists.
        library_panel:    Widget de biblioteca (para obtener selección actual).
    """

    def __init__(
        self,
        playlist_service: PlaylistService,
        player_service:   PlayerService,
        playlist_panel:   PlaylistPanel,
        library_panel:    LibraryPanel,
    ) -> None:
        self._playlist_svc = playlist_service
        self._player       = player_service
        self._panel        = playlist_panel
        self._library      = library_panel

        self._connect_panel()
        self._connect_app_events()
        self._refresh_playlists()

        logger.debug("PlaylistController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        panel = self._panel
        panel.playlist_selected.connect(self._on_playlist_selected)
        panel.play_requested.connect(self._on_play_requested)
        panel.create_requested.connect(self._on_create_requested)
        panel.rename_requested.connect(self._on_rename_requested)
        panel.delete_requested.connect(self._on_delete_requested)
        panel.add_track_requested.connect(self._on_add_track_requested)
        panel.remove_track_requested.connect(self._on_remove_track_requested)

    def _connect_app_events(self) -> None:
        app_events.library_updated.connect(self._refresh_playlists)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_playlist_selected(self, playlist: Playlist) -> None:
        tracks = self._playlist_svc.get_tracks(playlist)
        self._panel.set_playlist_tracks(tracks)

    def _on_play_requested(self, playlist: Playlist, start_index: int = 0) -> None:
        tracks = self._playlist_svc.get_tracks(playlist)
        if tracks:
            self._player.set_queue(tracks, start_index=min(start_index, len(tracks) - 1))

    def _on_create_requested(self, name: str) -> None:
        self._playlist_svc.create_playlist(name)
        self._refresh_playlists()

    def _on_rename_requested(self, playlist_id: int, new_name: str) -> None:
        self._playlist_svc.rename_playlist(playlist_id, new_name)
        self._refresh_playlists()

    def _on_delete_requested(self, playlist_id: int) -> None:
        self._playlist_svc.delete_playlist(playlist_id)
        self._refresh_playlists()

    def _on_add_track_requested(self, playlist_id: int, track_id: int) -> None:
        self._playlist_svc.add_track(playlist_id, track_id)
        app_events.status_message.emit("Pista añadida a la playlist.")

    def _on_remove_track_requested(self, playlist_id: int, track_id: int) -> None:
        self._playlist_svc.remove_track(playlist_id, track_id)
        # Refrescar pistas de la playlist actualmente abierta
        playlist = self._panel.current_playlist
        if playlist:
            self._on_playlist_selected(playlist)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_playlists(self) -> None:
        playlists = self._playlist_svc.get_all_playlists()
        self._panel.set_playlists(playlists)
