"""CoverArtClient — Descarga portadas desde Cover Art Archive."""
from __future__ import annotations

import logging
from pathlib import Path

import requests

from audiorep.core.utils import ensure_dir

logger = logging.getLogger(__name__)
_TIMEOUT = 10


class CoverArtClient:
    def __init__(self, cache_dir: str = "data/covers") -> None:
        self._cache_dir = Path(cache_dir)
        ensure_dir(self._cache_dir)

    def get_cover(self, release_id: str) -> bytes | None:
        cache_path = self._cache_dir / f"{release_id}.jpg"
        if cache_path.exists():
            return cache_path.read_bytes()
        url = f"https://coverartarchive.org/release/{release_id}/front-500"
        try:
            resp = requests.get(url, timeout=_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            data = resp.content
            cache_path.write_bytes(data)
            return data
        except Exception as exc:
            logger.warning("CoverArtClient: no se pudo descargar portada %s: %s", release_id, exc)
            return None

    def get_cover_from_url(self, url: str) -> bytes | None:
        try:
            resp = requests.get(url, timeout=_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.warning("CoverArtClient.get_cover_from_url: %s", exc)
            return None
