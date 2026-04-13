"""MusicBrainzClient — Implementa IMetadataProvider usando musicbrainzngs."""
from __future__ import annotations

import logging

import musicbrainzngs

logger = logging.getLogger(__name__)


class MusicBrainzClient:
    def __init__(self, app_name: str = "AudioRep", app_version: str = "0.20.0") -> None:
        musicbrainzngs.set_useragent(app_name, app_version, "https://github.com/mugolini-14/AudioRep")

    def search_by_disc_id(self, disc_id: str) -> list[dict]:
        try:
            result = musicbrainzngs.get_releases_by_discid(disc_id, includes=["artists", "recordings"])
            releases = result.get("disc", {}).get("release-list", []) or result.get("release-list", [])
            return releases
        except Exception as exc:
            logger.warning("MusicBrainzClient.search_by_disc_id: %s", exc)
            return []

    def search_album(self, artist: str, title: str) -> list[dict]:
        try:
            result = musicbrainzngs.search_releases(artist=artist, release=title, limit=10)
            return result.get("release-list", [])
        except Exception as exc:
            logger.warning("MusicBrainzClient.search_album: %s", exc)
            return []

    def get_track_info(self, recording_id: str) -> dict | None:
        try:
            result = musicbrainzngs.get_recording_by_id(recording_id, includes=["artists", "releases"])
            return result.get("recording")
        except Exception as exc:
            logger.warning("MusicBrainzClient.get_track_info: %s", exc)
            return None

    def get_cover_url(self, release_id: str) -> str | None:
        return f"https://coverartarchive.org/release/{release_id}/front"
