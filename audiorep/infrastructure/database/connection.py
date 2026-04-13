"""
AudioRep — Conexión a la base de datos SQLite.

La clase `DatabaseConnection` gestiona la conexión y el esquema.
Las migraciones son secuenciales y se rastrean con PRAGMA user_version.

Uso:
    db = DatabaseConnection("data/audiorep.db")
    db.connect()
    # ... usar db en repositories ...
    db.close()
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Envuelve una conexión SQLite y gestiona las migraciones de esquema.

    Attributes:
        _path:  Ruta al archivo de la base de datos.
        _conn:  Conexión sqlite3 activa (None hasta que se llame connect()).
    """

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Abre la conexión y ejecuta las migraciones pendientes."""
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        try:
            self._migrate()
        except sqlite3.DatabaseError as exc:
            # La BD está corrupta (disk I/O error, file is not a database, etc.).
            # Se renombra como .bak y se crea una BD nueva desde cero.
            logger.error("BD corrupta (%s) — se crea una nueva. Archivo original: %s.bak", exc, self._path)
            self._conn.close()
            db_path = Path(self._path)
            bak_path = db_path.with_suffix(".db.bak")
            try:
                if bak_path.exists():
                    bak_path.unlink()
                db_path.rename(bak_path)
            except OSError as rename_exc:
                logger.warning("No se pudo renombrar la BD corrupta: %s", rename_exc)
            # Reconectar con archivo limpio
            self._conn = sqlite3.connect(self._path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._migrate()
        logger.info("DatabaseConnection: conectado a %s", self._path)

    def close(self) -> None:
        """Cierra la conexión de forma segura."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("DatabaseConnection: conexión cerrada.")

    # ------------------------------------------------------------------
    # Acceso público
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        """Retorna la conexión activa. Lanza RuntimeError si no está abierta."""
        if self._conn is None:
            raise RuntimeError("DatabaseConnection: no hay conexión activa. Llame connect() primero.")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta una sentencia SQL y retorna el cursor."""
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params_seq: list[tuple]) -> sqlite3.Cursor:
        """Ejecuta una sentencia SQL para múltiples filas."""
        return self.conn.executemany(sql, params_seq)

    def commit(self) -> None:
        """Confirma la transacción actual."""
        self.conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Ejecuta una consulta SELECT y retorna todas las filas."""
        return self.conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Ejecuta una consulta SELECT y retorna la primera fila o None."""
        return self.conn.execute(sql, params).fetchone()

    # ------------------------------------------------------------------
    # Migraciones
    # ------------------------------------------------------------------

    def _migrate(self) -> None:
        """Aplica todas las migraciones pendientes de forma secuencial."""
        assert self._conn is not None

        version: int = self._conn.execute("PRAGMA user_version").fetchone()[0]
        logger.debug("DatabaseConnection: user_version actual = %d", version)

        if version < 1:
            self._migrate_v1()
            self._conn.execute("PRAGMA user_version = 1")
            self._conn.commit()
            logger.info("Migración v1 aplicada.")

        if version < 2:
            self._migrate_v2()
            self._conn.execute("PRAGMA user_version = 2")
            self._conn.commit()
            logger.info("Migración v2 aplicada (radio_stations).")

        # Reparación de esquema: agrega columnas que pueden faltar en bases de
        # datos creadas antes de que se agregaran al esquema original.
        self._repair_schema()

    def _repair_schema(self) -> None:
        """
        Agrega columnas faltantes a tablas existentes.
        Usa ALTER TABLE ... ADD COLUMN con try/except porque SQLite lanza
        OperationalError si la columna ya existe.
        """
        assert self._conn is not None
        repairs = [
            ("playlists", "is_smart",    "INTEGER NOT NULL DEFAULT 0"),
            ("playlists", "smart_query", "TEXT    NOT NULL DEFAULT '{}'"),
        ]
        for table, column, definition in repairs:
            try:
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )
                self._conn.commit()
                logger.info("Columna añadida: %s.%s", table, column)
            except Exception:
                pass  # La columna ya existe

    def _migrate_v1(self) -> None:
        """
        Esquema inicial: artists, albums, tracks, playlists, playlist_entries.
        """
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS artists (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                sort_name     TEXT    NOT NULL DEFAULT '',
                musicbrainz_id TEXT   DEFAULT NULL,
                genres        TEXT    NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS albums (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT    NOT NULL,
                artist_id     INTEGER REFERENCES artists(id) ON DELETE SET NULL,
                artist_name   TEXT    NOT NULL DEFAULT '',
                year          INTEGER DEFAULT NULL,
                release_date  TEXT    DEFAULT NULL,
                genre         TEXT    NOT NULL DEFAULT '',
                label         TEXT    NOT NULL DEFAULT '',
                musicbrainz_id TEXT   DEFAULT NULL,
                cover_path    TEXT    DEFAULT NULL,
                total_tracks  INTEGER NOT NULL DEFAULT 0,
                total_discs   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tracks (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT    NOT NULL,
                artist_name   TEXT    NOT NULL DEFAULT '',
                album_title   TEXT    NOT NULL DEFAULT '',
                album_id      INTEGER REFERENCES albums(id) ON DELETE SET NULL,
                artist_id     INTEGER REFERENCES artists(id) ON DELETE SET NULL,
                track_number  INTEGER NOT NULL DEFAULT 0,
                disc_number   INTEGER NOT NULL DEFAULT 1,
                duration_ms   INTEGER NOT NULL DEFAULT 0,
                year          INTEGER DEFAULT NULL,
                genre         TEXT    NOT NULL DEFAULT '',
                file_path     TEXT    DEFAULT NULL,
                format        TEXT    NOT NULL DEFAULT 'UNKNOWN',
                source        TEXT    NOT NULL DEFAULT 'LOCAL',
                bitrate_kbps  INTEGER NOT NULL DEFAULT 0,
                musicbrainz_id TEXT   DEFAULT NULL,
                acoustid      TEXT    DEFAULT NULL,
                play_count    INTEGER NOT NULL DEFAULT 0,
                rating        INTEGER NOT NULL DEFAULT 0,
                added_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                is_smart      INTEGER NOT NULL DEFAULT 0,
                smart_query   TEXT    NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS playlist_entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id   INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                track_id      INTEGER NOT NULL REFERENCES tracks(id)    ON DELETE CASCADE,
                position      INTEGER NOT NULL DEFAULT 0,
                added_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE (playlist_id, track_id)
            );

            CREATE INDEX IF NOT EXISTS idx_tracks_artist  ON tracks(artist_id);
            CREATE INDEX IF NOT EXISTS idx_tracks_album   ON tracks(album_id);
            CREATE INDEX IF NOT EXISTS idx_tracks_path    ON tracks(file_path);
            CREATE INDEX IF NOT EXISTS idx_albums_artist  ON albums(artist_id);
        """)

    def _migrate_v2(self) -> None:
        """
        Migración 2: tabla radio_stations para emisoras de radio por internet.
        """
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS radio_stations (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT    NOT NULL,
                stream_url        TEXT    NOT NULL,
                country           TEXT    NOT NULL DEFAULT '',
                genre             TEXT    NOT NULL DEFAULT '',
                logo_url          TEXT    NOT NULL DEFAULT '',
                is_favorite       INTEGER NOT NULL DEFAULT 0,
                added_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                bitrate_kbps      INTEGER NOT NULL DEFAULT 0,
                radio_browser_id  TEXT    NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_radio_favorite ON radio_stations(is_favorite);
        """)
