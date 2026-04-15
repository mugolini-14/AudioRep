"""
CDReader — Implementación de ICDReader usando la librería discid.
"""
from __future__ import annotations

import logging
import sys

import discid

from audiorep.domain.cd_disc import CDDisc, CDTrack, RipStatus

logger = logging.getLogger(__name__)


def _compute_freedb_id(tracks: list[CDTrack]) -> str:
    """
    Calcula el disc ID CDDB/FreeDB/GnuDB a partir de offsets y duraciones.

    Fórmula estándar CDDB:
        n = sum( sum_digits(offset_in_seconds) ) % 255  para cada pista
        t = total_seconds_del_disco
        disc_id = (n << 24) | (t << 8) | num_tracks
    """
    if not tracks:
        return "00000000"

    def _sum_digits(n: int) -> int:
        return sum(int(d) for d in str(max(n, 0)))

    offsets_sec = [t.offset // 75 for t in tracks]
    last = tracks[-1]
    total_sec = (last.offset + last.duration_ms * 75 // 1000) // 75

    n = sum(_sum_digits(s) for s in offsets_sec) % 255
    disc_id = (n << 24) | (total_sec << 8) | len(tracks)
    return f"{disc_id:08x}"


class CDReader:
    """Lee el Disc ID y las pistas de un CD físico. Implementa ICDReader."""

    def read_disc(self, drive: str = "") -> CDDisc:
        """Lee el CD en la unidad dada y retorna un CDDisc."""
        try:
            actual_drive = drive or discid.get_default_device() or ""
            disc = discid.read(actual_drive or None)
            tracks = [
                CDTrack(
                    number=t.number,
                    duration_ms=int(t.seconds * 1000),
                    offset=t.offset,
                    rip_status=RipStatus.PENDING,
                )
                for t in disc.tracks
            ]
            freedb_id = _compute_freedb_id(tracks)
            return CDDisc(
                disc_id=disc.id,
                drive_path=actual_drive,
                tracks=tracks,
                freedb_id=freedb_id,
            )
        except Exception as exc:
            logger.error("CDReader.read_disc: %s", exc)
            raise

    def list_drives(self) -> list[str]:
        """Retorna lista de unidades de CD disponibles en el sistema."""
        drives: list[str] = []

        if sys.platform == "win32":
            drives = self._list_drives_windows()
        else:
            drives = self._list_drives_linux()

        # Fallback: usar la unidad por defecto de discid
        if not drives:
            try:
                default = discid.get_default_device()
                if default:
                    drives.append(default)
            except Exception:
                pass

        return drives or [""]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _list_drives_windows() -> list[str]:
        """Enumera unidades de CD en Windows vía GetLogicalDrives."""
        drives: list[str] = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
            for i in range(26):
                if bitmask & (1 << i):
                    letter = chr(65 + i) + ":"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(letter + "\\")  # type: ignore[attr-defined]
                    if drive_type == 5:  # DRIVE_CDROM = 5
                        drives.append(letter)
        except Exception as exc:
            logger.warning("CDReader._list_drives_windows: %s", exc)
        return drives

    @staticmethod
    def _list_drives_linux() -> list[str]:
        """Enumera unidades de CD en Linux buscando paths comunes."""
        import os
        candidates = ["/dev/cdrom", "/dev/sr0", "/dev/sr1", "/dev/dvd", "/dev/dvdrw"]
        return [p for p in candidates if os.path.exists(p)]
