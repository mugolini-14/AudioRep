"""PlaylistRepository — Implementa IPlaylistRepository usando SQLite."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from audiorep.domain.playlist import Playlist, PlaylistEntry
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PlaylistRepository(BaseRepository):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        row = self._fetchone("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
        if row is None:
            return None
        return self._row_to_playlist(row)

    def get_all(self) -> list[Playlist]:
        rows = self._fetchall("SELECT * FROM playlists ORDER BY name")
        return [self._row_to_playlist(r) for r in rows]

    def save(self, playlist: Playlist) -> Playlist:
        if playlist.id is None:
            return self._insert(playlist)
        return self._update(playlist)

    def delete(self, playlist_id: int) -> None:
        self._execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self._commit()

    def add_track(self, playlist_id: int, track_id: int) -> None:
        max_pos = self._fetchone(
            "SELECT MAX(position) FROM playlist_entries WHERE playlist_id = ?",
            (playlist_id,),
        )
        position = (max_pos[0] or 0) + 1 if max_pos and max_pos[0] is not None else 0
        self._execute(
            "INSERT OR IGNORE INTO playlist_entries (playlist_id, track_id, position) VALUES (?,?,?)",
            (playlist_id, track_id, position),
        )
        self._commit()

    def remove_track(self, playlist_id: int, track_id: int) -> None:
        self._execute(
            "DELETE FROM playlist_entries WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id),
        )
        self._commit()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _insert(self, playlist: Playlist) -> Playlist:
        cur = self._execute(
            "INSERT INTO playlists (name, is_smart, smart_query) VALUES (?,?,?)",
            (playlist.name, int(playlist.is_smart), json.dumps(playlist.smart_query)),
        )
        self._commit()
        playlist.id = cur.lastrowid
        return playlist

    def _update(self, playlist: Playlist) -> Playlist:
        self._execute(
            "UPDATE playlists SET name=?, is_smart=?, smart_query=? WHERE id=?",
            (playlist.name, int(playlist.is_smart), json.dumps(playlist.smart_query), playlist.id),
        )
        self._commit()
        return playlist

    def _row_to_playlist(self, row) -> Playlist:
        # Convertir a dict para usar .get() — sqlite3.Row lanza IndexError
        # si la columna no existe (puede pasar en DBs creadas por versiones anteriores).
        d = dict(row)
        entries = self._load_entries(d["id"])
        try:
            smart_query = json.loads(d.get("smart_query") or "{}")
        except (json.JSONDecodeError, TypeError):
            smart_query = {}
        return Playlist(
            id=d["id"],
            name=d["name"],
            is_smart=bool(d.get("is_smart", 0)),
            smart_query=smart_query,
            entries=entries,
        )

    def _load_entries(self, playlist_id: int) -> list[PlaylistEntry]:
        rows = self._fetchall(
            "SELECT * FROM playlist_entries WHERE playlist_id = ? ORDER BY position",
            (playlist_id,),
        )
        entries = []
        for r in rows:
            try:
                added_at = datetime.fromisoformat(r["added_at"])
            except (ValueError, TypeError):
                added_at = datetime.now()
            entries.append(PlaylistEntry(
                id=r["id"],
                track_id=r["track_id"],
                position=r["position"],
                added_at=added_at,
            ))
        return entries
