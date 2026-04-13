"""
AudioRep — Servicio de radio por internet.

Orquesta:
  - Reproducción de streams vía IAudioPlayer.play_url()
  - Búsqueda de emisoras online vía IRadioSearchProvider (worker thread)
  - Persistencia de emisoras guardadas vía IRadioStationRepository

Señales propias (para el controller):
    search_results_ready  → lista de RadioStation encontradas
    search_error          → mensaje de error durante la búsqueda

Señales globales emitidas (app_events):
    radio_station_changed
    radio_playback_started
    radio_playback_stopped
    radio_stations_updated
    status_message
    error_occurred
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import (
    IAudioPlayer,
    IRadioSearchProvider,
    IRadioStationRepository,
)
from audiorep.domain.radio_station import RadioStation

logger = logging.getLogger(__name__)


# ===========================================================================
# Worker interno — búsqueda en radio-browser.info (no bloquea el hilo UI)
# ===========================================================================

class _SearchWorker(QThread):
    """Ejecuta la búsqueda online en un hilo secundario."""

    results_ready = pyqtSignal(list)   # list[RadioStation]
    error         = pyqtSignal(str)

    def __init__(
        self,
        provider: IRadioSearchProvider,
        query: str,
        country: str,
        genre: str,
        limit: int,
    ) -> None:
        super().__init__()
        self._provider = provider
        self._query    = query
        self._country  = country
        self._genre    = genre
        self._limit    = limit

    def run(self) -> None:
        try:
            stations = self._provider.search(
                query=self._query,
                country=self._country,
                genre=self._genre,
                limit=self._limit,
            )
            self.results_ready.emit(stations)
        except Exception as exc:  # noqa: BLE001
            logger.exception("_SearchWorker: error durante la búsqueda")
            self.error.emit(str(exc))


# ===========================================================================
# RadioService
# ===========================================================================

class RadioService(QObject):
    """
    Servicio de radio por internet.

    Args:
        player:      Reproductor de audio (implementa IAudioPlayer).
        station_repo: Repositorio de emisoras guardadas.
        search_provider: Cliente de búsqueda online (radio-browser.info).
    """

    # Señales propias para que el controller actualice la UI
    search_results_ready = pyqtSignal(list)   # list[RadioStation]
    search_error         = pyqtSignal(str)

    def __init__(
        self,
        player: IAudioPlayer,
        station_repo: IRadioStationRepository,
        search_provider: IRadioSearchProvider,
    ) -> None:
        super().__init__()
        self._player          = player
        self._repo            = station_repo
        self._search_provider = search_provider

        self._current_station: RadioStation | None = None
        self._search_worker:   _SearchWorker | None = None

    # ------------------------------------------------------------------
    # Reproducción
    # ------------------------------------------------------------------

    def play(self, station: RadioStation) -> None:
        """Comienza a reproducir el stream de la emisora dada."""
        logger.info("RadioService: reproduciendo '%s' → %s", station.name, station.stream_url)
        self._current_station = station
        self._player.play_url(station.stream_url)
        app_events.radio_station_changed.emit(station)
        app_events.radio_playback_started.emit()
        app_events.status_message.emit(f"Radio: {station.name}")

    def stop(self) -> None:
        """Detiene la reproducción de radio."""
        logger.info("RadioService: stop")
        self._player.stop()
        self._current_station = None
        app_events.radio_playback_stopped.emit()
        app_events.status_message.emit("Radio detenida.")

    @property
    def current_station(self) -> RadioStation | None:
        """Emisora actualmente en reproducción, o None."""
        return self._current_station

    @property
    def is_playing(self) -> bool:
        """True si hay una emisora reproduciéndose."""
        return self._current_station is not None and self._player.is_playing

    # ------------------------------------------------------------------
    # Búsqueda online
    # ------------------------------------------------------------------

    def search(
        self,
        query: str = "",
        country: str = "",
        genre: str = "",
        limit: int = 50,
    ) -> None:
        """
        Lanza una búsqueda asíncrona en radio-browser.info.

        Los resultados se emiten mediante `search_results_ready(list[RadioStation])`.
        Si ocurre un error se emite `search_error(str)`.
        """
        # Cancelar búsqueda previa si todavía corre
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(2000)

        app_events.status_message.emit("Buscando emisoras…")

        self._search_worker = _SearchWorker(
            provider=self._search_provider,
            query=query,
            country=country,
            genre=genre,
            limit=limit,
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()

    def _on_search_results(self, stations: list[RadioStation]) -> None:
        app_events.status_message.emit(f"{len(stations)} emisoras encontradas.")
        self.search_results_ready.emit(stations)

    def _on_search_error(self, message: str) -> None:
        logger.error("RadioService: error de búsqueda — %s", message)
        app_events.error_occurred.emit("Error de búsqueda", message)
        self.search_error.emit(message)

    # ------------------------------------------------------------------
    # Gestión de emisoras guardadas
    # ------------------------------------------------------------------

    def get_all_stations(self) -> list[RadioStation]:
        """Retorna todas las emisoras guardadas por el usuario."""
        return self._repo.get_all()

    def get_favorite_stations(self) -> list[RadioStation]:
        """Retorna las emisoras marcadas como favoritas."""
        return self._repo.get_favorites()

    def save_station(self, station: RadioStation) -> RadioStation:
        """
        Guarda una emisora (nueva o existente).

        Retorna la emisora persistida (con id asignado si era nueva).
        """
        saved = self._repo.save(station)
        app_events.radio_stations_updated.emit()
        app_events.status_message.emit(f"'{saved.name}' guardada.")
        logger.info("RadioService: guardada estación id=%s '%s'", saved.id, saved.name)
        return saved

    def delete_station(self, station_id: int) -> None:
        """Elimina una emisora guardada por su id."""
        self._repo.delete(station_id)
        app_events.radio_stations_updated.emit()
        logger.info("RadioService: eliminada estación id=%d", station_id)

    def toggle_favorite(self, station_id: int) -> None:
        """Alterna el estado de favorita de la emisora."""
        station = self._repo.get_by_id(station_id)
        if station is None:
            logger.warning("RadioService: toggle_favorite — id=%d no encontrado", station_id)
            return
        new_value = not station.is_favorite
        self._repo.set_favorite(station_id, new_value)
        app_events.radio_stations_updated.emit()
        logger.debug("RadioService: station %d → is_favorite=%s", station_id, new_value)
