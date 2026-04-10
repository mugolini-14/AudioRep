"""
CDReader — Lector de información básica del CD físico.

Implementa ICDReader usando la librería `discid`.

discid lee el TOC (Table of Contents) del CD para:
    - Calcular el Disc ID (compatible con MusicBrainz y FreeDB).
    - Enumerar las pistas con número, offset y duración.

No realiza ninguna petición de red; solo hardware local.

Conversión de sectores a tiempo:
    1 sector CD = 1/75 segundo
    duration_ms = (sectors / 75) * 1000
"""
from __future__ import annotations

import logging
import platform

import discid  # type: ignore[import-untyped]

from audiorep.core.exceptions import CDReadError, NoCDInsertedError
from audiorep.domain.cd_disc import CDDisc, CDTrack

logger = logging.getLogger(__name__)

_SECTORS_PER_SECOND = 75


class CDReader:
    """
    Lee el TOC del CD usando discid y construye un CDDisc.

    Implementa ICDReader.
    """

    def read_disc(self, drive: str = "") -> CDDisc:
        """
        Lee el CD en la unidad indicada.

        Args:
            drive: Ruta de la unidad lectora.
                   Si está vacía se usa la unidad por defecto del sistema.
                   Windows: "D:", "E:", etc.
                   Linux:   "/dev/cdrom", "/dev/sr0", etc.

        Returns:
            CDDisc con pistas, offsets y duración calculados.

        Raises:
            NoCDInsertedError: si no hay ningún CD en la unidad.
            CDReadError:       si ocurre un error de hardware o permisos.
        """
        device = drive or discid.get_default_device()
        logger.debug("Leyendo CD en unidad: %s", device)

        try:
            disc = discid.read(device)
        except discid.DiscError as exc:
            msg = str(exc).lower()
            if "no medium" in msg or "not ready" in msg or "no disc" in msg:
                raise NoCDInsertedError() from exc
            raise CDReadError(f"Error al leer el CD en '{device}': {exc}") from exc
        except Exception as exc:
            raise CDReadError(f"Error inesperado leyendo CD: {exc}") from exc

        tracks = self._build_tracks(disc)

        cd_disc = CDDisc(
            disc_id=disc.id,
            drive_path=device,
            tracks=tracks,
        )

        logger.info(
            "CD leído: disc_id=%s, pistas=%d, duración=%s",
            disc.id, len(tracks), cd_disc.total_duration_display,
        )
        return cd_disc

    def list_drives(self) -> list[str]:
        """
        Retorna las unidades de CD disponibles en el sistema.

        En Windows intenta las letras D: a L:.
        En Linux busca /dev/sr* y /dev/cdrom*.
        """
        drives: list[str] = []
        system = platform.system()

        if system == "Windows":
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                if bitmask & (1 << i):
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(f"{letter}:\\")
                    # 5 = DRIVE_CDROM
                    if drive_type == 5:
                        drives.append(f"{letter}:")
        else:
            import glob
            for pattern in ("/dev/sr*", "/dev/cdrom*", "/dev/dvd*"):
                drives.extend(sorted(glob.glob(pattern)))

        if not drives:
            default = discid.get_default_device()
            drives = [default] if default else []

        logger.debug("Unidades CD encontradas: %s", drives)
        return drives

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_tracks(disc) -> list[CDTrack]:
        """Convierte los tracks de discid a entidades CDTrack."""
        tracks: list[CDTrack] = []

        for t in disc.tracks:
            # discid.Track.length = duración en sectores
            # discid.Track.offset = posición en sectores desde el inicio
            length_sectors = getattr(t, "length", 0)
            offset_sectors = getattr(t, "offset", 0)
            duration_ms    = int(length_sectors / _SECTORS_PER_SECOND * 1000)

            tracks.append(CDTrack(
                number=t.number,
                duration_ms=duration_ms,
                offset=offset_sectors,
                isrc=getattr(t, "isrc", None) or None,
            ))

        return tracks
