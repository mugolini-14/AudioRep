"""
Repository de Playlists.

Implementa IPlaylistRepository usando SQLite.
Carga las entradas (playlist_entries) junto con cada Playlist.
"""
from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime

from audiorep.domain.playlist import Playlist, PlaylistEntry
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PlaylistRepository(BaseRepository):
    """CRUD de playlists y sus entradas sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Mapeo rows → dominio
    # ------------------------------------------------------------------

    def _to_playlist(self, row: sqlite3.Row) -> Playlist:
        """Construye un Playlist con sus entradas cargadas."""
        playlist = Playlist(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            is_smart=bool(row["is_smart"]),
            smart_query=json.loads(row["smart_query_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        playlist.entries = self._load_entries(playlist.id)  # type: ignore[arg-type]
        return playlist

    def _load_entries(self, playlist_id: int) -> list[PlaylistEntry]:
        rows = self._db.execute(
            """
            SELECT track_id, position, added_at
            FROM playlist_entries
            WHERE playlist_id = ?
            ORDER BY position
            """,
            (playlist_id,),
        ).fetchall()
        return [
            PlaylistEntry(
                track_id=r["track_id"],
                position=r["position"],
                added_at=datetime.fromisoformat(r["added_at"]),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        return self._fetch_one(
            "SELECT * FROM playlists WHERE id = ?",
            (playlist_id,),
            self._to_playlist,
        )

    def get_all(self) -> list[Playlist]:
        return self._fetch_all(
            "SELECT * FROM playlists ORDER BY name COLLATE NOCASE",
            (),
            self._to_playlist,
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def save(self, playlist: Playlist) -> Playlist:
        if playlist.id is None:
            return self._insert_playlist(playlist)
        return self._update_playlist(playlist)

    def _insert_playlist(self, playlist: Playlist) -> Playlist:
        new_id = self._insert(
            """
            INSERT INTO playlists (name, description, is_smart, smart_query_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                playlist.name,
                playlist.description,
                int(playlist.is_smart),
                json.dumps(playlist.smart_query),
            ),
        )
        playlist.id = new_id
        self._save_entries(playlist)
        logger.debug("Playlist insertada: id=%d, name=%r", new_id, playlist.name)
        return playlist

    def _update_playlist(self, playlist: Playlist) -> Playlist:
        self._update(
            """
            UPDATE playlists
            SET name = ?, description = ?, is_smart = ?,
                smart_query_json = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                playlist.name,
                playlist.description,
                int(playlist.is_smart),
                json.dumps(playlist.smart_query),
                playlist.id,
            ),
        )
        # Reemplazar entradas: eliminar las viejas e insertar las actuales
        self._delete(
            "DELETE FROM playlist_entries WHERE playlist_id = ?",
            (playlist.id,),
        )
        self._save_entries(playlist)
        logger.debug("Playlist actualizada: id=%d", playlist.id)
        return playlist

    def _save_entries(self, playlist: Playlist) -> None:
        """Inserta todas las entradas actuales de la playlist."""
        if not playlist.entries or playlist.id is None:
            return
        self._db.executemany(
            """
            INSERT INTO playlist_entries (playlist_id, track_id, position, added_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (playlist.id, e.track_id, e.position, e.added_at.isoformat())
                for e in playlist.entries
            ],
        )
        self._db.commit()

    def delete(self, playlist_id: int) -> None:
        """Elimina la playlist. Las entradas se borran en cascada (FK)."""
        self._delete("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        logger.debug("Playlist eliminada: id=%d", playlist_id)

    # ------------------------------------------------------------------
    # Operaciones especializadas
    # ------------------------------------------------------------------

    def add_track(self, playlist_id: int, track_id: int) -> None:
        """Agrega una pista al final de la playlist sin cargar toda la entidad."""
        row = self._db.execute(
            "SELECT COALESCE(MAX(position), 0) FROM playlist_entries WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        next_position = row[0] + 1
        self._insert(
            """
            INSERT INTO playlist_entries (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            """,
            (playlist_id, track_id, next_position),
        )
        self._update(
            "UPDATE playlists SET updated_at = datetime('now') WHERE id = ?",
            (playlist_id,),
        )

    def remove_track(self, playlist_id: int, track_id: int) -> None:
        """Elimina todas las apariciones de una pista en la playlist."""
        self._delete(
            "DELETE FROM playlist_entries WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id),
        )
        self._update(
            "UPDATE playlists SET updated_at = datetime('now') WHERE id = ?",
            (playlist_id,),
        )
