"""
Repository de Tracks.

Implementa ITrackRepository usando SQLite.
Es el repository más usado de la aplicación.
"""
from __future__ import annotations

import sqlite3
import logging

from audiorep.domain.track import Track, AudioFormat, TrackSource
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TrackRepository(BaseRepository):
    """CRUD de pistas de audio sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Mapeo row → dominio
    # ------------------------------------------------------------------

    @staticmethod
    def _to_track(row: sqlite3.Row) -> Track:
        return Track(
            id=row["id"],
            title=row["title"],
            artist_id=row["artist_id"],
            artist_name=row["artist_name"],
            album_id=row["album_id"],
            album_title=row["album_title"],
            track_number=row["track_number"],
            disc_number=row["disc_number"],
            duration_ms=row["duration_ms"],
            year=row["year"],
            genre=row["genre"],
            file_path=row["file_path"],
            format=AudioFormat(row["format"]),
            source=TrackSource(row["source"]),
            bitrate_kbps=row["bitrate_kbps"],
            sample_rate_hz=row["sample_rate_hz"],
            channels=row["channels"],
            file_size_bytes=row["file_size_bytes"],
            musicbrainz_id=row["musicbrainz_id"],
            acoustid=row["acoustid"],
            play_count=row["play_count"],
            rating=row["rating"],
            comment=row["comment"],
            lyrics=row["lyrics"],
        )

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, track_id: int) -> Track | None:
        return self._fetch_one(
            "SELECT * FROM tracks WHERE id = ?",
            (track_id,),
            self._to_track,
        )

    def get_all(self) -> list[Track]:
        return self._fetch_all(
            """
            SELECT * FROM tracks
            ORDER BY artist_name COLLATE NOCASE,
                     album_title COLLATE NOCASE,
                     disc_number,
                     track_number
            """,
            (),
            self._to_track,
        )

    def get_by_album(self, album_id: int) -> list[Track]:
        return self._fetch_all(
            """
            SELECT * FROM tracks WHERE album_id = ?
            ORDER BY disc_number, track_number
            """,
            (album_id,),
            self._to_track,
        )

    def get_by_artist(self, artist_id: int) -> list[Track]:
        return self._fetch_all(
            """
            SELECT * FROM tracks WHERE artist_id = ?
            ORDER BY album_title COLLATE NOCASE, disc_number, track_number
            """,
            (artist_id,),
            self._to_track,
        )

    def get_by_ids(self, track_ids: list[int]) -> list[Track]:
        """Retorna varias pistas por sus IDs, conservando el orden dado."""
        if not track_ids:
            return []
        placeholders = ",".join("?" * len(track_ids))
        rows = self._db.execute(
            f"SELECT * FROM tracks WHERE id IN ({placeholders})", tuple(track_ids)
        ).fetchall()
        # Reordenar según el orden de track_ids
        by_id = {r["id"]: self._to_track(r) for r in rows}
        return [by_id[tid] for tid in track_ids if tid in by_id]

    def search(self, query: str) -> list[Track]:
        """Búsqueda por título, artista o álbum."""
        pattern = self._like(query)
        return self._fetch_all(
            """
            SELECT * FROM tracks
            WHERE title       LIKE ? ESCAPE '\\'
               OR artist_name LIKE ? ESCAPE '\\'
               OR album_title LIKE ? ESCAPE '\\'
            ORDER BY artist_name COLLATE NOCASE, album_title COLLATE NOCASE, track_number
            """,
            (pattern, pattern, pattern),
            self._to_track,
        )

    def exists_by_path(self, file_path: str) -> bool:
        """Indica si ya existe una pista con esa ruta de archivo."""
        row = self._db.execute(
            "SELECT 1 FROM tracks WHERE file_path = ? LIMIT 1", (file_path,)
        ).fetchone()
        return row is not None

    def get_most_played(self, limit: int = 25) -> list[Track]:
        return self._fetch_all(
            "SELECT * FROM tracks ORDER BY play_count DESC LIMIT ?",
            (limit,),
            self._to_track,
        )

    def get_highest_rated(self, limit: int = 25) -> list[Track]:
        return self._fetch_all(
            "SELECT * FROM tracks WHERE rating > 0 ORDER BY rating DESC, play_count DESC LIMIT ?",
            (limit,),
            self._to_track,
        )

    def get_recently_added(self, limit: int = 50) -> list[Track]:
        return self._fetch_all(
            "SELECT * FROM tracks ORDER BY created_at DESC LIMIT ?",
            (limit,),
            self._to_track,
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def save(self, track: Track) -> Track:
        if track.id is None:
            return self._insert_track(track)
        return self._update_track(track)

    def _insert_track(self, track: Track) -> Track:
        new_id = self._insert(
            """
            INSERT INTO tracks (
                title, artist_id, artist_name, album_id, album_title,
                track_number, disc_number, duration_ms, year, genre,
                file_path, format, source, bitrate_kbps, sample_rate_hz,
                channels, file_size_bytes, musicbrainz_id, acoustid,
                play_count, rating, comment, lyrics
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                track.title,
                track.artist_id,
                track.artist_name,
                track.album_id,
                track.album_title,
                track.track_number,
                track.disc_number,
                track.duration_ms,
                track.year,
                track.genre,
                track.file_path,
                track.format.value,
                track.source.value,
                track.bitrate_kbps,
                track.sample_rate_hz,
                track.channels,
                track.file_size_bytes,
                track.musicbrainz_id,
                track.acoustid,
                track.play_count,
                track.rating,
                track.comment,
                track.lyrics,
            ),
        )
        track.id = new_id
        logger.debug("Track insertado: id=%d, title=%r", new_id, track.title)
        return track

    def _update_track(self, track: Track) -> Track:
        self._update(
            """
            UPDATE tracks
            SET title = ?, artist_id = ?, artist_name = ?, album_id = ?,
                album_title = ?, track_number = ?, disc_number = ?,
                duration_ms = ?, year = ?, genre = ?, file_path = ?,
                format = ?, source = ?, bitrate_kbps = ?, sample_rate_hz = ?,
                channels = ?, file_size_bytes = ?, musicbrainz_id = ?,
                acoustid = ?, play_count = ?, rating = ?, comment = ?,
                lyrics = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                track.title,
                track.artist_id,
                track.artist_name,
                track.album_id,
                track.album_title,
                track.track_number,
                track.disc_number,
                track.duration_ms,
                track.year,
                track.genre,
                track.file_path,
                track.format.value,
                track.source.value,
                track.bitrate_kbps,
                track.sample_rate_hz,
                track.channels,
                track.file_size_bytes,
                track.musicbrainz_id,
                track.acoustid,
                track.play_count,
                track.rating,
                track.comment,
                track.lyrics,
                track.id,
            ),
        )
        logger.debug("Track actualizado: id=%d", track.id)
        return track

    def delete(self, track_id: int) -> None:
        """Elimina la pista. Las entradas en playlists se eliminan en cascada."""
        self._delete("DELETE FROM tracks WHERE id = ?", (track_id,))
        logger.debug("Track eliminado: id=%d", track_id)

    # ------------------------------------------------------------------
    # Operaciones especializadas
    # ------------------------------------------------------------------

    def increment_play_count(self, track_id: int) -> None:
        """Incrementa el contador de reproducciones en 1."""
        self._update(
            "UPDATE tracks SET play_count = play_count + 1, updated_at = datetime('now') WHERE id = ?",
            (track_id,),
        )

    def set_rating(self, track_id: int, rating: int) -> None:
        """Actualiza la puntuación (0–5)."""
        self._update(
            "UPDATE tracks SET rating = ?, updated_at = datetime('now') WHERE id = ?",
            (max(0, min(5, rating)), track_id),
        )

    def update_tags(self, track: Track) -> None:
        """
        Actualiza solo los campos de metadatos/tags de una pista.
        Más eficiente que save() cuando solo cambió el tagging.
        """
        self._update(
            """
            UPDATE tracks
            SET title = ?, artist_id = ?, artist_name = ?, album_id = ?,
                album_title = ?, track_number = ?, disc_number = ?,
                year = ?, genre = ?, musicbrainz_id = ?, comment = ?,
                lyrics = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                track.title,
                track.artist_id,
                track.artist_name,
                track.album_id,
                track.album_title,
                track.track_number,
                track.disc_number,
                track.year,
                track.genre,
                track.musicbrainz_id,
                track.comment,
                track.lyrics,
                track.id,
            ),
        )
