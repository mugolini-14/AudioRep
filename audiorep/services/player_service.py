"""
PlayerService — Controla la reproducción de audio.

Responsabilidades:
    - Gestionar la cola de reproducción (tracks).
    - Delegar llamadas de play/pause/stop al IAudioPlayer.
    - Emitir señales de app_events al cambiar el estado.
    - Actualizar play_count en el repositorio cuando termina una pista.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, QTimer

from audiorep.core.events import app_events
from audiorep.core.interfaces import IAudioPlayer, ITrackRepository
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class _IncrementPlayCountWorker(QThread):
    """Worker de vida corta para actualizar play_count sin bloquear la UI."""

    def __init__(self, repo: ITrackRepository, track_id: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._track_id = track_id
        self.finished.connect(self.deleteLater)

    def run(self) -> None:
        try:
            self._repo.increment_play_count(self._track_id)
        except Exception as exc:
            logger.warning("No se pudo actualizar play_count: %s", exc)


class PlayerService(QObject):
    """
    Servicio de reproducción de música local y CD.

    Args:
        player:     Implementación de IAudioPlayer (VLCPlayer).
        track_repo: Repositorio de pistas para actualizar play_count.
    """

    def __init__(
        self,
        player: IAudioPlayer,
        track_repo: ITrackRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._track_repo = track_repo
        self._queue: list[Track] = []
        self._current_index: int = -1
        self._current_track: Track | None = None
        self._finish_pending: bool = False   # evita que el timer dispare _on_track_finished varias veces

        # Poll position every 200 ms (reduce track-end detection latency)
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._poll_position)
        self._timer.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_track(self) -> Track | None:
        return self._current_track

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    def set_queue(self, tracks: list[Track], start_index: int = 0) -> None:
        """Reemplaza la cola y comienza a reproducir desde start_index."""
        self._queue = list(tracks)
        self._current_index = start_index
        if self._queue:
            self._play_current()

    def play(self, track: Track) -> None:
        """Reproduce una pista específica (sin modificar la cola)."""
        self._current_track = track
        self._player.play(track)
        app_events.track_changed.emit(track)
        app_events.playback_started.emit()
        logger.info("Reproduciendo: %s", track)

    def pause(self) -> None:
        if self._player.is_playing:
            self._player.pause()
            app_events.playback_paused.emit()

    def resume(self) -> None:
        if self._player.is_paused:
            self._player.resume()
            app_events.playback_resumed.emit()

    def stop(self) -> None:
        self._player.stop()
        app_events.playback_stopped.emit()

    def next_track(self) -> None:
        if not self._queue:
            return
        if self._current_index < len(self._queue) - 1:
            self._current_index += 1
            self._play_current()

    def previous_track(self) -> None:
        if not self._queue:
            return
        if self._current_index > 0:
            self._current_index -= 1
            self._play_current()

    def seek(self, position_ms: int) -> None:
        self._player.seek(position_ms)

    def set_volume(self, volume: int) -> None:
        self._player.set_volume(volume)
        app_events.volume_changed.emit(volume)

    def get_volume(self) -> int:
        return self._player.get_volume()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _poll_position(self) -> None:
        if not self._player.is_playing and not self._player.is_paused:
            return
        pos = self._player.get_position_ms()
        dur = self._player.get_duration_ms()
        if dur > 0:
            app_events.position_changed.emit(pos, dur)
            # Auto-advance cuando la pista termina (últimos 600 ms).
            # _finish_pending evita que el timer lo llame varias veces seguidas.
            if not self._finish_pending and pos > 0 and pos >= dur - 600:
                self._finish_pending = True
                self._on_track_finished()

    def _on_track_finished(self) -> None:
        if self._current_track and self._current_track.id is not None:
            worker = _IncrementPlayCountWorker(
                self._track_repo, self._current_track.id, self
            )
            worker.start()
        app_events.track_finished.emit()
        self.next_track()

    def _play_current(self) -> None:
        self._finish_pending = False   # reset al iniciar pista nueva
        if 0 <= self._current_index < len(self._queue):
            track = self._queue[self._current_index]
            self.play(track)
