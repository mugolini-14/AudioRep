"""FileTagger — Implementa IFileTagger usando mutagen."""
from __future__ import annotations

import logging
from pathlib import Path

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TYER, TCON, APIC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis

logger = logging.getLogger(__name__)

_TAG_MAP = {
    "title":        ("TIT2", "title",        "TITLE"),
    "artist":       ("TPE1", "artist",        "ARTIST"),
    "album":        ("TALB", "album",         "ALBUM"),
    "track_number": ("TRCK", "tracknumber",   "TRACKNUMBER"),
    "year":         ("TYER", "date",          "DATE"),
    "genre":        ("TCON", "genre",         "GENRE"),
}


class FileTagger:
    """Lee y escribe tags de audio usando mutagen. Implementa IFileTagger."""

    def read_tags(self, file_path: str) -> dict:
        try:
            audio = mutagen.File(file_path, easy=True)
            if audio is None:
                return {}
            tags: dict = {}
            for key in ("title", "artist", "album", "tracknumber", "date", "genre"):
                val = audio.get(key)
                if val:
                    tags[key] = val[0] if isinstance(val, list) else str(val)
            # Duración
            if hasattr(audio, "info") and hasattr(audio.info, "length"):
                tags["duration_ms"] = int(audio.info.length * 1000)
            if hasattr(audio, "info") and hasattr(audio.info, "bitrate"):
                tags["bitrate_kbps"] = audio.info.bitrate // 1000
            return tags
        except Exception as exc:
            logger.warning("FileTagger.read_tags '%s': %s", file_path, exc)
            return {}

    def write_tags(self, file_path: str, tags: dict) -> None:
        try:
            audio = mutagen.File(file_path, easy=True)
            if audio is None:
                return
            for key, value in tags.items():
                if value is not None:
                    audio[key] = [str(value)]
            audio.save()
        except Exception as exc:
            logger.warning("FileTagger.write_tags '%s': %s", file_path, exc)

    def read_embedded_cover(self, file_path: str) -> bytes | None:
        try:
            suffix = Path(file_path).suffix.lower()
            if suffix == ".flac":
                audio = FLAC(file_path)
                if audio.pictures:
                    return audio.pictures[0].data
            elif suffix == ".mp3":
                audio = ID3(file_path)
                for tag in audio.values():
                    if isinstance(tag, APIC):
                        return tag.data
            else:
                audio = mutagen.File(file_path)
                if audio and hasattr(audio, "tags") and audio.tags:
                    cover = audio.tags.get("metadata_block_picture") or audio.tags.get("covr")
                    if cover:
                        data = cover[0]
                        if isinstance(data, bytes):
                            return data
                        if hasattr(data, "data"):
                            return data.data
        except Exception as exc:
            logger.debug("FileTagger.read_embedded_cover '%s': %s", file_path, exc)
        return None

    def write_embedded_cover(self, file_path: str, image_data: bytes) -> None:
        try:
            suffix = Path(file_path).suffix.lower()
            if suffix == ".flac":
                audio = FLAC(file_path)
                pic = Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.data = image_data
                audio.clear_pictures()
                audio.add_picture(pic)
                audio.save()
            elif suffix == ".mp3":
                audio = ID3(file_path)
                audio["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_data)
                audio.save()
        except Exception as exc:
            logger.warning("FileTagger.write_embedded_cover '%s': %s", file_path, exc)
