"""
Backend de reproducción de audio usando libVLC (python-vlc).

Implementa IAudioPlayer.

Requisitos del sistema:
    - VLC Media Player instalado (libvlc.dll en Windows).
    - python-vlc en el entorno Python.

Notas de diseño:
    - La posición se actualiza mediante un QTimer que hace polling a VLC
      cada 500 ms. Esto es más simple y seguro que usar callbacks de VLC
      desde hilos externos al event loop de Qt.
    - El evento MediaPlayerEndReached de VLC llega en el hilo de VLC;
      se re-despacha al hilo de Qt con QTimer.singleShot(0, ...).
    - El volumen se persiste internamente para restaurarlo tras un stop/play.
"""
from __future__ import annotations

import logging

import vlc  # type: ignore[import-untyped]
from PyQt6.QtCore import QObject, QTimer

from audiorep.core.events import app_events
from audiorep.domain.track import Track, TrackSource

logger = logging.getLogger(__name__)

# Intervalo de polling de posición en ms
_POSITION_POLL_MS = 500


class VLCPlayer(QObject):
    """
    Reproductor de audio basado en libVLC.

    Hereda de QObject para poder usar QTimer interno.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Instancia VLC global (una por aplicación)
        self._instance: vlc.Instance = vlc.Instance("--no-xlib")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._current_track: Track | None = None
        self._volume: int = 80

        # Timer para emitir position_changed periódicamente
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POSITION_POLL_MS)
        self._poll_timer.timeout.connect(self._on_poll_timer)

        # Suscribirse al evento de fin de pista de VLC
        em = self._player.event_manager()
        em.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_end_reached)
        em.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error)

        # Aplicar volumen inicial
        self._player.audio_set_volume(self._volume)
        logger.debug("VLCPlayer iniciado.")

    # ------------------------------------------------------------------
    # IAudioPlayer — reproducción
    # ------------------------------------------------------------------

    def play(self, track: Track) -> None:
        """
        Inicia la reproducción de una pista.

        Soporta:
            - Archivos locales (LOCAL, RIPPED): usa la ruta del archivo.
            - Pistas de CD (CD): usa MRL cdda://drive@track_number.
        """
        mrl = self._build_mrl(track)
        if not mrl:
            logger.error("No se pudo construir el MRL para la pista: %r", track.title)
            app_events.error_occurred.emit(
                "Error de reproducción",
                f"No hay ruta disponible para '{track.title}'.",
            )
            return

        media = self._instance.media_new(mrl)
        self._player.set_media(media)
        self._player.audio_set_volume(self._volume)
        self._player.play()
        self._current_track = track
        self._poll_timer.start()

        logger.debug("Reproduciendo: %r — MRL: %s", track.title, mrl)
        app_events.playback_started.emit()

    def pause(self) -> None:
        """Pausa la reproducción en curso."""
        if self._player.is_playing():
            self._player.set_pause(1)
            self._poll_timer.stop()
            app_events.playback_paused.emit()
            logger.debug("Reproducción pausada.")

    def resume(self) -> None:
        """Reanuda la reproducción pausada."""
        if self.is_paused:
            self._player.set_pause(0)
            self._poll_timer.start()
            app_events.playback_resumed.emit()
            logger.debug("Reproducción reanudada.")

    def stop(self) -> None:
        """Detiene la reproducción y libera el recurso de media."""
        self._poll_timer.stop()
        self._player.stop()
        self._current_track = None
        app_events.playback_stopped.emit()
        logger.debug("Reproducción detenida.")

    def seek(self, position_ms: int) -> None:
        """Salta a la posición indicada en milisegundos."""
        duration = self.get_duration_ms()
        if duration <= 0:
            return
        # VLC usa posición relativa en [0.0, 1.0]
        relative = max(0.0, min(1.0, position_ms / duration))
        self._player.set_position(relative)

    # ------------------------------------------------------------------
    # IAudioPlayer — estado
    # ------------------------------------------------------------------

    def get_position_ms(self) -> int:
        """Posición actual en milisegundos."""
        pos = self._player.get_time()
        return max(0, pos)

    def get_duration_ms(self) -> int:
        """Duración total en milisegundos."""
        dur = self._player.get_length()
        return max(0, dur)

    def set_volume(self, volume: int) -> None:
        """Ajusta el volumen (0–100)."""
        self._volume = max(0, min(100, volume))
        self._player.audio_set_volume(self._volume)
        app_events.volume_changed.emit(self._volume)

    def get_volume(self) -> int:
        return self._volume

    @property
    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    @property
    def is_paused(self) -> bool:
        state = self._player.get_state()
        return state == vlc.State.Paused

    @property
    def current_track(self) -> Track | None:
        return self._current_track

    # ------------------------------------------------------------------
    # Callbacks internos
    # ------------------------------------------------------------------

    def _on_poll_timer(self) -> None:
        """Emite position_changed cada _POSITION_POLL_MS ms."""
        position = self.get_position_ms()
        duration = self.get_duration_ms()
        app_events.position_changed.emit(position, duration)

    def _on_vlc_end_reached(self, event: vlc.Event) -> None:
        """
        Callback de VLC: la pista terminó de reproducirse.
        Viene en el hilo de VLC; se re-despacha al event loop de Qt.
        """
        QTimer.singleShot(0, self._emit_track_finished)

    def _emit_track_finished(self) -> None:
        """Se ejecuta en el hilo de Qt después de que la pista terminó."""
        self._poll_timer.stop()
        logger.debug("Pista finalizada: %r", self._current_track and self._current_track.title)
        app_events.track_finished.emit()

    def _on_vlc_error(self, event: vlc.Event) -> None:
        """Callback de VLC: error de reproducción."""
        title = self._current_track.title if self._current_track else "desconocida"
        QTimer.singleShot(
            0,
            lambda: app_events.error_occurred.emit(
                "Error de reproducción",
                f"VLC reportó un error al reproducir '{title}'.",
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_mrl(track: Track) -> str | None:
        """
        Construye el MRL (Media Resource Locator) para VLC.

        - Archivos locales: ruta del sistema de archivos.
        - CD: cdda://drive@track_number  (ej. cdda://D:@3 en Windows).
        """
        if track.source == TrackSource.CD:
            # file_path almacena la letra de la unidad (ej. "D:")
            drive = track.file_path or ""
            return f"cdda://{drive}@{track.track_number}"
        return track.file_path

    def __del__(self) -> None:
        """Libera recursos de VLC al destruir el objeto."""
        try:
            self._poll_timer.stop()
            self._player.stop()
            self._player.release()
            self._instance.release()
        except Exception:
            pass
