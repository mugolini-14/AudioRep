"""
MusicBrainzClient — Implementa IMetadataProvider e ICDLookupProvider
usando la librería musicbrainzngs.

Formato normalizado de resultados de disc lookup:
    {
        "album":      str,
        "artist":     str,
        "year":       str,          # "1994" o ""
        "genre":      str,          # MusicBrainz no tiene género, siempre ""
        "release_id": str,          # MBID del release
        "tracks": [
            {"number": int, "title": str, "recording_id": str, "duration_ms": int}
        ]
    }
"""
from __future__ import annotations

import logging

import musicbrainzngs

from audiorep.domain.cd_disc import CDDisc

logger = logging.getLogger(__name__)


def _normalize_release(release: dict) -> dict:
    """Convierte un release raw de MusicBrainzngs al formato normalizado."""
    # Título del álbum
    album = release.get("title", "")

    # Artista principal
    credits = release.get("artist-credit", [])
    artist = ""
    if credits:
        first = credits[0]
        if isinstance(first, dict):
            artist = first.get("name") or first.get("artist", {}).get("name", "")

    # Año (date puede ser "1994", "1994-05-10", etc.)
    date = release.get("date", "") or release.get("first-release-date", "")
    year = date[:4] if date else ""

    # Release ID (MBID)
    release_id = release.get("id", "")

    # Pistas: buscar en medium-list → track-list → recording
    tracks: list[dict] = []
    for medium in release.get("medium-list", []):
        for t in medium.get("track-list", []):
            rec   = t.get("recording", {})
            title = rec.get("title", "") or t.get("title", "")
            num_str = t.get("number", "") or str(t.get("position", ""))
            try:
                num = int(num_str)
            except (ValueError, TypeError):
                num = len(tracks) + 1
            duration_ms = 0
            try:
                length = rec.get("length") or t.get("length")
                if length:
                    duration_ms = int(length)
            except (ValueError, TypeError):
                pass
            tracks.append({
                "number":       num,
                "title":        title,
                "recording_id": rec.get("id", ""),
                "duration_ms":  duration_ms,
            })

    return {
        "album":      album,
        "artist":     artist,
        "year":       year,
        "genre":      "",          # MusicBrainz no expone género por release
        "release_id": release_id,
        "tracks":     tracks,
    }


class MusicBrainzClient:
    """
    Cliente de MusicBrainz.

    Implementa:
        IMetadataProvider  — para identificación automática (CDService._IdentifyWorker)
        ICDLookupProvider  — para el panel manual de metadatos (CDMetadataPanel)
    """

    name = "MusicBrainz"

    def __init__(self, app_name: str = "AudioRep", app_version: str = "0.30.0") -> None:
        musicbrainzngs.set_useragent(
            app_name, app_version, "https://github.com/mugolini-14/AudioRep"
        )

    # ------------------------------------------------------------------
    # IMetadataProvider
    # ------------------------------------------------------------------

    def search_by_disc_id(self, disc_id: str) -> list[dict]:
        """
        Busca releases por MusicBrainz Disc ID.
        Retorna lista en formato normalizado.
        """
        try:
            result = musicbrainzngs.get_releases_by_discid(
                disc_id, includes=["artists", "recordings"]
            )
            releases = (
                result.get("disc", {}).get("release-list", [])
                or result.get("release-list", [])
            )
            return [_normalize_release(r) for r in releases]
        except musicbrainzngs.ResponseError as exc:
            # 404 = disc ID no encontrado en MB
            logger.info("MusicBrainz: disc ID '%s' no encontrado (%s)", disc_id, exc)
            return []
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
            result = musicbrainzngs.get_recording_by_id(
                recording_id, includes=["artists", "releases"]
            )
            return result.get("recording")
        except Exception as exc:
            logger.warning("MusicBrainzClient.get_track_info: %s", exc)
            return None

    def get_cover_url(self, release_id: str) -> str | None:
        return f"https://coverartarchive.org/release/{release_id}/front"

    # ------------------------------------------------------------------
    # ICDLookupProvider
    # ------------------------------------------------------------------

    def search_disc(self, disc: CDDisc) -> list[dict]:
        """
        Busca el disco usando su MusicBrainz Disc ID.
        Retorna lista en formato normalizado.
        """
        return self.search_by_disc_id(disc.disc_id)
