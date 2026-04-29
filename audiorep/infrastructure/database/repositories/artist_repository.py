"""ArtistRepository — Implementa IArtistRepository usando SQLite."""
from __future__ import annotations

import logging

from audiorep.domain.artist import Artist
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ArtistRepository(BaseRepository):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    def get_by_id(self, artist_id: int) -> Artist | None:
        row = self._fetchone("SELECT * FROM artists WHERE id = ?", (artist_id,))
        return self._row_to_artist(row) if row else None

    def get_all(self) -> list[Artist]:
        rows = self._fetchall("SELECT * FROM artists ORDER BY sort_name ASC, name ASC")
        return [self._row_to_artist(r) for r in rows]

    def search(self, query: str) -> list[Artist]:
        rows = self._fetchall("SELECT * FROM artists WHERE name LIKE ? ORDER BY name ASC",
                              (f"%{query}%",))
        return [self._row_to_artist(r) for r in rows]

    def save(self, artist: Artist) -> Artist:
        if artist.id is None:
            return self._insert(artist)
        return self._update(artist)

    def delete(self, artist_id: int) -> None:
        self._execute("DELETE FROM artists WHERE id = ?", (artist_id,))
        self._commit()

    def get_or_create(self, name: str) -> Artist:
        row = self._fetchone("SELECT * FROM artists WHERE name = ?", (name,))
        if row:
            return self._row_to_artist(row)
        artist = Artist(name=name, sort_name=name)
        return self._insert(artist)

    def _insert(self, artist: Artist) -> Artist:
        import json
        cur = self._execute(
            "INSERT INTO artists (name, sort_name, musicbrainz_id, genres, country) VALUES (?,?,?,?,?)",
            (artist.name, artist.sort_name or artist.name,
             artist.musicbrainz_id, json.dumps(artist.genres), artist.country),
        )
        self._commit()
        return Artist(id=cur.lastrowid, name=artist.name, sort_name=artist.sort_name,
                      musicbrainz_id=artist.musicbrainz_id, genres=artist.genres,
                      country=artist.country)

    def _update(self, artist: Artist) -> Artist:
        import json
        self._execute(
            "UPDATE artists SET name=?, sort_name=?, musicbrainz_id=?, genres=?, country=? WHERE id=?",
            (artist.name, artist.sort_name or artist.name,
             artist.musicbrainz_id, json.dumps(artist.genres), artist.country, artist.id),
        )
        self._commit()
        return artist

    def delete_all(self) -> None:
        self._execute("DELETE FROM artists")
        self._commit()

    def update_country(self, name: str, country: str) -> None:
        """Actualiza el país del artista si aún no tiene uno asignado."""
        self._execute(
            "UPDATE artists SET country=? WHERE name=? AND country=''",
            (country, name),
        )
        self._commit()

    @staticmethod
    def _row_to_artist(row) -> Artist:
        import json
        try:
            genres = json.loads(row["genres"] or "[]")
        except Exception:
            genres = []
        country = ""
        try:
            country = row["country"] or ""
        except (IndexError, KeyError):
            pass
        return Artist(id=row["id"], name=row["name"], sort_name=row["sort_name"] or "",
                      musicbrainz_id=row["musicbrainz_id"], genres=genres, country=country)
