"""
MusicBrainzClient — Cliente de la API de MusicBrainz.

Implementa IMetadataProvider usando la librería `musicbrainzngs`.

MusicBrainz es una base de datos musical abierta. Permite:
    - Identificar un CD por su Disc ID.
    - Buscar álbumes por artista y título.
    - Obtener información detallada de grabaciones.
    - Obtener la URL de portada (vía Cover Art Archive).

Límite de velocidad:
    MusicBrainz requiere máximo 1 petición por segundo.
    El cliente implementa un delay mínimo entre peticiones.

Documentación: https://musicbrainz.org/doc/MusicBrainz_API
"""
from __future__ import annotations

import logging
import time
from typing import Any

import musicbrainzngs  # type: ignore[import-untyped]

from audiorep.core.exceptions import APIConnectionError, APIRateLimitError

logger = logging.getLogger(__name__)

# Intervalo mínimo entre peticiones (segundos)
_MIN_REQUEST_INTERVAL = 1.1


class MusicBrainzClient:
    """
    Cliente de MusicBrainz.

    Args:
        app_name:    Nombre de la aplicación (requerido por MusicBrainz).
        app_version: Versión de la aplicación.
        contact:     URL o email de contacto (requerido por MusicBrainz).
    """

    def __init__(
        self,
        app_name: str = "AudioRep",
        app_version: str = "0.1.0",
        contact: str = "https://github.com/audiorep",
    ) -> None:
        musicbrainzngs.set_useragent(app_name, app_version, contact)
        self._last_request_time: float = 0.0
        logger.debug("MusicBrainzClient iniciado.")

    # ------------------------------------------------------------------
    # IMetadataProvider
    # ------------------------------------------------------------------

    def search_by_disc_id(self, disc_id: str) -> list[dict]:
        """
        Busca releases que coincidan con el Disc ID dado.

        Returns:
            Lista de dicts normalizados con: title, artist, year, genre,
            cover_url, musicbrainz_id, tracks.
            Lista vacía si no hay resultados.
        """
        logger.info("Buscando disc_id en MusicBrainz: %s", disc_id)
        try:
            self._throttle()
            result = musicbrainzngs.get_releases_by_discid(
                disc_id,
                includes=["artists", "recordings", "release-groups"],
            )
        except musicbrainzngs.ResponseError as exc:
            if "404" in str(exc):
                logger.info("Disc ID no encontrado en MusicBrainz: %s", disc_id)
                return []
            raise APIConnectionError("MusicBrainz") from exc
        except musicbrainzngs.NetworkError as exc:
            raise APIConnectionError("MusicBrainz") from exc

        releases = []
        raw_releases = (
            result.get("disc", {}).get("release-list", [])
            or result.get("release-list", [])
        )
        for raw in raw_releases:
            parsed = self._parse_release(raw, disc_id)
            if parsed:
                releases.append(parsed)

        logger.info("disc_id %s → %d resultado(s) en MusicBrainz.", disc_id, len(releases))
        return releases

    def search_album(self, artist: str, title: str) -> list[dict]:
        """
        Busca álbumes por artista y título.

        Returns:
            Lista de dicts normalizados (misma estructura que search_by_disc_id).
        """
        logger.info("Buscando álbum: '%s' — '%s'", artist, title)
        try:
            self._throttle()
            result = musicbrainzngs.search_releases(
                artist=artist,
                release=title,
                limit=10,
            )
        except musicbrainzngs.NetworkError as exc:
            raise APIConnectionError("MusicBrainz") from exc

        releases = []
        for raw in result.get("release-list", []):
            parsed = self._parse_release(raw)
            if parsed:
                releases.append(parsed)
        return releases

    def get_track_info(self, recording_id: str) -> dict | None:
        """
        Obtiene información detallada de una grabación por su MBID.
        """
        try:
            self._throttle()
            result = musicbrainzngs.get_recording_by_id(
                recording_id,
                includes=["artists", "releases"],
            )
        except musicbrainzngs.ResponseError:
            return None
        except musicbrainzngs.NetworkError as exc:
            raise APIConnectionError("MusicBrainz") from exc

        rec = result.get("recording", {})
        return {
            "musicbrainz_id": rec.get("id"),
            "title":          rec.get("title", ""),
            "duration_ms":    int(rec.get("length", 0)),
        }

    def get_cover_url(self, release_id: str) -> str | None:
        """
        Retorna la URL de la portada frontal en Cover Art Archive.

        No hace una petición HTTP; construye la URL directamente con el MBID.
        La URL puede o no existir; el CoverArtClient verifica antes de descargar.
        """
        if not release_id:
            return None
        return f"https://coverartarchive.org/release/{release_id}/front-500"

    # ------------------------------------------------------------------
    # Parseo de respuestas
    # ------------------------------------------------------------------

    def _parse_release(self, raw: dict, disc_id: str = "") -> dict | None:
        """Normaliza un release de MusicBrainz al formato interno."""
        release_id = raw.get("id")
        if not release_id:
            return None

        # Artista
        artist = ""
        credit_list = raw.get("artist-credit", [])
        if credit_list:
            first_credit = credit_list[0]
            if isinstance(first_credit, dict):
                artist = (
                    first_credit.get("artist", {}).get("name", "")
                    or first_credit.get("name", "")
                )

        # Año
        year = None
        date_str = raw.get("date", "")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        # Pistas
        tracks = self._extract_tracks(raw, artist)

        # Género (MusicBrainz no tiene géneros directos; se extrae del release-group)
        genre = ""
        rg = raw.get("release-group", {})
        tags = rg.get("tag-list", []) or raw.get("tag-list", [])
        if tags:
            genre = tags[0].get("name", "")

        return {
            "musicbrainz_id": release_id,
            "title":          raw.get("title", ""),
            "artist":         artist,
            "year":           year,
            "genre":          genre,
            "cover_url":      self.get_cover_url(release_id),
            "tracks":         tracks,
        }

    @staticmethod
    def _extract_tracks(raw: dict, album_artist: str) -> list[dict]:
        """Extrae las pistas de un release."""
        tracks: list[dict] = []
        medium_list = raw.get("medium-list", [])
        if not medium_list:
            return tracks

        for medium in medium_list:
            disc_num = medium.get("position", 1)
            for t in medium.get("track-list", []):
                recording = t.get("recording", {})
                # Artista de la pista (puede ser diferente al del álbum)
                track_artist = album_artist
                track_credits = recording.get("artist-credit", [])
                if track_credits and isinstance(track_credits[0], dict):
                    track_artist = (
                        track_credits[0].get("artist", {}).get("name", "")
                        or album_artist
                    )

                tracks.append({
                    "number":           int(t.get("position", 0)),
                    "disc_number":      disc_num,
                    "title":            recording.get("title", t.get("title", "")),
                    "artist":           track_artist,
                    "duration_ms":      int(recording.get("length", 0)),
                    "musicbrainz_id":   recording.get("id"),
                    "isrc":             None,
                })
        return tracks

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Espera lo necesario para no superar 1 req/seg."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()
