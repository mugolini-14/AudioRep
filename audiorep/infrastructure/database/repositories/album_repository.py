"""AlbumRepository — Implementa IAlbumRepository usando SQLite."""
from __future__ import annotations

import logging
from datetime import date

from audiorep.domain.album import Album
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AlbumRepository(BaseRepository):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    def get_by_id(self, album_id: int) -> Album | None:
        row = self._fetchone("SELECT * FROM albums WHERE id = ?", (album_id,))
        return self._row_to_album(row) if row else None

    def get_all(self) -> list[Album]:
        rows = self._fetchall("SELECT * FROM albums ORDER BY artist_name ASC, title ASC")
        return [self._row_to_album(r) for r in rows]

    def search(self, query: str) -> list[Album]:
        rows = self._fetchall(
            "SELECT * FROM albums WHERE title LIKE ? OR artist_name LIKE ? ORDER BY title ASC",
            (f"%{query}%", f"%{query}%"))
        return [self._row_to_album(r) for r in rows]

    def save(self, album: Album) -> Album:
        if album.id is None:
            return self._insert(album)
        return self._update(album)

    def delete(self, album_id: int) -> None:
        self._execute("DELETE FROM albums WHERE id = ?", (album_id,))
        self._commit()

    def get_or_create(self, title: str, artist_id: int, artist_name: str) -> Album:
        row = self._fetchone(
            "SELECT * FROM albums WHERE title = ? AND artist_id = ?", (title, artist_id))
        if row:
            return self._row_to_album(row)
        album = Album(title=title, artist_id=artist_id, artist_name=artist_name)
        return self._insert(album)

    def _insert(self, album: Album) -> Album:
        rd = album.release_date.isoformat() if album.release_date else None
        cur = self._execute(
            """INSERT INTO albums (title, artist_id, artist_name, year, release_date, genre,
               label, musicbrainz_id, cover_path, total_tracks, total_discs, release_type)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (album.title, album.artist_id, album.artist_name, album.year, rd,
             album.genre, album.label, album.musicbrainz_id, album.cover_path,
             album.total_tracks, album.total_discs, album.release_type),
        )
        self._commit()
        return Album(id=cur.lastrowid, title=album.title, artist_id=album.artist_id,
                     artist_name=album.artist_name, year=album.year,
                     release_date=album.release_date, genre=album.genre, label=album.label,
                     musicbrainz_id=album.musicbrainz_id, cover_path=album.cover_path,
                     total_tracks=album.total_tracks, total_discs=album.total_discs,
                     release_type=album.release_type)

    def _update(self, album: Album) -> Album:
        rd = album.release_date.isoformat() if album.release_date else None
        self._execute(
            """UPDATE albums SET title=?, artist_id=?, artist_name=?, year=?, release_date=?,
               genre=?, label=?, musicbrainz_id=?, cover_path=?, total_tracks=?, total_discs=?,
               release_type=? WHERE id=?""",
            (album.title, album.artist_id, album.artist_name, album.year, rd,
             album.genre, album.label, album.musicbrainz_id, album.cover_path,
             album.total_tracks, album.total_discs, album.release_type, album.id),
        )
        self._commit()
        return album

    def delete_all(self) -> None:
        self._execute("DELETE FROM albums")
        self._commit()

    def update_release_type(self, title: str, artist_name: str, release_type: str) -> None:
        """Actualiza release_type del primer álbum que coincida por título y artista."""
        self._execute(
            "UPDATE albums SET release_type=? WHERE title=? AND artist_name=? AND release_type=''",
            (release_type, title, artist_name),
        )
        self._commit()

    @staticmethod
    def _row_to_album(row) -> Album:
        rd = None
        if row["release_date"]:
            try:
                rd = date.fromisoformat(row["release_date"])
            except Exception:
                pass
        release_type = ""
        try:
            release_type = row["release_type"] or ""
        except (IndexError, KeyError):
            pass
        return Album(id=row["id"], title=row["title"], artist_id=row["artist_id"],
                     artist_name=row["artist_name"] or "", year=row["year"],
                     release_date=rd, genre=row["genre"] or "", label=row["label"] or "",
                     musicbrainz_id=row["musicbrainz_id"], cover_path=row["cover_path"],
                     total_tracks=int(row["total_tracks"]), total_discs=int(row["total_discs"]),
                     release_type=release_type)
