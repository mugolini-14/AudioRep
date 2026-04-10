"""
PlayerService — Servicio de reproducción de AudioRep.

Responsabilidades:
    - Gestionar la cola de reproducción (queue).
    - Controlar play / pause / resume / stop / next / previous.
    - Modos de reproducción: shuffle y repeat (none / one / all).
    - Mantener historial de pistas reproducidas.
    - Incrementar el play_count en la BD al cambiar de pista.
    - Delegar la reproducción efectiva a IAudioPlayer (VLCPlayer).
    - Comunicarse con el resto de la app a través de app_events.

Esta clase NO importa nada de PyQt6 ni de VLC directamente;
recibe sus dependencias via inyección en el constructor.
"""
from __future__ import annotations

import logging
import random
from enum import Enum

from audiorep.core.events import app_events
from audiorep.core.interfaces import IAudioPlayer, ITrackRepository
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class RepeatMode(str, Enum):
    """Modos de repetición de la cola."""
    NONE = "none"   # Sin repetición
    ONE  = "one"    # Repite la pista actual indefinidamente
    ALL  = "all"    # Repite la cola completa al terminar


class PlayerService:
    """
    Servicio central de reproducción.

    Args:
        player:     Implementación de IAudioPlayer (ej. VLCPlayer).
        track_repo: Repositorio de pistas (para incrementar play_count).
    """

    def __init__(
        self,
        player: IAudioPlayer,
        track_repo: ITrackRepository,
    ) -> None:
        self._player     = player
        self._track_repo = track_repo

        # ── Estado de la cola ──────────────────────────────────────────
        self._queue: list[Track] = []          # pistas en orden original
        self._queue_index: int = -1            # índice actual en _queue
        self._shuffle_indices: list[int] = []  # índices permutados para shuffle
        self._shuffle_pos: int = -1            # posición actual en shuffle

        # ── Historial (para Previous) ──────────────────────────────────
        self._history: list[Track] = []
        self._MAX_HISTORY = 200

        # ── Modos ─────────────────────────────────────────────────────
        self._shuffle: bool = False
        self._repeat: RepeatMode = RepeatMode.NONE

        # ── Escuchar eventos del player ────────────────────────────────
        app_events.track_finished.connect(self._on_track_finished)

        logger.debug("PlayerService iniciado.")

    # ------------------------------------------------------------------
    # Cola de reproducción
    # ------------------------------------------------------------------

    def set_queue(self, tracks: list[Track], start_index: int = 0) -> None:
        """
        Reemplaza la cola actual y comienza a reproducir desde start_index.

        Args:
            tracks:      Lista de pistas a encolar.
            start_index: Índice de la pista con la que arrancar.
        """
        if not tracks:
            return
        self._queue = list(tracks)
        self._rebuild_shuffle_indices()
        self._queue_index = max(0, min(start_index, len(self._queue) - 1))
        if self._shuffle:
            # Poner start_index al principio del orden aleatorio
            if start_index in self._shuffle_indices:
                self._shuffle_indices.remove(start_index)
                self._shuffle_indices.insert(0, start_index)
            self._shuffle_pos = 0
        self._play_current()

    def add_to_queue(self, track: Track) -> None:
        """Agrega una pista al final de la cola sin interrumpir la reproducción."""
        self._queue.append(track)
        if self._shuffle:
            self._shuffle_indices.append(len(self._queue) - 1)

    def clear_queue(self) -> None:
        """Vacía la cola y detiene la reproducción."""
        self.stop()
        self._queue.clear()
        self._queue_index = -1
        self._shuffle_indices.clear()
        self._shuffle_pos = -1

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    @property
    def current_track(self) -> Track | None:
        """La pista que se está reproduciendo actualmente, o None."""
        if 0 <= self._queue_index < len(self._queue):
            return self._queue[self._queue_index]
        return None

    @property
    def current_index(self) -> int:
        """Índice de la pista actual en la cola original."""
        return self._queue_index

    # ------------------------------------------------------------------
    # Controles de reproducción
    # ------------------------------------------------------------------

    def play(self) -> None:
        """
        Arranca o reanuda la reproducción.
        - Si está pausado: reanuda.
        - Si no hay pista: empieza desde el inicio de la cola.
        """
        if self._player.is_paused:
            self._player.resume()
        elif not self._player.is_playing and self._queue:
            if self._queue_index < 0:
                self._queue_index = 0
            self._play_current()

    def pause(self) -> None:
        """Pausa la reproducción en curso."""
        if self._player.is_playing:
            self._player.pause()

    def stop(self) -> None:
        """Detiene la reproducción completamente."""
        self._player.stop()

    def next_track(self) -> None:
        """Avanza a la siguiente pista de la cola."""
        next_index = self._resolve_next_index(user_requested=True)
        if next_index is None:
            self.stop()
            return
        self._queue_index = next_index
        if self._shuffle:
            self._shuffle_pos = self._shuffle_indices.index(next_index)
        self._play_current()

    def previous_track(self) -> None:
        """
        Retrocede a la pista anterior.
        - Si la posición actual > 3 s: reinicia la pista actual.
        - Si no: va a la pista anterior del historial.
        """
        if self._player.get_position_ms() > 3_000:
            self._player.seek(0)
            return
        if self._history:
            prev = self._history.pop()
            # Buscar el índice en la cola
            try:
                self._queue_index = self._queue.index(prev)
            except ValueError:
                # La pista ya no está en la cola, reproducirla directamente
                self._queue.insert(self._queue_index, prev)
            self._play_current()

    def play_track_at(self, index: int) -> None:
        """Reproduce la pista en el índice dado de la cola."""
        if 0 <= index < len(self._queue):
            self._queue_index = index
            if self._shuffle:
                try:
                    self._shuffle_pos = self._shuffle_indices.index(index)
                except ValueError:
                    self._shuffle_pos = 0
            self._play_current()

    # ------------------------------------------------------------------
    # Controles de posición y volumen
    # ------------------------------------------------------------------

    def seek(self, position_ms: int) -> None:
        """Salta a la posición indicada en milisegundos."""
        self._player.seek(position_ms)

    def set_volume(self, volume: int) -> None:
        """Ajusta el volumen (0–100)."""
        self._player.set_volume(volume)

    def get_volume(self) -> int:
        return self._player.get_volume()

    # ------------------------------------------------------------------
    # Modos de reproducción
    # ------------------------------------------------------------------

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        self._shuffle = value
        if value:
            self._rebuild_shuffle_indices()
            # Colocar la pista actual al principio
            if self._queue_index in self._shuffle_indices:
                self._shuffle_indices.remove(self._queue_index)
                self._shuffle_indices.insert(0, self._queue_index)
            self._shuffle_pos = 0
        logger.debug("Shuffle: %s", value)

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @repeat.setter
    def repeat(self, mode: RepeatMode) -> None:
        self._repeat = mode
        logger.debug("Repeat: %s", mode)

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._player.is_playing

    @property
    def is_paused(self) -> bool:
        return self._player.is_paused

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _play_current(self) -> None:
        """Reproduce la pista en _queue_index."""
        track = self.current_track
        if track is None:
            return

        # Agregar al historial antes de cambiar
        if self._history and self._history[-1] != track:
            self._history.append(track)
        elif not self._history:
            self._history.append(track)
        if len(self._history) > self._MAX_HISTORY:
            self._history.pop(0)

        logger.info("Reproduciendo: %s — %s", track.artist_name, track.title)
        self._player.play(track)
        app_events.track_changed.emit(track)

    def _on_track_finished(self) -> None:
        """
        Responde al evento track_finished emitido por el player.
        Decide qué hacer según el modo de repeat.
        """
        if self._repeat == RepeatMode.ONE:
            # Repetir la misma pista
            self._player.seek(0)
            self._player.play(self.current_track)  # type: ignore[arg-type]
            return

        # Incrementar play_count en la BD (best effort)
        if self.current_track and self.current_track.id is not None:
            try:
                self._track_repo.increment_play_count(self.current_track.id)
            except Exception as exc:
                logger.warning("No se pudo incrementar play_count: %s", exc)

        next_index = self._resolve_next_index(user_requested=False)
        if next_index is None:
            # No hay siguiente → fin de la cola
            self.stop()
            return

        self._queue_index = next_index
        if self._shuffle:
            self._shuffle_pos += 1
        self._play_current()

    def _resolve_next_index(self, *, user_requested: bool) -> int | None:
        """
        Calcula el índice de la siguiente pista.

        Args:
            user_requested: True si el usuario presionó "siguiente" manualmente
                            (en ese caso, RepeatMode.ALL siempre avanza).

        Returns:
            Índice en _queue, o None si no hay siguiente pista.
        """
        if not self._queue:
            return None

        if self._shuffle:
            next_shuffle_pos = self._shuffle_pos + 1
            if next_shuffle_pos >= len(self._shuffle_indices):
                if self._repeat == RepeatMode.ALL or user_requested:
                    # Reiniciar orden aleatorio
                    self._rebuild_shuffle_indices()
                    self._shuffle_pos = -1
                    next_shuffle_pos = 0
                else:
                    return None
            self._shuffle_pos = next_shuffle_pos
            return self._shuffle_indices[self._shuffle_pos]
        else:
            next_index = self._queue_index + 1
            if next_index >= len(self._queue):
                if self._repeat == RepeatMode.ALL or user_requested:
                    return 0
                return None
            return next_index

    def _rebuild_shuffle_indices(self) -> None:
        """Genera una permutación aleatoria de los índices de la cola."""
        indices = list(range(len(self._queue)))
        random.shuffle(indices)
        self._shuffle_indices = indices
        self._shuffle_pos = -1
