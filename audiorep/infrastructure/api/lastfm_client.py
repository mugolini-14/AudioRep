"""
LastFmClient — Obtiene tags de género desde Last.fm.

Requiere la librería `pylast`. Si no está instalada, todos los métodos
retornan listas vacías sin lanzar error (degradación limpia).

Uso:
    client = LastFmClient(api_key="tu_clave")
    genres = client.get_track_genres("The Beatles", "Let It Be")
    # → ["rock", "classic rock", "pop"]
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import pylast
    _PYLAST_OK = True
except ImportError:
    _PYLAST_OK = False


# Tags de Last.fm que NO son géneros musicales (excluir del resultado)
_NON_GENRE_TAGS = {
    "seen live", "favorites", "favourite", "love", "under 2000 listeners",
    "beautiful", "awesome", "amazing", "great", "good", "my favourite",
    "all time favorites", "sexy", "chill", "sad", "happy", "relaxing",
    "melancholic", "epic", "dark", "cool", "nice", "perfect",
}


class LastFmClient:
    """
    Cliente de Last.fm para obtener tags de género.

    Si `pylast` no está instalado o la API key está vacía, todos los
    métodos retornan listas vacías sin lanzar excepción.
    """

    def __init__(self, api_key: str) -> None:
        self._network: object | None = None
        if _PYLAST_OK and api_key:
            try:
                self._network = pylast.LastFMNetwork(api_key=api_key)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning("LastFmClient: no se pudo inicializar: %s", exc)

    @property
    def available(self) -> bool:
        return self._network is not None

    def get_track_genres(self, artist: str, title: str, limit: int = 5) -> list[str]:
        """Retorna los top tags de género de una pista en Last.fm."""
        if not self._network or not artist or not title:
            return []
        try:
            track = self._network.get_track(artist, title)  # type: ignore[attr-defined]
            raw_tags = track.get_top_tags(limit=limit + 5)
            return self._filter_genre_tags(raw_tags, limit)
        except Exception as exc:
            logger.debug("LastFmClient.get_track_genres(%s, %s): %s", artist, title, exc)
            return []

    def get_artist_genres(self, artist: str, limit: int = 5) -> list[str]:
        """Retorna los top tags de género de un artista en Last.fm."""
        if not self._network or not artist:
            return []
        try:
            artist_obj = self._network.get_artist(artist)  # type: ignore[attr-defined]
            raw_tags = artist_obj.get_top_tags(limit=limit + 5)
            return self._filter_genre_tags(raw_tags, limit)
        except Exception as exc:
            logger.debug("LastFmClient.get_artist_genres(%s): %s", artist, exc)
            return []

    @staticmethod
    def _filter_genre_tags(raw_tags: list, limit: int) -> list[str]:
        """Filtra tags que no son géneros y retorna los mejores `limit`."""
        result: list[str] = []
        for tag in raw_tags:
            try:
                name = tag.item.name.lower().strip()
            except Exception:
                continue
            if name and name not in _NON_GENRE_TAGS:
                result.append(name.title())
            if len(result) >= limit:
                break
        return result
