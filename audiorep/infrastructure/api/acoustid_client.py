"""AcoustIDClient — Implementa IFingerprintProvider usando pyacoustid."""
from __future__ import annotations

import logging

import acoustid

logger = logging.getLogger(__name__)


class AcoustIDClient:
    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def identify(self, file_path: str) -> list[dict]:
        if not self._api_key:
            logger.warning("AcoustIDClient: no hay API key configurada.")
            return []
        try:
            results = []
            for score, recording_id, title, artist in acoustid.match(self._api_key, file_path):
                results.append({
                    "score": score,
                    "recording_id": recording_id,
                    "title": title or "",
                    "artist": artist or "",
                })
            return results
        except Exception as exc:
            logger.warning("AcoustIDClient.identify: %s", exc)
            return []
