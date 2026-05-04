"""EqPresetRepository — Persistencia de presets de usuario del ecualizador."""
from __future__ import annotations

import logging

from audiorep.domain.eq_preset import EqPreset
from audiorep.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class EqPresetRepository:
    """Implementa IEqPresetRepository sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def get_all(self) -> list[EqPreset]:
        rows = self._db.fetchall(
            "SELECT name, preamp, band_0, band_1, band_2, band_3, band_4, "
            "band_5, band_6, band_7, band_8, band_9 FROM eq_presets ORDER BY name"
        )
        return [
            EqPreset(
                name=row["name"],
                preamp=row["preamp"],
                bands=[
                    row["band_0"], row["band_1"], row["band_2"], row["band_3"],
                    row["band_4"], row["band_5"], row["band_6"], row["band_7"],
                    row["band_8"], row["band_9"],
                ],
                is_builtin=False,
            )
            for row in rows
        ]

    def save(self, preset: EqPreset) -> None:
        self._db.execute(
            """INSERT INTO eq_presets
               (name, preamp, band_0, band_1, band_2, band_3, band_4,
                band_5, band_6, band_7, band_8, band_9)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 preamp=excluded.preamp, band_0=excluded.band_0,
                 band_1=excluded.band_1, band_2=excluded.band_2,
                 band_3=excluded.band_3, band_4=excluded.band_4,
                 band_5=excluded.band_5, band_6=excluded.band_6,
                 band_7=excluded.band_7, band_8=excluded.band_8,
                 band_9=excluded.band_9""",
            (
                preset.name, preset.preamp,
                preset.bands[0], preset.bands[1], preset.bands[2],
                preset.bands[3], preset.bands[4], preset.bands[5],
                preset.bands[6], preset.bands[7], preset.bands[8],
                preset.bands[9],
            ),
        )
        self._db.commit()
        logger.debug("EqPresetRepository: preset guardado '%s'", preset.name)

    def delete(self, name: str) -> None:
        self._db.execute("DELETE FROM eq_presets WHERE name = ?", (name,))
        self._db.commit()
        logger.debug("EqPresetRepository: preset eliminado '%s'", name)
