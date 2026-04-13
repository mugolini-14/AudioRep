"""TrackRepository — Implementa ITrackRepository usando SQLite."""
from __future__ import annotations

import logging

from audiorep.domain.track import Track, AudioFormat, TrackSource
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TrackRepository(BaseRepository):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    def get_by_id(self, track_id: int) -> Track | None:
        row = self._fetchone("SELECT * FROM tracks WHERE id = ?", (track_id,))
        return self._row_to_track(row) if row else None

    def get_all(self) -> list[Track]:
        rows = self._fetchall("SELECT * FROM tracks ORDER BY artist_name, album_title, track_number")
        return [self._row_to_track(r) for r in rows]

    def search(self, query: str) -> list[Track]:
        q = f"%{query}%"
        rows = self._fetchall(
            "SELECT * FROM tracks WHERE title LIKE ? OR artist_name LIKE ? OR album_title LIKE ?"
            " ORDER BY artist_name, album_title, track_number",
            (q, q, q))
        return [self._row_to_track(r) for r in rows]

    def save(self, track: Track) -> Track:
        if track.id is None:
            return self._insert(track)
        return self._update(track)

    def delete(self, track_id: int) -> None:
        self._execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        self._commit()

    def update_tags(self, track: Track) -> None:
        self._execute(
            "UPDATE tracks SET title=?, artist_name=?, album_title=?, track_number=?, "
            "disc_number=?, year=?, genre=?, musicbrainz_id=?, acoustid=? WHERE id=?",
            (track.title, track.artist_name, track.album_title, track.track_number,
             track.disc_number, track.year, track.genre, track.musicbrainz_id,
             track.acoustid, track.id))
        self._commit()

    def get_most_played(self, limit: int = 25) -> list[Track]:
        rows = self._fetchall(
            "SELECT * FROM tracks WHERE play_count > 0 ORDER BY play_count DESC LIMIT ?", (limit,))
        return [self._row_to_track(r) for r in rows]

    def get_highest_rated(self, limit: int = 25) -> list[Track]:
        rows = self._fetchall(
            "SELECT * FROM tracks WHERE rating > 0 ORDER BY rating DESC, play_count DESC LIMIT ?",
            (limit,))
        return [self._row_to_track(r) for r in rows]

    def get_recently_added(self, limit: int = 50) -> list[Track]:
        rows = self._fetchall(
            "SELECT * FROM tracks ORDER BY added_at DESC LIMIT ?", (limit,))
        return [self._row_to_track(r) for r in rows]

    def increment_play_count(self, track_id: int) -> None:
        self._execute("UPDATE tracks SET play_count = play_count + 1 WHERE id = ?", (track_id,))
        self._commit()

    def _insert(self, track: Track) -> Track:
        cur = self._execute(
            """INSERT INTO tracks (title, artist_name, album_title, album_id, artist_id,
               track_number, disc_number, duration_ms, year, genre, file_path, format, source,
               bitrate_kbps, musicbrainz_id, acoustid, play_count, rating)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (track.title, track.artist_name, track.album_title, track.album_id, track.artist_id,
             track.track_number, track.disc_number, track.duration_ms, track.year, track.genre,
             track.file_path, track.format.value if track.format else "UNKNOWN",
             track.source.value if track.source else "LOCAL",
             track.bitrate_kbps, track.musicbrainz_id, track.acoustid,
             track.play_count, track.rating))
        self._commit()
        track.id = cur.lastrowid
        return track

    def _update(self, track: Track) -> Track:
        self._execute(
            """UPDATE tracks SET title=?, artist_name=?, album_title=?, album_id=?, artist_id=?,
               track_number=?, disc_number=?, duration_ms=?, year=?, genre=?, file_path=?,
               format=?, source=?, bitrate_kbps=?, musicbrainz_id=?, acoustid=?,
               play_count=?, rating=? WHERE id=?""",
            (track.title, track.artist_name, track.album_title, track.album_id, track.artist_id,
             track.track_number, track.disc_number, track.duration_ms, track.year, track.genre,
             track.file_path, track.format.value if track.format else "UNKNOWN",
             track.source.value if track.source else "LOCAL",
             track.bitrate_kbps, track.musicbrainz_id, track.acoustid,
             track.play_count, track.rating, track.id))
        self._commit()
        return track

    @staticmethod
    def _row_to_track(row) -> Track:
        try:
            fmt = AudioFormat(row["format"])
        except ValueError:
            fmt = AudioFormat.UNKNOWN
        try:
            src = TrackSource(row["source"])
        except ValueError:
            src = TrackSource.LOCAL
        return Track(
            id=row["id"], title=row["title"] or "",
            artist_name=row["artist_name"] or "", album_title=row["album_title"] or "",
            album_id=row["album_id"], artist_id=row["artist_id"],
            track_number=int(row["track_number"]), disc_number=int(row["disc_number"]),
            duration_ms=int(row["duration_ms"]), year=row["year"],
            genre=row["genre"] or "", file_path=row["file_path"],
            format=fmt, source=src, bitrate_kbps=int(row["bitrate_kbps"]),
            musicbrainz_id=row["musicbrainz_id"], acoustid=row["acoustid"],
            play_count=int(row["play_count"]), rating=int(row["rating"]))
