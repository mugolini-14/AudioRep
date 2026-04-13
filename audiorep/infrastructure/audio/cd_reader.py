"""
CDReader — Implementación de ICDReader usando la librería discid.
"""
from __future__ import annotations

import logging

import discid

from audiorep.domain.cd_disc import CDDisc, CDTrack, RipStatus

logger = logging.getLogger(__name__)


class CDReader:
    """Lee el Disc ID y las pistas de un CD físico. Implementa ICDReader."""

    def read_disc(self, drive: str = "") -> CDDisc:
        """Lee el CD en la unidad dada y retorna un CDDisc."""
        try:
            disc = discid.read(drive or None)
            tracks = [
                CDTrack(
                    number=t.number,
                    duration_ms=int(t.seconds * 1000),
                    offset=t.offset,
                    rip_status=RipStatus.PENDING,
                )
                for t in disc.tracks
            ]
            return CDDisc(
                disc_id=disc.id,
                drive_path=drive or "",
                tracks=tracks,
            )
        except Exception as exc:
            logger.error("CDReader.read_disc: %s", exc)
            raise

    def list_drives(self) -> list[str]:
        """Retorna lista de unidades de CD disponibles."""
        try:
            default = discid.get_default_device()
            return [default] if default else []
        except Exception:
            return []
