"""
PlayerController — Bisagra entre la UI de reproducción y el PlayerService.

Responsabilidades:
    - Conectar las señales de PlayerBar y NowPlaying con los métodos
      del PlayerService.
    - Escuchar los eventos globales (app_events) y actualizar los widgets
      en consecuencia.
    - Mantener la coherencia visual del estado (playing/paused/stopped).

No contiene lógica de negocio; delega todo al service.
No accede a la BD ni a infrastructure directamente.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.track import Track
from audiorep.services.player_service import PlayerService, RepeatMode
from audiorep.ui.widgets.now_playing import NowPlaying
from audiorep.ui.widgets.player_bar import PlayerBar

logger = logging.getLogger(__name__)


class PlayerController:
    """
    Controller de reproducción.

    Args:
        service:     El PlayerService que realiza la reproducción.
        player_bar:  Widget de controles (botones + sliders).
        now_playing: Widget de información de la pista actual.
    """

    def __init__(
        self,
        service: PlayerService,
        player_bar: PlayerBar,
        now_playing: NowPlaying,
    ) -> None:
        self._service     = service
        self._player_bar  = player_bar
        self._now_playing = now_playing

        self._connect_player_bar()
        self._connect_app_events()

        logger.debug("PlayerController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: PlayerBar → Service
    # ------------------------------------------------------------------

    def _connect_player_bar(self) -> None:
        """Conecta las señales de los widgets con los métodos del service."""
        bar = self._player_bar

        bar.play_pause_clicked.connect(self._on_play_pause)
        bar.stop_clicked.connect(self._on_stop)
        bar.next_clicked.connect(self._service.next_track)
        bar.previous_clicked.connect(self._service.previous_track)
        bar.seek_requested.connect(self._service.seek)
        bar.volume_changed.connect(self._service.set_volume)
        bar.shuffle_toggled.connect(self._on_shuffle_toggled)
        bar.repeat_changed.connect(self._on_repeat_changed)

    # ------------------------------------------------------------------
    # Conexiones: app_events → Widgets
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        """Conecta los eventos globales con los métodos de actualización de UI."""
        app_events.track_changed.connect(self._on_track_changed)
        app_events.playback_started.connect(self._on_playback_started)
        app_events.playback_paused.connect(self._on_playback_paused)
        app_events.playback_resumed.connect(self._on_playback_resumed)
        app_events.playback_stopped.connect(self._on_playback_stopped)
        app_events.position_changed.connect(self._on_position_changed)

    # ------------------------------------------------------------------
    # Handlers: PlayerBar → Service
    # ------------------------------------------------------------------

    def _on_play_pause(self) -> None:
        """Alterna entre play y pause según el estado actual."""
        if self._service.is_playing:
            self._service.pause()
        else:
            self._service.play()

    def _on_stop(self) -> None:
        self._service.stop()
        self._player_bar.reset()
        self._now_playing.clear()

    def _on_shuffle_toggled(self, enabled: bool) -> None:
        self._service.shuffle = enabled
        logger.debug("Shuffle: %s", enabled)

    def _on_repeat_changed(self, mode_value: str) -> None:
        self._service.repeat = RepeatMode(mode_value)
        logger.debug("Repeat: %s", mode_value)

    # ------------------------------------------------------------------
    # Handlers: app_events → Widgets
    # ------------------------------------------------------------------

    def _on_track_changed(self, track: Track) -> None:
        """Nueva pista en reproducción: actualizar NowPlaying."""
        self._now_playing.update_track(track)
        logger.debug("UI: pista cambiada → %r", track.title)

    def _on_playback_started(self) -> None:
        self._player_bar.set_playing(True)

    def _on_playback_paused(self) -> None:
        self._player_bar.set_playing(False)

    def _on_playback_resumed(self) -> None:
        self._player_bar.set_playing(True)

    def _on_playback_stopped(self) -> None:
        self._player_bar.set_playing(False)
        self._player_bar.reset()

    def _on_position_changed(self, position_ms: int, duration_ms: int) -> None:
        self._player_bar.update_position(position_ms, duration_ms)
