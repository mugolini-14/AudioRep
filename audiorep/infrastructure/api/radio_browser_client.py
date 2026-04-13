"""
AudioRep — Cliente para radio-browser.info.

Implementa `IRadioSearchProvider`. Accede a la API pública de radio-browser.info
para buscar y obtener emisoras de radio de internet.

API: https://api.radio-browser.info/
  - GET /json/stations/search  → búsqueda por nombre, país, genre
  - GET /json/stations/byuuid/{uuid} → emisora por ID
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

import requests

from audiorep.domain.radio_station import RadioStation

logger = logging.getLogger(__name__)

# radio-browser.info tiene múltiples servidores espejo.
# Usamos los más estables como fallback.
_API_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
]

_TIMEOUT = 10  # segundos


class RadioBrowserClient:
    """
    Cliente HTTP para la API de radio-browser.info.

    Implementa `IRadioSearchProvider`.
    Las respuestas de la API se mapean a entidades `RadioStation`.
    """

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "AudioRep/0.20 (https://github.com/mugolini-14/audiorep)",
            "Accept": "application/json",
        })
        # Seleccionar servidor al azar para distribuir carga
        self._base_url = random.choice(_API_SERVERS)
        logger.debug("RadioBrowserClient: usando servidor %s", self._base_url)

    # ------------------------------------------------------------------
    # IRadioSearchProvider
    # ------------------------------------------------------------------

    def search(
        self,
        query: str = "",
        country: str = "",
        genre: str = "",
        limit: int = 50,
    ) -> list[RadioStation]:
        """
        Busca emisoras según los criterios dados.

        Args:
            query:   Texto libre para buscar en el nombre de la emisora.
            country: Código de país ISO 3166-1 alpha-2 (ej. "AR", "US").
            genre:   Etiqueta de género (ej. "rock", "jazz", "news").
            limit:   Máximo de resultados.

        Returns:
            Lista de `RadioStation` con `id=None` (no persistidas localmente).
        """
        params: dict[str, Any] = {
            "hidebroken": "true",
            "order": "votes",
            "reverse": "true",
            "limit": limit,
        }
        if query:
            params["name"] = query
        if country:
            params["countrycode"] = country.upper()
        if genre:
            params["tag"] = genre.lower()

        data = self._get("/json/stations/search", params)
        stations = [self._dict_to_station(d) for d in data]
        logger.debug("RadioBrowserClient: búsqueda '%s' → %d resultados", query, len(stations))
        return stations

    def get_by_id(self, radio_browser_id: str) -> RadioStation | None:
        """
        Retorna la emisora con el UUID de radio-browser, o None si no existe.

        Args:
            radio_browser_id: UUID de la emisora en radio-browser.info.
        """
        data = self._get(f"/json/stations/byuuid/{radio_browser_id}", {})
        if not data:
            return None
        return self._dict_to_station(data[0])

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict) -> list[dict]:
        """Realiza una petición GET y retorna los datos como lista de dicts."""
        url = f"{self._base_url}{path}"
        try:
            response = self._session.get(url, params=params, timeout=_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.warning("RadioBrowserClient: error en GET %s — %s", url, exc)
            # Intentar con otro servidor
            return self._get_fallback(path, params)

    def _get_fallback(self, path: str, params: dict) -> list[dict]:
        """Reintenta la petición con un servidor alternativo."""
        fallbacks = [s for s in _API_SERVERS if s != self._base_url]
        for server in fallbacks:
            url = f"{server}{path}"
            try:
                response = self._session.get(url, params=params, timeout=_TIMEOUT)
                response.raise_for_status()
                logger.debug("RadioBrowserClient: fallback exitoso con %s", server)
                self._base_url = server  # usar este servidor para las próximas peticiones
                return response.json()
            except requests.RequestException as exc:
                logger.warning("RadioBrowserClient: fallback %s falló — %s", server, exc)
        logger.error("RadioBrowserClient: todos los servidores fallaron.")
        return []

    @staticmethod
    def _dict_to_station(data: dict) -> RadioStation:
        """Convierte un dict de la API en una entidad RadioStation."""
        # Intentar parsear el bitrate
        try:
            bitrate = int(data.get("bitrate", 0) or 0)
        except (ValueError, TypeError):
            bitrate = 0

        return RadioStation(
            id=None,  # no persistida todavía
            name=data.get("name", "").strip(),
            stream_url=data.get("url_resolved") or data.get("url", ""),
            country=data.get("countrycode", "") or data.get("country", ""),
            genre=data.get("tags", "").split(",")[0].strip() if data.get("tags") else "",
            logo_url=data.get("favicon", "") or "",
            is_favorite=False,
            added_at=datetime.now(),
            bitrate_kbps=bitrate,
            radio_browser_id=data.get("stationuuid", ""),
        )
