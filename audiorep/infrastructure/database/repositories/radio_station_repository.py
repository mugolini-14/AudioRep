"""
AudioRep — Repositorio de emisoras de radio.

Implementa `IRadioStationRepository` usando SQLite.
Persiste y recupera entidades `RadioStation` de la tabla `radio_stations`.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime

from audiorep.domain.radio_station import RadioStation
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RadioStationRepository(BaseRepository):
    """
    Acceso a datos de emisoras de radio.

    La tabla `radio_stations` se crea en la migración v2 de DatabaseConnection.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # IRadioStationRepository
    # ------------------------------------------------------------------

    def get_by_id(self, station_id: int) -> RadioStation | None:
        """Retorna la emisora con el id dado, o None si no existe."""
        row = self._fetchone(
            "SELECT * FROM radio_stations WHERE id = ?",
            (station_id,),
        )
        return self._row_to_station(row) if row else None

    def get_all(self) -> list[RadioStation]:
        """Retorna todas las emisoras guardadas, ordenadas por nombre."""
        rows = self._fetchall(
            "SELECT * FROM radio_stations ORDER BY name ASC"
        )
        return [self._row_to_station(r) for r in rows]

    def get_favorites(self) -> list[RadioStation]:
        """Retorna solo las emisoras marcadas como favoritas."""
        rows = self._fetchall(
            "SELECT * FROM radio_stations WHERE is_favorite = 1 ORDER BY name ASC"
        )
        return [self._row_to_station(r) for r in rows]

    def save(self, station: RadioStation) -> RadioStation:
        """
        Persiste la emisora.

        - Si `station.id` es None: INSERT → retorna la emisora con el nuevo id.
        - Si `station.id` tiene valor: UPDATE → retorna la misma emisora.
        """
        if station.id is None:
            return self._insert(station)
        return self._update(station)

    def delete(self, station_id: int) -> None:
        """Elimina la emisora con el id dado."""
        self._execute("DELETE FROM radio_stations WHERE id = ?", (station_id,))
        self._commit()
        logger.debug("RadioStationRepository: eliminada estación id=%d", station_id)

    def set_favorite(self, station_id: int, is_favorite: bool) -> None:
        """Marca o desmarca como favorita la emisora con el id dado."""
        self._execute(
            "UPDATE radio_stations SET is_favorite = ? WHERE id = ?",
            (1 if is_favorite else 0, station_id),
        )
        self._commit()
        logger.debug(
            "RadioStationRepository: station %d → is_favorite=%s",
            station_id,
            is_favorite,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _insert(self, station: RadioStation) -> RadioStation:
        cursor = self._execute(
            """
            INSERT INTO radio_stations
                (name, stream_url, country, genre, logo_url,
                 is_favorite, added_at, bitrate_kbps, radio_browser_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                station.name,
                station.stream_url,
                station.country,
                station.genre,
                station.logo_url,
                1 if station.is_favorite else 0,
                station.added_at.isoformat(),
                station.bitrate_kbps,
                station.radio_browser_id,
            ),
        )
        self._commit()
        new_id: int = cursor.lastrowid  # type: ignore[assignment]
        logger.debug("RadioStationRepository: insertada estación id=%d ('%s')", new_id, station.name)
        return RadioStation(
            id=new_id,
            name=station.name,
            stream_url=station.stream_url,
            country=station.country,
            genre=station.genre,
            logo_url=station.logo_url,
            is_favorite=station.is_favorite,
            added_at=station.added_at,
            bitrate_kbps=station.bitrate_kbps,
            radio_browser_id=station.radio_browser_id,
        )

    def _update(self, station: RadioStation) -> RadioStation:
        self._execute(
            """
            UPDATE radio_stations
               SET name             = ?,
                   stream_url       = ?,
                   country          = ?,
                   genre            = ?,
                   logo_url         = ?,
                   is_favorite      = ?,
                   bitrate_kbps     = ?,
                   radio_browser_id = ?
             WHERE id = ?
            """,
            (
                station.name,
                station.stream_url,
                station.country,
                station.genre,
                station.logo_url,
                1 if station.is_favorite else 0,
                station.bitrate_kbps,
                station.radio_browser_id,
                station.id,
            ),
        )
        self._commit()
        logger.debug("RadioStationRepository: actualizada estación id=%d ('%s')", station.id, station.name)
        return station

    @staticmethod
    def _row_to_station(row: sqlite3.Row) -> RadioStation:
        """Convierte una fila SQLite en una entidad RadioStation."""
        added_at_raw: str = row["added_at"]
        try:
            added_at = datetime.fromisoformat(added_at_raw)
        except (ValueError, TypeError):
            added_at = datetime.now()

        return RadioStation(
            id=row["id"],
            name=row["name"],
            stream_url=row["stream_url"],
            country=row["country"] or "",
            genre=row["genre"] or "",
            logo_url=row["logo_url"] or "",
            is_favorite=bool(row["is_favorite"]),
            added_at=added_at,
            bitrate_kbps=int(row["bitrate_kbps"]),
            radio_browser_id=row["radio_browser_id"] or "",
        )
