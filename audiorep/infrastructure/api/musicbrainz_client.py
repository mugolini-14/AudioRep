"""
MusicBrainzClient — Implementa IMetadataProvider e ICDLookupProvider
usando la librería musicbrainzngs.

Formato normalizado de resultados de disc lookup:
    {
        "album":      str,
        "artist":     str,
        "year":       str,          # "1994" o ""
        "genre":      str,          # MusicBrainz no tiene género, siempre ""
        "label":      str,          # sello discográfico o ""
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

# Códigos ISO-2 más frecuentes en MusicBrainz → nombre completo.
# Se usa como fallback cuando area.name no está disponible.
_ISO_FALLBACK: dict[str, str] = {
    "AD": "Andorra",         "AE": "United Arab Emirates", "AR": "Argentina",
    "AT": "Austria",         "AU": "Australia",             "BE": "Belgium",
    "BR": "Brazil",          "CA": "Canada",                "CH": "Switzerland",
    "CL": "Chile",           "CN": "China",                 "CO": "Colombia",
    "CU": "Cuba",            "CZ": "Czech Republic",        "DE": "Germany",
    "DK": "Denmark",         "EG": "Egypt",                 "ES": "Spain",
    "FI": "Finland",         "FR": "France",                "GB": "United Kingdom",
    "GR": "Greece",          "HR": "Croatia",               "HU": "Hungary",
    "ID": "Indonesia",       "IE": "Ireland",               "IL": "Israel",
    "IN": "India",           "IS": "Iceland",               "IT": "Italy",
    "JP": "Japan",           "KR": "South Korea",           "LT": "Lithuania",
    "LU": "Luxembourg",      "MX": "Mexico",                "MY": "Malaysia",
    "NG": "Nigeria",         "NL": "Netherlands",           "NO": "Norway",
    "NZ": "New Zealand",     "PE": "Peru",                  "PH": "Philippines",
    "PL": "Poland",          "PT": "Portugal",              "RO": "Romania",
    "RS": "Serbia",          "RU": "Russia",                "SE": "Sweden",
    "SG": "Singapore",       "SI": "Slovenia",              "SK": "Slovakia",
    "TH": "Thailand",        "TR": "Turkey",                "TW": "Taiwan",
    "UA": "Ukraine",         "US": "United States",         "UY": "Uruguay",
    "VE": "Venezuela",       "ZA": "South Africa",          "ZW": "Zimbabwe",
}


def _resolve_country(raw: str) -> str:
    """Convierte un código ISO-2 en nombre completo.

    Intenta primero con pycountry (si está instalado). Si no,
    consulta el fallback interno. Si no coincide, devuelve raw tal cual.
    """
    if not raw or len(raw) != 2:
        return raw
    code = raw.upper()
    try:
        import pycountry  # type: ignore[import]
        country = pycountry.countries.get(alpha_2=code)
        if country:
            return country.name
    except Exception:
        pass
    return _ISO_FALLBACK.get(code, raw)


def _normalize_release(release: dict) -> dict:
    """Convierte un release raw de MusicBrainzngs al formato normalizado."""
    # Título del álbum
    album = release.get("title", "")

    # Artista principal + país/área del artista
    credits = release.get("artist-credit", [])
    artist = ""
    artist_country = ""
    if credits:
        first = credits[0]
        if isinstance(first, dict):
            artist = first.get("name") or first.get("artist", {}).get("name", "")
            artist_obj = first.get("artist", {})
            artist_country = _resolve_country(
                artist_obj.get("area", {}).get("name", "")
                or artist_obj.get("country", "")
            )

    # Año (date puede ser "1994", "1994-05-10", etc.)
    date = release.get("date", "") or release.get("first-release-date", "")
    year = date[:4] if date else ""

    # Release ID (MBID)
    release_id = release.get("id", "")

    # Tipo de release (Album, Single, EP, Compilation, etc.)
    release_type = ""
    rg = release.get("release-group") or {}
    release_type = rg.get("primary-type", "")

    # Sello discográfico + país del sello
    label = ""
    label_country = ""
    for info in release.get("label-info-list", []):
        lbl = info.get("label") or {}
        name = lbl.get("name", "")
        if name:
            label = name
            label_country = _resolve_country(
                lbl.get("area", {}).get("name", "")
                or lbl.get("country", "")
            )
            break

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
        "album":          album,
        "artist":         artist,
        "artist_country": artist_country,
        "year":           year,
        "genre":          "",          # MusicBrainz no expone género por release
        "label":          label,
        "label_country":  label_country,
        "release_type":   release_type,
        "release_id":     release_id,
        "tracks":         tracks,
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
        # Caché MBID → país del sello para evitar llamadas redundantes a la API.
        self._label_country_cache: dict[str, str] = {}

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
                disc_id, includes=["artists", "recordings", "labels", "release-groups"]
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
    # Enriquecimiento de pistas de biblioteca
    # ------------------------------------------------------------------

    def enrich_track(
        self,
        artist: str,
        title: str,
        album: str = "",
        mbid: str | None = None,
    ) -> dict | None:
        """
        Busca metadatos completos de una pista en MusicBrainz.

        Si se provee `mbid`, hace lookup directo. En caso contrario
        realiza una búsqueda por texto y luego lookup del primer resultado.

        Retorna dict con: mbid, genre, year, artist_country,
                          label, label_country, release_type.
        Retorna None si no se encuentra información.
        """
        try:
            recording: dict = {}

            # "artists" es necesario para que artist-credit incluya area/country
            _REC_INCLUDES = ["tags", "artists", "artist-credits", "releases", "release-groups"]

            if mbid:
                result = musicbrainzngs.get_recording_by_id(mbid, includes=_REC_INCLUDES)
                recording = result.get("recording", {})
            else:
                if not artist and not title:
                    return None
                search_result = musicbrainzngs.search_recordings(
                    artist=artist,
                    recording=title,
                    release=album,
                    limit=3,
                )
                candidates = search_result.get("recording-list", [])
                if not candidates:
                    return None
                best_mbid = candidates[0].get("id", "")
                if not best_mbid:
                    return None
                full_result = musicbrainzngs.get_recording_by_id(
                    best_mbid, includes=_REC_INCLUDES
                )
                recording = full_result.get("recording", {})

            if not recording:
                return None

            found_mbid = recording.get("id", "")

            # Género: primer tag con el mayor count
            tags = recording.get("tag-list", [])
            genre = ""
            if tags:
                try:
                    sorted_tags = sorted(
                        tags, key=lambda t: int(t.get("count", 0)), reverse=True
                    )
                    genre = sorted_tags[0].get("name", "").strip().title() if sorted_tags else ""
                except Exception:
                    pass

            # País del artista
            artist_country = ""
            credits = recording.get("artist-credit", [])
            if credits and isinstance(credits[0], dict):
                artist_obj = credits[0].get("artist", {})
                artist_country = _resolve_country(
                    artist_obj.get("area", {}).get("name", "")
                    or artist_obj.get("country", "")
                )

            # Año, sello y tipo desde el primer release
            year = ""
            label = ""
            label_country = ""
            release_type = ""
            releases = recording.get("release-list", [])
            if releases:
                rel = releases[0]
                date_str = rel.get("date", "") or ""
                year = date_str[:4] if date_str else ""

                for info in rel.get("label-info-list", []):
                    lbl = info.get("label") or {}
                    if lbl.get("name"):
                        label = lbl["name"]
                        label_country = _resolve_country(
                            lbl.get("area", {}).get("name", "")
                            or lbl.get("country", "")
                        )
                        break

                rg = rel.get("release-group") or {}
                release_type = rg.get("primary-type", "")

            return {
                "mbid":           found_mbid,
                "genre":          genre,
                "year":           year,
                "artist_country": artist_country,
                "label":          label,
                "label_country":  label_country,
                "release_type":   release_type,
            }

        except musicbrainzngs.ResponseError as exc:
            logger.info("MusicBrainzClient.enrich_track: no encontrado (%s)", exc)
            return None
        except Exception as exc:
            logger.warning("MusicBrainzClient.enrich_track: %s", exc)
            return None

    # ------------------------------------------------------------------
    # ICDLookupProvider
    # ------------------------------------------------------------------
    # Enriquecimiento de álbumes de biblioteca
    # ------------------------------------------------------------------

    def enrich_album(self, artist: str, title: str) -> dict | None:
        """
        Busca metadatos completos de un álbum en MusicBrainz.

        Usa el endpoint de releases (no recordings) para obtener en una sola
        llamada: year, artist_country, label, label_country, release_type.

        Retorna dict con esas claves, o None si no se encontró nada.
        """
        try:
            if not artist and not title:
                return None

            result = musicbrainzngs.search_releases(
                artist=artist, release=title, limit=5
            )
            releases = result.get("release-list", [])
            if not releases:
                return None

            release_mbid = releases[0].get("id", "")
            if not release_mbid:
                return None

            full = musicbrainzngs.get_release_by_id(
                release_mbid,
                includes=["artists", "labels", "artist-credits", "release-groups"],
            )
            release = full.get("release", {})
            if not release:
                return None

            # País del artista
            artist_country = ""
            credits = release.get("artist-credit", [])
            if credits and isinstance(credits[0], dict):
                artist_obj = credits[0].get("artist", {})
                artist_country = _resolve_country(
                    artist_obj.get("area", {}).get("name", "")
                    or artist_obj.get("country", "")
                )

            # Año
            date = release.get("date", "") or ""
            year = date[:4] if date else ""

            # Sello — el endpoint de releases no devuelve area/country del sello;
            # se requiere un lookup separado por MBID del sello.
            label = ""
            label_country = ""
            label_mbid = ""
            for info in release.get("label-info-list", []):
                lbl = info.get("label") or {}
                if lbl.get("name"):
                    label = lbl["name"]
                    label_mbid = lbl.get("id", "")
                    label_country = _resolve_country(
                        lbl.get("area", {}).get("name", "")
                        or lbl.get("country", "")
                    )
                    break

            if not label_country and label_mbid:
                label_country = self._fetch_label_country(label_mbid)

            # Tipo de lanzamiento
            rg = release.get("release-group") or {}
            release_type = rg.get("primary-type", "")

            logger.debug(
                "enrich_album '%s - %s': country=%s label=%s type=%s",
                artist, title, artist_country, label, release_type,
            )
            return {
                "year":           year,
                "artist_country": artist_country,
                "label":          label,
                "label_country":  label_country,
                "release_type":   release_type,
            }

        except Exception as exc:
            logger.warning("MusicBrainzClient.enrich_album '%s - %s': %s", artist, title, exc)
            return None

    def _fetch_label_country(self, label_mbid: str) -> str:
        """Lookup directo por MBID del sello para obtener su país de origen.

        get_release_by_id con includes=['labels'] no devuelve area/country del
        sello; se necesita una llamada separada a get_label_by_id.
        Resultados cacheados por MBID para evitar llamadas redundantes.
        """
        if label_mbid in self._label_country_cache:
            return self._label_country_cache[label_mbid]
        try:
            import time
            time.sleep(1.1)  # respetar rate limit de MusicBrainz
            result = musicbrainzngs.get_label_by_id(label_mbid, includes=[])
            lbl = result.get("label", {})
            raw = (
                lbl.get("area", {}).get("name", "")
                or lbl.get("country", "")
            )
            country = _resolve_country(raw)
            self._label_country_cache[label_mbid] = country
            logger.debug("_fetch_label_country %s → '%s'", label_mbid, country)
            return country
        except Exception as exc:
            logger.debug("_fetch_label_country %s: %s", label_mbid, exc)
            self._label_country_cache[label_mbid] = ""
            return ""

    # ------------------------------------------------------------------

    def search_disc(self, disc: CDDisc) -> list[dict]:
        """
        Busca el disco usando su MusicBrainz Disc ID.
        Retorna lista en formato normalizado.
        """
        return self.search_by_disc_id(disc.disc_id)
