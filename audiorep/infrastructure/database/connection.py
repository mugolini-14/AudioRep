"""
Conexión a la base de datos SQLite de AudioRep.

Responsabilidades:
    - Abrir / cerrar la conexión a SQLite.
    - Ejecutar el sistema de migraciones al arranque.
    - Proveer un cursor thread-safe para los repositories.

Uso típico:
    db = DatabaseConnection("audiorep.db")
    db.connect()
    # ... pasar db a los repositories ...
    db.close()

    # O como context manager:
    with DatabaseConnection("audiorep.db") as db:
        repo = TrackRepository(db)
"""
from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Migraciones
# ------------------------------------------------------------------
# Cada entrada es la SQL completa de una versión.
# NUNCA se modifica una migración existente; solo se agregan nuevas al final.
# ------------------------------------------------------------------
_MIGRATIONS: list[str] = [
    # ── Migración 0001: schema inicial ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version     INTEGER PRIMARY KEY,
        applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS artists (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        name              TEXT    NOT NULL,
        sort_name         TEXT    NOT NULL DEFAULT '',
        musicbrainz_id    TEXT,
        biography         TEXT    NOT NULL DEFAULT '',
        genres_json       TEXT    NOT NULL DEFAULT '[]',
        created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS albums (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        title             TEXT    NOT NULL,
        artist_id         INTEGER REFERENCES artists(id) ON DELETE SET NULL,
        artist_name       TEXT    NOT NULL DEFAULT '',
        year              INTEGER,
        release_date      TEXT,
        genre             TEXT    NOT NULL DEFAULT '',
        genres_json       TEXT    NOT NULL DEFAULT '[]',
        label             TEXT    NOT NULL DEFAULT '',
        catalog_number    TEXT    NOT NULL DEFAULT '',
        musicbrainz_id    TEXT,
        cover_path        TEXT,
        total_tracks      INTEGER NOT NULL DEFAULT 0,
        total_discs       INTEGER NOT NULL DEFAULT 1,
        comment           TEXT    NOT NULL DEFAULT '',
        created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS tracks (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        title             TEXT    NOT NULL,
        artist_id         INTEGER REFERENCES artists(id) ON DELETE SET NULL,
        artist_name       TEXT    NOT NULL DEFAULT '',
        album_id          INTEGER REFERENCES albums(id) ON DELETE SET NULL,
        album_title       TEXT    NOT NULL DEFAULT '',
        track_number      INTEGER NOT NULL DEFAULT 0,
        disc_number       INTEGER NOT NULL DEFAULT 1,
        duration_ms       INTEGER NOT NULL DEFAULT 0,
        year              INTEGER,
        genre             TEXT    NOT NULL DEFAULT '',
        file_path         TEXT,
        format            TEXT    NOT NULL DEFAULT 'unknown',
        source            TEXT    NOT NULL DEFAULT 'local',
        bitrate_kbps      INTEGER NOT NULL DEFAULT 0,
        sample_rate_hz    INTEGER NOT NULL DEFAULT 0,
        channels          INTEGER NOT NULL DEFAULT 2,
        file_size_bytes   INTEGER NOT NULL DEFAULT 0,
        musicbrainz_id    TEXT,
        acoustid          TEXT,
        play_count        INTEGER NOT NULL DEFAULT 0,
        rating            INTEGER NOT NULL DEFAULT 0,
        comment           TEXT    NOT NULL DEFAULT '',
        lyrics            TEXT    NOT NULL DEFAULT '',
        created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS playlists (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        name              TEXT    NOT NULL,
        description       TEXT    NOT NULL DEFAULT '',
        is_smart          INTEGER NOT NULL DEFAULT 0,
        smart_query_json  TEXT    NOT NULL DEFAULT '{}',
        created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS playlist_entries (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
        track_id    INTEGER NOT NULL REFERENCES tracks(id)    ON DELETE CASCADE,
        position    INTEGER NOT NULL,
        added_at    TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE (playlist_id, position)
    );

    CREATE INDEX IF NOT EXISTS idx_tracks_album_id    ON tracks(album_id);
    CREATE INDEX IF NOT EXISTS idx_tracks_artist_id   ON tracks(artist_id);
    CREATE INDEX IF NOT EXISTS idx_tracks_file_path   ON tracks(file_path);
    CREATE INDEX IF NOT EXISTS idx_albums_artist_id   ON albums(artist_id);
    CREATE INDEX IF NOT EXISTS idx_playlist_entries_playlist ON playlist_entries(playlist_id);
    """,
]


class DatabaseConnection:
    """
    Gestiona la conexión SQLite y el ciclo de vida de las migraciones.

    Args:
        db_path: Ruta al archivo .db. Puede ser ":memory:" para tests.
    """

    def __init__(self, db_path: str = "audiorep.db") -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Abre la conexión y ejecuta las migraciones pendientes."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True) \
            if self._db_path != ":memory:" else None

        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,  # repositories corren en el hilo principal
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._run_migrations()
        logger.info("Base de datos conectada: %s", self._db_path)

    def close(self) -> None:
        """Cierra la conexión si está abierta."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Base de datos cerrada.")

    def __enter__(self) -> DatabaseConnection:
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Acceso a la conexión
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        """Retorna la conexión activa. Lanza RuntimeError si no está abierta."""
        if self._conn is None:
            raise RuntimeError(
                "La base de datos no está conectada. Llamar a connect() primero."
            )
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta una sentencia SQL y retorna el cursor."""
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params_seq)

    def commit(self) -> None:
        self.conn.commit()

    # ------------------------------------------------------------------
    # Migraciones
    # ------------------------------------------------------------------

    def _run_migrations(self) -> None:
        """Aplica las migraciones pendientes en orden."""
        self._conn.execute(  # type: ignore[union-attr]
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "  version    INTEGER PRIMARY KEY,"
            "  applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ");"
        )
        self._conn.commit()  # type: ignore[union-attr]

        row = self._conn.execute(  # type: ignore[union-attr]
            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
        ).fetchone()
        current_version: int = row[0]

        pending = _MIGRATIONS[current_version:]
        for i, migration_sql in enumerate(pending, start=current_version + 1):
            logger.info("Aplicando migración %04d…", i)
            self._conn.executescript(migration_sql)  # type: ignore[union-attr]
            self._conn.execute(  # type: ignore[union-attr]
                "INSERT INTO schema_version (version) VALUES (?)", (i,)
            )
            self._conn.commit()  # type: ignore[union-attr]
            logger.info("Migración %04d aplicada.", i)

        if pending:
            logger.info("%d migración(es) aplicada(s).", len(pending))
        else:
            logger.debug("Base de datos al día (versión %d).", current_version)
