"""
Repository de Albums.

Implementa IAlbumRepository usando SQLite.
"""
from __future__ import annotations

import json
import sqlite3
import logging
from datetime import date

from audiorep.domain.album import Album
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AlbumRepository(BaseRepository):
    """CRUD de álbumes sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Mapeo row → dominio
    # ------------------------------------------------------------------

    @staticmethod
    def _to_album(row: sqlite3.Row) -> Album:
        release_date: date | None = None
        if row["release_date"]:
            try:
                release_date = date.fromisoformat(row["release_date"])
            except ValueError:
                pass

        return Album(
            id=row["id"],
            title=row["title"],
            artist_id=row["artist_id"],
            artist_name=row["artist_name"],
            year=row["year"],
            release_date=release_date,
            genre=row["genre"],
            genres=json.loads(row["genres_json"]),
            label=row["label"],
            catalog_number=row["catalog_number"],
            musicbrainz_id=row["musicbrainz_id"],
            cover_path=row["cover_path"],
            total_tracks=row["total_tracks"],
            total_discs=row["total_discs"],
            comment=row["comment"],
        )

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, album_id: int) -> Album | None:
        return self._fetch_one(
            "SELECT * FROM albums WHERE id = ?",
            (album_id,),
            self._to_album,
        )

    def get_all(self) -> list[Album]:
        return self._fetch_all(
            "SELECT * FROM albums ORDER BY artist_name COLLATE NOCASE, year, title COLLATE NOCASE",
            (),
            self._to_album,
        )

    def search(self, query: str) -> list[Album]:
        """Búsqueda por título o nombre de artista."""
        pattern = self._like(query)
        return self._fetch_all(
            """
            SELECT * FROM albums
            WHERE title LIKE ? ESCAPE '\\'
               OR artist_name LIKE ? ESCAPE '\\'
            ORDER BY artist_name COLLATE NOCASE, year
            """,
            (pattern, pattern),
            self._to_album,
        )

    def get_by_artist(self, artist_id: int) -> list[Album]:
        return self._fetch_all(
            "SELECT * FROM albums WHERE artist_id = ? ORDER BY year, title COLLATE NOCASE",
            (artist_id,),
            self._to_album,
        )

    def get_by_musicbrainz_id(self, mbid: str) -> Album | None:
        return self._fetch_one(
            "SELECT * FROM albums WHERE musicbrainz_id = ?",
            (mbid,),
            self._to_album,
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def save(self, album: Album) -> Album:
        if album.id is None:
            return self._insert_album(album)
        return self._update_album(album)

    def _insert_album(self, album: Album) -> Album:
        new_id = self._insert(
            """
            INSERT INTO albums (
                title, artist_id, artist_name, year, release_date, genre,
                genres_json, label, catalog_number, musicbrainz_id,
                cover_path, total_tracks, total_discs, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                album.title,
                album.artist_id,
                album.artist_name,
                album.year,
                album.release_date.isoformat() if album.release_date else None,
                album.genre,
                json.dumps(album.genres),
                album.label,
                album.catalog_number,
                album.musicbrainz_id,
                album.cover_path,
                album.total_tracks,
                album.total_discs,
                album.comment,
            ),
        )
        album.id = new_id
        logger.debug("Album insertado: id=%d, title=%r", new_id, album.title)
        return album

    def _update_album(self, album: Album) -> Album:
        self._update(
            """
            UPDATE albums
            SET title = ?, artist_id = ?, artist_name = ?, year = ?,
                release_date = ?, genre = ?, genres_json = ?, label = ?,
                catalog_number = ?, musicbrainz_id = ?, cover_path = ?,
                total_tracks = ?, total_discs = ?, comment = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                album.title,
                album.artist_id,
                album.artist_name,
                album.year,
                album.release_date.isoformat() if album.release_date else None,
                album.genre,
                json.dumps(album.genres),
                album.label,
                album.catalog_number,
                album.musicbrainz_id,
                album.cover_path,
                album.total_tracks,
                album.total_discs,
                album.comment,
                album.id,
            ),
        )
        logger.debug("Album actualizado: id=%d", album.id)
        return album

    def delete(self, album_id: int) -> None:
        """Elimina el álbum. Las pistas quedan con album_id=NULL."""
        self._delete("DELETE FROM albums WHERE id = ?", (album_id,))
        logger.debug("Album eliminado: id=%d", album_id)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def get_or_create(self, title: str, artist_id: int | None, artist_name: str) -> Album:
        """
        Retorna el álbum con ese título y artista, o lo crea si no existe.
        """
        existing = self._fetch_one(
            """
            SELECT * FROM albums
            WHERE title = ? COLLATE NOCASE
              AND (artist_id = ? OR (artist_id IS NULL AND ? IS NULL))
            """,
            (title, artist_id, artist_id),
            self._to_album,
        )
        if existing:
            return existing
        return self.save(Album(title=title, artist_id=artist_id, artist_name=artist_name))

    def update_cover(self, album_id: int, cover_path: str) -> None:
        """Actualiza solo la ruta de la portada (operación frecuente)."""
        self._update(
            "UPDATE albums SET cover_path = ?, updated_at = datetime('now') WHERE id = ?",
            (cover_path, album_id),
        )
