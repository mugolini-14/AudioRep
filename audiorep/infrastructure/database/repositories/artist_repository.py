"""
Repository de Artists.

Implementa IArtistRepository usando SQLite.
Traduce entre sqlite3.Row y la entidad de dominio Artist.
"""
from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime

from audiorep.domain.artist import Artist
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ArtistRepository(BaseRepository):
    """CRUD de artistas sobre SQLite."""

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Mapeo row → dominio
    # ------------------------------------------------------------------

    @staticmethod
    def _to_artist(row: sqlite3.Row) -> Artist:
        return Artist(
            id=row["id"],
            name=row["name"],
            sort_name=row["sort_name"],
            musicbrainz_id=row["musicbrainz_id"],
            biography=row["biography"],
            genres=json.loads(row["genres_json"]),
        )

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get_by_id(self, artist_id: int) -> Artist | None:
        return self._fetch_one(
            "SELECT * FROM artists WHERE id = ?",
            (artist_id,),
            self._to_artist,
        )

    def get_all(self) -> list[Artist]:
        return self._fetch_all(
            "SELECT * FROM artists ORDER BY sort_name COLLATE NOCASE",
            (),
            self._to_artist,
        )

    def search(self, query: str) -> list[Artist]:
        """Búsqueda por nombre (insensible a mayúsculas)."""
        return self._fetch_all(
            "SELECT * FROM artists WHERE name LIKE ? ESCAPE '\\' "
            "ORDER BY sort_name COLLATE NOCASE",
            (self._like(query),),
            self._to_artist,
        )

    def get_by_musicbrainz_id(self, mbid: str) -> Artist | None:
        return self._fetch_one(
            "SELECT * FROM artists WHERE musicbrainz_id = ?",
            (mbid,),
            self._to_artist,
        )

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def save(self, artist: Artist) -> Artist:
        """
        Inserta o actualiza un artista.
        Si artist.id es None, inserta y asigna el nuevo ID.
        Si artist.id tiene valor, actualiza.
        """
        if artist.id is None:
            return self._insert_artist(artist)
        return self._update_artist(artist)

    def _insert_artist(self, artist: Artist) -> Artist:
        new_id = self._insert(
            """
            INSERT INTO artists (name, sort_name, musicbrainz_id, biography, genres_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                artist.name,
                artist.sort_name,
                artist.musicbrainz_id,
                artist.biography,
                json.dumps(artist.genres),
            ),
        )
        artist.id = new_id
        logger.debug("Artist insertado: id=%d, name=%r", new_id, artist.name)
        return artist

    def _update_artist(self, artist: Artist) -> Artist:
        self._update(
            """
            UPDATE artists
            SET name = ?, sort_name = ?, musicbrainz_id = ?,
                biography = ?, genres_json = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                artist.name,
                artist.sort_name,
                artist.musicbrainz_id,
                artist.biography,
                json.dumps(artist.genres),
                artist.id,
            ),
        )
        logger.debug("Artist actualizado: id=%d", artist.id)
        return artist

    def delete(self, artist_id: int) -> None:
        """Elimina el artista. Las pistas y álbumes quedan con artist_id=NULL."""
        self._delete("DELETE FROM artists WHERE id = ?", (artist_id,))
        logger.debug("Artist eliminado: id=%d", artist_id)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def get_or_create(self, name: str) -> Artist:
        """
        Retorna el artista con ese nombre, o lo crea si no existe.
        Útil al importar pistas sin saber si el artista ya está en la BD.
        """
        existing = self._fetch_one(
            "SELECT * FROM artists WHERE name = ? COLLATE NOCASE",
            (name,),
            self._to_artist,
        )
        if existing:
            return existing
        return self.save(Artist(name=name))
