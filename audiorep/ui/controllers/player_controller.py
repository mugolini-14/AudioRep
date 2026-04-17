"""
PlayerController — Bisagra entre PlayerBar/NowPlaying y PlayerService.

Responsabilidades:
    - Conectar señales de PlayerBar con PlayerService.
    - Escuchar app_events (track_changed, position_changed, etc.).
    - Actualizar PlayerBar y NowPlaying con el estado actual.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.track import Track
from audiorep.services.player_service import PlayerService
from audiorep.ui.widgets.now_playing import NowPlaying
from audiorep.ui.widgets.player_bar import PlayerBar

logger = logging.getLogger(__name__)


class PlayerController:
    """
    Controller del reproductor.

    Args:
        service:     PlayerService.
        player_bar:  Widget con controles de reproducción.
        now_playing: Widget con info de la pista actual.
    """

    def __init__(
        self,
        service:     PlayerService,
        player_bar:  PlayerBar,
        now_playing: NowPlaying,
    ) -> None:
        self._service     = service
        self._player_bar  = player_bar
        self._now_playing = now_playing

        self._connect_player_bar()
        self._connect_app_events()

        # Sincronizar volumen inicial (audio_get_volume devuelve -1 en modo callback)
        vol = self._service.get_volume()
        self._player_bar.set_volume(vol if vol > 0 else 100)

        logger.debug("PlayerController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: PlayerBar → PlayerService
    # ------------------------------------------------------------------

    def _connect_player_bar(self) -> None:
        bar = self._player_bar
        bar.play_pause_clicked.connect(self._on_play_pause)
        bar.stop_clicked.connect(self._service.stop)
        bar.next_clicked.connect(self._service.next_track)
        bar.previous_clicked.connect(self._service.previous_track)
        bar.seek_requested.connect(self._service.seek)
        bar.volume_changed.connect(self._service.set_volume)

    # ------------------------------------------------------------------
    # Conexiones: app_events → PlayerBar / NowPlaying
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.track_changed.connect(self._on_track_changed)
        app_events.position_changed.connect(self._player_bar.update_position)
        app_events.playback_started.connect(
            lambda: self._player_bar.set_playing(True)
        )
        app_events.playback_paused.connect(
            lambda: self._player_bar.set_playing(False)
        )
        app_events.playback_resumed.connect(
            lambda: self._player_bar.set_playing(True)
        )
        app_events.playback_stopped.connect(self._on_stopped)
        app_events.volume_changed.connect(self._player_bar.set_volume)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_play_pause(self) -> None:
        player = self._service._player
        if player.is_playing:
            self._service.pause()
        elif player.is_paused:
            self._service.resume()

    def _on_track_changed(self, track: Track) -> None:
        self._now_playing.update_track(track)
        self._player_bar.update_track(track)
        self._player_bar.set_playing(True)

    def _on_stopped(self) -> None:
        self._player_bar.set_playing(False)
        self._player_bar.reset_position()
