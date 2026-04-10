"""
FileTagger — Lector y escritor de tags de audio usando mutagen.

Implementa IFileTagger.

Formatos soportados y sus claves de tag:
    MP3  (ID3)   : TIT2, TPE1, TALB, TRCK, TPOS, TDRC/TYER, TCON
    FLAC (VorbisComment) : title, artist, album, tracknumber, discnumber, date, genre
    OGG  (VorbisComment) : ídem FLAC
    MP4/AAC (MP4Tags)    : ©nam, ©ART, ©alb, trkn, disk, ©day, ©gen
    WAV  (ID3)   : ídem MP3

El método `read_tags` normaliza todo a un dict con claves estándar.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import mutagen
import mutagen.flac
import mutagen.id3
import mutagen.mp3
import mutagen.mp4
import mutagen.oggvorbis
import mutagen.wave

from audiorep.core.exceptions import TaggerError

logger = logging.getLogger(__name__)

# Claves normalizadas que devuelve read_tags()
_EMPTY_TAGS: dict = {
    "title":          "",
    "artist":         "",
    "album":          "",
    "track_number":   0,
    "disc_number":    1,
    "year":           None,
    "genre":          "",
    "comment":        "",
    "duration_ms":    0,
    "bitrate_kbps":   0,
    "sample_rate_hz": 0,
    "channels":       2,
    "file_size_bytes": 0,
    "format":         "unknown",
}


class FileTagger:
    """
    Lee y escribe tags en archivos de audio.
    Implementa IFileTagger.
    """

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def read_tags(self, file_path: str) -> dict:
        """
        Lee los tags de un archivo de audio y devuelve un dict normalizado.

        Returns:
            Dict con claves: title, artist, album, track_number, disc_number,
            year, genre, comment, duration_ms, bitrate_kbps, sample_rate_hz,
            channels, file_size_bytes, format.

        Raises:
            TaggerError: si el archivo no puede ser leído.
        """
        tags = dict(_EMPTY_TAGS)

        try:
            audio = mutagen.File(file_path, easy=False)
        except Exception as exc:
            raise TaggerError(f"No se pudo leer el archivo: {file_path}") from exc

        if audio is None:
            raise TaggerError(f"Formato de audio no reconocido: {file_path}")

        # Info técnica (disponible en todos los formatos)
        info = audio.info
        tags["duration_ms"]    = int(getattr(info, "length", 0) * 1000)
        tags["bitrate_kbps"]   = int(getattr(info, "bitrate", 0) / 1000) \
                                  if hasattr(info, "bitrate") else 0
        tags["sample_rate_hz"] = getattr(info, "sample_rate", 0)
        tags["channels"]       = getattr(info, "channels", 2)
        tags["file_size_bytes"] = os.path.getsize(file_path)

        ext = Path(file_path).suffix.lower()

        if isinstance(audio, mutagen.mp3.MP3):
            tags["format"] = "mp3"
            self._read_id3(audio, tags)

        elif isinstance(audio, mutagen.flac.FLAC):
            tags["format"] = "flac"
            self._read_vorbis(audio, tags)

        elif isinstance(audio, mutagen.oggvorbis.OggVorbis):
            tags["format"] = "ogg"
            self._read_vorbis(audio, tags)

        elif isinstance(audio, mutagen.mp4.MP4):
            tags["format"] = "aac" if ext in (".aac", ".m4a") else "aac"
            self._read_mp4(audio, tags)

        elif isinstance(audio, mutagen.wave.WAVE):
            tags["format"] = "wav"
            if audio.tags:
                self._read_id3(audio, tags)

        else:
            tags["format"] = ext.lstrip(".") or "unknown"
            # Intento genérico con EasyID3-like interface
            try:
                self._read_generic(audio, tags)
            except Exception:
                pass

        # Fallback: usar el nombre del archivo como título si está vacío
        if not tags["title"]:
            tags["title"] = Path(file_path).stem

        return tags

    def _read_id3(self, audio: mutagen.FileType, tags: dict) -> None:
        """Lee tags ID3 (MP3, WAV)."""
        raw = audio.tags
        if raw is None:
            return

        def _text(key: str) -> str:
            frame = raw.get(key)
            if frame and hasattr(frame, "text") and frame.text:
                return str(frame.text[0]).strip()
            return ""

        tags["title"]  = _text("TIT2")
        tags["artist"] = _text("TPE1") or _text("TPE2")
        tags["album"]  = _text("TALB")
        tags["genre"]  = _text("TCON")
        tags["comment"] = _text("COMM::\x00\x00\x00") or _text("COMM")

        # Año: TDRC (v2.4) o TYER (v2.3)
        year_str = _text("TDRC") or _text("TYER")
        tags["year"] = self._parse_year(year_str)

        # Número de pista (puede ser "5/12")
        trck = _text("TRCK")
        tags["track_number"] = self._parse_slash_int(trck)

        # Número de disco
        tpos = _text("TPOS")
        tags["disc_number"] = self._parse_slash_int(tpos) or 1

    def _read_vorbis(self, audio: mutagen.FileType, tags: dict) -> None:
        """Lee comentarios Vorbis (FLAC, OGG)."""
        raw = audio.tags
        if raw is None:
            return

        def _first(key: str) -> str:
            vals = raw.get(key.upper()) or raw.get(key.lower()) or []
            return str(vals[0]).strip() if vals else ""

        tags["title"]  = _first("title")
        tags["artist"] = _first("artist")
        tags["album"]  = _first("album")
        tags["genre"]  = _first("genre")
        tags["comment"] = _first("comment")
        tags["year"]   = self._parse_year(_first("date") or _first("year"))
        tags["track_number"] = self._parse_slash_int(_first("tracknumber"))
        tags["disc_number"]  = self._parse_slash_int(_first("discnumber")) or 1

    def _read_mp4(self, audio: mutagen.mp4.MP4, tags: dict) -> None:
        """Lee tags MP4/M4A."""
        raw = audio.tags
        if raw is None:
            return

        def _first(key: str) -> str:
            vals = raw.get(key, [])
            return str(vals[0]).strip() if vals else ""

        tags["title"]  = _first("©nam")
        tags["artist"] = _first("©ART")
        tags["album"]  = _first("©alb")
        tags["genre"]  = _first("©gen")
        tags["comment"] = _first("©cmt")
        tags["year"]   = self._parse_year(_first("©day"))

        # trkn es una lista de tuplas (track, total)
        trkn = raw.get("trkn")
        if trkn and isinstance(trkn[0], (list, tuple)):
            tags["track_number"] = int(trkn[0][0]) if trkn[0][0] else 0
        disk = raw.get("disk")
        if disk and isinstance(disk[0], (list, tuple)):
            tags["disc_number"] = int(disk[0][0]) if disk[0][0] else 1

    def _read_generic(self, audio: mutagen.FileType, tags: dict) -> None:
        """Intento genérico para formatos desconocidos con tags tipo dict."""
        raw = audio.tags
        if raw is None:
            return
        for key in ("title", "artist", "album", "genre"):
            val = raw.get(key, raw.get(key.upper(), []))
            if isinstance(val, list) and val:
                tags[key] = str(val[0]).strip()

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def write_tags(self, file_path: str, tags: dict) -> None:
        """
        Escribe los tags en el archivo de audio.

        Args:
            file_path: Ruta al archivo.
            tags:      Dict con las claves de read_tags() a actualizar.

        Raises:
            TaggerError: si no se puede escribir.
        """
        try:
            audio = mutagen.File(file_path, easy=False)
        except Exception as exc:
            raise TaggerError(f"No se pudo abrir para escritura: {file_path}") from exc

        if audio is None:
            raise TaggerError(f"Formato no reconocido: {file_path}")

        try:
            if isinstance(audio, mutagen.mp3.MP3):
                self._write_id3(audio, tags)
            elif isinstance(audio, (mutagen.flac.FLAC, mutagen.oggvorbis.OggVorbis)):
                self._write_vorbis(audio, tags)
            elif isinstance(audio, mutagen.mp4.MP4):
                self._write_mp4(audio, tags)
            audio.save()
        except Exception as exc:
            raise TaggerError(f"Error al guardar tags en: {file_path}") from exc

    def _write_id3(self, audio: mutagen.mp3.MP3, tags: dict) -> None:
        if audio.tags is None:
            audio.add_tags()
        raw = audio.tags
        if tags.get("title"):
            raw["TIT2"] = mutagen.id3.TIT2(text=[tags["title"]])
        if tags.get("artist"):
            raw["TPE1"] = mutagen.id3.TPE1(text=[tags["artist"]])
        if tags.get("album"):
            raw["TALB"] = mutagen.id3.TALB(text=[tags["album"]])
        if tags.get("genre"):
            raw["TCON"] = mutagen.id3.TCON(text=[tags["genre"]])
        if tags.get("year"):
            raw["TDRC"] = mutagen.id3.TDRC(text=[str(tags["year"])])
        if tags.get("track_number"):
            raw["TRCK"] = mutagen.id3.TRCK(text=[str(tags["track_number"])])
        if tags.get("disc_number"):
            raw["TPOS"] = mutagen.id3.TPOS(text=[str(tags["disc_number"])])

    def _write_vorbis(self, audio: mutagen.FileType, tags: dict) -> None:
        mapping = {
            "title":        "TITLE",
            "artist":       "ARTIST",
            "album":        "ALBUM",
            "genre":        "GENRE",
            "comment":      "COMMENT",
            "track_number": "TRACKNUMBER",
            "disc_number":  "DISCNUMBER",
        }
        for key, vkey in mapping.items():
            val = tags.get(key)
            if val:
                audio[vkey] = [str(val)]
        if tags.get("year"):
            audio["DATE"] = [str(tags["year"])]

    def _write_mp4(self, audio: mutagen.mp4.MP4, tags: dict) -> None:
        if audio.tags is None:
            audio.add_tags()
        raw = audio.tags
        if tags.get("title"):
            raw["©nam"] = [tags["title"]]
        if tags.get("artist"):
            raw["©ART"] = [tags["artist"]]
        if tags.get("album"):
            raw["©alb"] = [tags["album"]]
        if tags.get("genre"):
            raw["©gen"] = [tags["genre"]]
        if tags.get("year"):
            raw["©day"] = [str(tags["year"])]
        if tags.get("track_number"):
            raw["trkn"] = [(int(tags["track_number"]), 0)]
        if tags.get("disc_number"):
            raw["disk"] = [(int(tags["disc_number"]), 0)]

    # ------------------------------------------------------------------
    # Portada embebida
    # ------------------------------------------------------------------

    def read_embedded_cover(self, file_path: str) -> bytes | None:
        """Extrae la imagen de portada embebida en el archivo, o None."""
        try:
            audio = mutagen.File(file_path, easy=False)
        except Exception:
            return None
        if audio is None:
            return None

        # MP3 ID3: APIC frame
        if isinstance(audio, mutagen.mp3.MP3) and audio.tags:
            for key in audio.tags:
                if key.startswith("APIC"):
                    return audio.tags[key].data

        # FLAC: pictures list
        if isinstance(audio, mutagen.flac.FLAC) and audio.pictures:
            return audio.pictures[0].data

        # MP4: covr
        if isinstance(audio, mutagen.mp4.MP4) and audio.tags:
            covers = audio.tags.get("covr", [])
            if covers:
                return bytes(covers[0])

        return None

    def write_embedded_cover(self, file_path: str, image_data: bytes) -> None:
        """Embebe una imagen de portada en el archivo de audio."""
        try:
            audio = mutagen.File(file_path, easy=False)
        except Exception as exc:
            raise TaggerError(f"No se pudo abrir para escritura: {file_path}") from exc
        if audio is None:
            return

        if isinstance(audio, mutagen.mp3.MP3):
            if audio.tags is None:
                audio.add_tags()
            audio.tags["APIC"] = mutagen.id3.APIC(
                mime="image/jpeg",
                type=mutagen.id3.PictureType.COVER_FRONT,
                data=image_data,
            )

        elif isinstance(audio, mutagen.flac.FLAC):
            pic = mutagen.flac.Picture()
            pic.data = image_data
            pic.mime = "image/jpeg"
            pic.type = mutagen.id3.PictureType.COVER_FRONT
            audio.clear_pictures()
            audio.add_picture(pic)

        elif isinstance(audio, mutagen.mp4.MP4):
            if audio.tags is None:
                audio.add_tags()
            audio.tags["covr"] = [
                mutagen.mp4.MP4Cover(image_data, mutagen.mp4.MP4Cover.FORMAT_JPEG)
            ]

        try:
            audio.save()
        except Exception as exc:
            raise TaggerError(f"Error al guardar portada en: {file_path}") from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_year(value: str) -> int | None:
        """Extrae el año de strings como '2003', '2003-07-15', '2003-00-00'."""
        if not value:
            return None
        try:
            return int(str(value)[:4])
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_slash_int(value: str) -> int:
        """Convierte '5/12' o '5' a 5. Retorna 0 si falla."""
        if not value:
            return 0
        try:
            return int(str(value).split("/")[0].strip())
        except (ValueError, TypeError):
            return 0
