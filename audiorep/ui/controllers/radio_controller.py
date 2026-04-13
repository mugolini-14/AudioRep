"""
RadioController — Bisagra entre RadioPanel y RadioService.

Responsabilidades:
    - Conectar las señales de RadioPanel con RadioService.
    - Escuchar app_events (radio_station_changed, radio_stations_updated,
      radio_playback_started, radio_playback_stopped).
    - Actualizar RadioPanel cuando cambia el estado de reproducción o la
      lista de emisoras guardadas.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.radio_station import RadioStation
from audiorep.services.radio_service import RadioService
from audiorep.ui.widgets.radio_panel import RadioPanel

logger = logging.getLogger(__name__)


class RadioController:
    """
    Controller de radio por internet.

    Args:
        radio_service: Servicio que orquesta búsqueda, reproducción y persistencia.
        radio_panel:   Widget del panel de radio.
    """

    def __init__(
        self,
        radio_service: RadioService,
        radio_panel:   RadioPanel,
    ) -> None:
        self._service = radio_service
        self._panel   = radio_panel

        self._connect_panel()
        self._connect_service()
        self._connect_app_events()

        # Cargar emisoras guardadas al iniciar
        self._refresh_saved()

        logger.debug("RadioController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: RadioPanel → RadioService
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        panel = self._panel
        panel.search_requested.connect(self._on_search_requested)
        panel.play_requested.connect(self._on_play_requested)
        panel.stop_requested.connect(self._on_stop_requested)
        panel.save_requested.connect(self._on_save_requested)
        panel.delete_requested.connect(self._on_delete_requested)
        panel.favorite_toggled.connect(self._on_favorite_toggled)

    # ------------------------------------------------------------------
    # Conexiones: RadioService → RadioPanel
    # ------------------------------------------------------------------

    def _connect_service(self) -> None:
        self._service.search_results_ready.connect(self._on_search_results)
        self._service.search_error.connect(self._on_search_error)

    # ------------------------------------------------------------------
    # Conexiones: app_events → RadioPanel
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.radio_station_changed.connect(self._on_station_changed)
        app_events.radio_playback_started.connect(self._on_playback_started)
        app_events.radio_playback_stopped.connect(self._on_playback_stopped)
        app_events.radio_stations_updated.connect(self._refresh_saved)

    # ------------------------------------------------------------------
    # Handlers: RadioPanel
    # ------------------------------------------------------------------

    def _on_search_requested(self, query: str, country: str, genre: str) -> None:
        self._panel.set_searching(True)
        self._service.search(query=query, country=country, genre=genre)

    def _on_play_requested(self, station: RadioStation) -> None:
        logger.info("RadioController: play → '%s'", station.name)
        self._service.play(station)

    def _on_stop_requested(self) -> None:
        self._service.stop()

    def _on_save_requested(self, station: RadioStation) -> None:
        self._service.save_station(station)

    def _on_delete_requested(self, station_id: int) -> None:
        self._service.delete_station(station_id)

    def _on_favorite_toggled(self, station_id: int) -> None:
        self._service.toggle_favorite(station_id)

    # ------------------------------------------------------------------
    # Handlers: RadioService
    # ------------------------------------------------------------------

    def _on_search_results(self, stations: list[RadioStation]) -> None:
        self._panel.set_searching(False)
        self._panel.set_search_results(stations)

    def _on_search_error(self, _message: str) -> None:
        self._panel.set_searching(False)

    # ------------------------------------------------------------------
    # Handlers: app_events
    # ------------------------------------------------------------------

    def _on_station_changed(self, station: RadioStation) -> None:
        self._panel.set_now_playing(station)

    def _on_playback_started(self) -> None:
        pass  # set_now_playing ya se llama desde _on_station_changed

    def _on_playback_stopped(self) -> None:
        self._panel.set_now_playing(None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_saved(self) -> None:
        """Recarga las listas de guardadas y favoritas en el panel."""
        self._panel.set_saved_stations(self._service.get_all_stations())
        self._panel.set_favorite_stations(self._service.get_favorite_stations())
