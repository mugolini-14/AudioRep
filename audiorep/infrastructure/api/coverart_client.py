"""
CoverArtClient — Descarga portadas desde Cover Art Archive.

Cover Art Archive (coverartarchive.org) aloja las imágenes asociadas
a los releases de MusicBrainz. Las URLs tienen la forma:
    https://coverartarchive.org/release/{mbid}/front-500

El cliente:
    - Descarga la imagen en bytes.
    - Cachea localmente en disco para evitar re-descargas.
    - Aplica timeout y manejo de errores de red.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import requests

from audiorep.core.exceptions import APIConnectionError

logger = logging.getLogger(__name__)

# Timeouts en segundos
_CONNECT_TIMEOUT = 5
_READ_TIMEOUT    = 15

# Tamaño de portada a pedir (250, 500, 1200 son válidas en CAA)
_COVER_SIZE = 500


class CoverArtClient:
    """
    Descarga y cachea portadas de álbumes desde Cover Art Archive.

    Args:
        cache_dir: Directorio local para guardar las portadas.
                   Se crea automáticamente si no existe.
    """

    def __init__(self, cache_dir: str = "data/covers") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "AudioRep/0.1.0"
        logger.debug("CoverArtClient listo. Cache: %s", self._cache_dir)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def fetch_cover(self, release_mbid: str) -> bytes | None:
        """
        Descarga la portada frontal de un release.
        Devuelve los bytes de la imagen, o None si no existe.

        Usa caché local: si ya fue descargada, la retorna desde disco.

        Args:
            release_mbid: MBID del release en MusicBrainz.

        Returns:
            bytes con la imagen (JPEG típicamente), o None.

        Raises:
            APIConnectionError: si hay un error de red irrecuperable.
        """
        cached = self._from_cache(release_mbid)
        if cached is not None:
            logger.debug("Portada desde caché: %s", release_mbid)
            return cached

        url = f"https://coverartarchive.org/release/{release_mbid}/front-{_COVER_SIZE}"
        logger.info("Descargando portada: %s", url)

        try:
            response = self._session.get(
                url,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                allow_redirects=True,
            )
        except requests.ConnectionError as exc:
            raise APIConnectionError("Cover Art Archive") from exc
        except requests.Timeout:
            logger.warning("Timeout descargando portada: %s", url)
            return None

        if response.status_code == 404:
            logger.debug("Portada no encontrada en CAA: %s", release_mbid)
            return None

        if response.status_code != 200:
            logger.warning(
                "Error HTTP %d al descargar portada: %s",
                response.status_code, url,
            )
            return None

        image_data = response.content
        if not image_data:
            return None

        self._save_to_cache(release_mbid, image_data)
        logger.info(
            "Portada descargada: %s (%d bytes)", release_mbid, len(image_data)
        )
        return image_data

    def fetch_cover_from_url(self, url: str) -> bytes | None:
        """
        Descarga una portada desde cualquier URL (no necesariamente CAA).
        Sin caché basada en MBID; usa el hash de la URL como clave.
        """
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cached = self._from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = self._session.get(
                url,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                allow_redirects=True,
            )
        except (requests.ConnectionError, requests.Timeout):
            logger.warning("No se pudo descargar portada desde: %s", url)
            return None

        if response.status_code != 200 or not response.content:
            return None

        self._save_to_cache(cache_key, response.content)
        return response.content

    def get_cached_path(self, release_mbid: str) -> Path | None:
        """Retorna la ruta al archivo de portada cacheado, o None."""
        path = self._cache_path(release_mbid)
        return path if path.exists() else None

    def save_cover_for_album(self, album_id: int, image_data: bytes) -> str:
        """
        Guarda la portada de un álbum específico con su album_id.
        Útil para portadas descargadas por otros medios.

        Returns:
            Ruta absoluta al archivo guardado.
        """
        path = self._cache_dir / f"album_{album_id}.jpg"
        path.write_bytes(image_data)
        return str(path)

    # ------------------------------------------------------------------
    # Caché
    # ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        """Ruta al archivo de caché para una clave dada."""
        safe_key = key.replace("-", "").replace("/", "_")[:40]
        return self._cache_dir / f"{safe_key}.jpg"

    def _from_cache(self, key: str) -> bytes | None:
        path = self._cache_path(key)
        if path.exists():
            return path.read_bytes()
        return None

    def _save_to_cache(self, key: str, data: bytes) -> None:
        self._cache_path(key).write_bytes(data)
