"""
VLCPlayer — Implementación de IAudioPlayer usando python-vlc (libVLC).
"""
from __future__ import annotations

import logging
import os
import sys

import vlc

from audiorep.domain.track import Track, TrackSource

logger = logging.getLogger(__name__)


def _find_vlc_plugins() -> None:
    """En bundle PyInstaller, apunta VLC_PLUGIN_PATH al directorio de plugins."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        plugins_dir = os.path.join(base, "plugins")
        if os.path.isdir(plugins_dir):
            os.environ.setdefault("VLC_PLUGIN_PATH", plugins_dir)


_find_vlc_plugins()


class VLCPlayer:
    """
    Reproductor de audio basado en libVLC.

    Implementa IAudioPlayer.
    """

    def __init__(self) -> None:
        self._instance = vlc.Instance("--no-video", "--quiet")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        logger.debug("VLCPlayer inicializado.")

    # ------------------------------------------------------------------
    # IAudioPlayer
    # ------------------------------------------------------------------

    def play(self, track: Track) -> None:
        """Reproduce un archivo de audio local o una pista de CD (CDDA)."""
        if not track.file_path:
            logger.warning("VLCPlayer.play: track sin file_path")
            return
        media = self._instance.media_new(track.file_path)
        if track.source == TrackSource.CD and track.track_number:
            # Para CD: VLC requiere el número de pista como media option,
            # no como parte del URI. El URI es solo cdda:///D:/ (dispositivo).
            media.add_option(f":cdda-track={track.track_number}")
            logger.debug("VLCPlayer: play CD pista %d desde '%s'", track.track_number, track.file_path)
        else:
            logger.debug("VLCPlayer: play '%s'", track.file_path)
        self._player.set_media(media)
        self._player.play()

    def play_url(self, url: str) -> None:
        """Reproduce un stream de URL (radio, HTTP, M3U, etc.)."""
        media = self._instance.media_new(url)
        self._player.set_media(media)
        self._player.play()
        logger.debug("VLCPlayer: play_url '%s'", url)

    def pause(self) -> None:
        self._player.pause()

    def resume(self) -> None:
        if self._player.get_state() == vlc.State.Paused:
            self._player.pause()  # VLC toggle

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        duration = self.get_duration_ms()
        if duration > 0:
            self._player.set_position(position_ms / duration)

    def get_position_ms(self) -> int:
        return max(0, self._player.get_time())

    def get_duration_ms(self) -> int:
        return max(0, self._player.get_length())

    def set_volume(self, volume: int) -> None:
        self._player.audio_set_volume(max(0, min(100, volume)))

    def get_volume(self) -> int:
        return self._player.audio_get_volume()

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing() == 1

    @property
    def is_paused(self) -> bool:
        return self._player.get_state() == vlc.State.Paused
