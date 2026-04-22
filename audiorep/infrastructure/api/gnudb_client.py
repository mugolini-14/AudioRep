"""
GnuDBClient — Búsqueda de metadatos de CD vía protocolo CDDB sobre HTTP.

GnuDB (gnudb.gnudb.org) es el sucesor libre y gratuito de FreeDB/CDDB.
No requiere API key ni registro.

Formato de resultado normalizado (igual que MusicBrainzClient.search_disc):
    {
        "album":      str,
        "artist":     str,
        "year":       str,
        "genre":      str,
        "release_id": str,   # "<category>/<discid>" p.ej. "rock/deadbeef"
        "tracks": [
            {"number": int, "title": str, "recording_id": str, "duration_ms": int}
        ]
    }

Protocolo CDDB resumido:
    1. GET /~cddb/cddb.cgi?cmd=cddb+query+<id>+<ntrks>+<off1>...+<total_sec>
           &hello=user+host+app+ver&proto=6
       → líneas con: código categoría discid título
    2. GET /~cddb/cddb.cgi?cmd=cddb+read+<category>+<discid>
           &hello=user+host+app+ver&proto=6
       → archivo XMCD con DTITLE, DYEAR, DGENRE, TTITLEn
"""
from __future__ import annotations

import logging
import re

import requests

from audiorep.domain.cd_disc import CDDisc

logger = logging.getLogger(__name__)

_BASE_URL  = "http://gnudb.gnudb.org/~cddb/cddb.cgi"
_HELLO     = "user+localhost+AudioRep+0.30"
_PROTO     = "6"
_TIMEOUT   = 8  # segundos


class GnuDBClient:
    """
    Cliente para GnuDB (CDDB sobre HTTP).

    Implementa ICDLookupProvider.
    No requiere API key.
    """

    name = "GnuDB"

    # ------------------------------------------------------------------
    # ICDLookupProvider
    # ------------------------------------------------------------------

    def search_disc(self, disc: CDDisc) -> list[dict]:
        """
        Busca el disco en GnuDB usando el Disc ID CDDB (freedb_id).
        Retorna lista de resultados en formato normalizado.
        """
        if not disc.tracks:
            return []

        cddb_id, ntrks, offsets_str, total_sec = self._disc_params(disc)
        logger.debug("GnuDB query: id=%s ntrks=%d total=%ds", cddb_id, ntrks, total_sec)

        # ── Paso 1: query ─────────────────────────────────────────── #
        query_cmd = (
            f"cddb query {cddb_id} {ntrks} {offsets_str} {total_sec}"
        )
        try:
            resp = requests.get(
                _BASE_URL,
                params={"cmd": query_cmd, "hello": _HELLO, "proto": _PROTO},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("GnuDB query error: %s", exc)
            return []

        matches = self._parse_query_response(resp.text)
        if not matches:
            logger.info("GnuDB: sin resultados para disc_id=%s", cddb_id)
            return []

        # ── Paso 2: leer cada resultado ──────────────────────────── #
        results: list[dict] = []
        for category, entry_id in matches[:5]:  # máximo 5
            entry = self._read_entry(category, entry_id, disc)
            if entry:
                results.append(entry)

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _disc_params(disc: CDDisc) -> tuple[str, int, str, int]:
        """
        Calcula los parámetros CDDB para la query:
            cddb_id, ntrks, offsets (frames separados por espacios), total_sec
        """
        tracks = disc.tracks
        ntrks  = len(tracks)

        # Offsets en frames (sectores a 75 fps)
        offsets_str = " ".join(str(t.offset) for t in tracks)

        # Duración total en segundos
        last = tracks[-1]
        total_frames = last.offset + (last.duration_ms * 75 // 1000)
        total_sec = total_frames // 75

        # Disc ID CDDB: usar el precomputado si está disponible,
        # de lo contrario calcularlo aquí
        if disc.freedb_id:
            cddb_id = disc.freedb_id
        else:
            def _sd(n: int) -> int:
                return sum(int(d) for d in str(max(n, 0)))
            n = sum(_sd(t.offset // 75) for t in tracks) % 255
            raw = (n << 24) | (total_sec << 8) | ntrks
            cddb_id = f"{raw:08x}"

        return cddb_id, ntrks, offsets_str, total_sec

    @staticmethod
    def _parse_query_response(text: str) -> list[tuple[str, str]]:
        """
        Parsea la respuesta de 'cddb query'.
        Código 200 = exacto, 211 = múltiples inexactos, 210 = múltiples exactos.
        Retorna lista de (category, discid).
        """
        lines = text.strip().splitlines()
        if not lines:
            return []

        first = lines[0]
        code = first[:3]

        if code == "200":
            # "200 category discid Título"
            parts = first.split(None, 3)
            if len(parts) >= 3:
                return [(parts[1], parts[2])]
            return []

        if code in ("210", "211"):
            matches: list[tuple[str, str]] = []
            for line in lines[1:]:
                line = line.strip()
                if line == ".":
                    break
                parts = line.split(None, 2)
                if len(parts) >= 2:
                    matches.append((parts[0], parts[1]))
            return matches

        return []

    def _read_entry(self, category: str, entry_id: str, disc: CDDisc) -> dict | None:
        """Descarga y parsea un entry XMCD de GnuDB."""
        read_cmd = f"cddb read {category} {entry_id}"
        try:
            resp = requests.get(
                _BASE_URL,
                params={"cmd": read_cmd, "hello": _HELLO, "proto": _PROTO},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("GnuDB read error (%s/%s): %s", category, entry_id, exc)
            return None

        return self._parse_xmcd(resp.text, category, entry_id, disc)

    @staticmethod
    def _parse_xmcd(text: str, category: str, entry_id: str, disc: CDDisc) -> dict | None:
        """
        Parsea el formato XMCD/CDDB:
            DTITLE=Artist / Album
            DYEAR=1994
            DGENRE=Rock
            TTITLE0=Track 1
            TTITLE1=Track 2
            ...
        """
        lines = text.splitlines()
        if not lines or not lines[0].startswith("210"):
            return None

        data: dict[str, str] = {}
        ttitles: dict[int, str] = {}

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("#") or not line or line == ".":
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()

            if key == "DTITLE":
                data["DTITLE"] = val
            elif key == "DYEAR":
                data["DYEAR"] = val
            elif key == "DGENRE":
                data["DGENRE"] = val
            elif re.match(r"TTITLE\d+", key):
                idx = int(key[6:])
                # Las entradas largas se concatenan en líneas múltiples
                ttitles[idx] = ttitles.get(idx, "") + val

        # Parsear DTITLE: "Artista / Álbum" o solo "Álbum"
        dtitle = data.get("DTITLE", "")
        if " / " in dtitle:
            artist, album = dtitle.split(" / ", 1)
        else:
            artist, album = "", dtitle

        year  = data.get("DYEAR", "")
        genre = data.get("DGENRE", "")

        # Construir lista de pistas normalizadas
        tracks: list[dict] = []
        for i, cd_track in enumerate(disc.tracks):
            title = ttitles.get(i, f"Pista {cd_track.number}")
            tracks.append({
                "number":       cd_track.number,
                "title":        title,
                "recording_id": "",          # GnuDB no tiene IDs individuales
                "duration_ms":  cd_track.duration_ms,
            })

        return {
            "album":      album.strip(),
            "artist":     artist.strip(),
            "year":       year,
            "genre":      genre,
            "label":      "",          # CDDB no expone sello discográfico
            "release_id": f"{category}/{entry_id}",
            "tracks":     tracks,
        }
