"""
AudioRep — Clase base para repositories SQLite.

Proporciona acceso a la `DatabaseConnection` y helpers comunes
que evitan repetición en cada repository concreto.
"""
from __future__ import annotations

import sqlite3

from audiorep.infrastructure.database.connection import DatabaseConnection


class BaseRepository:
    """
    Clase base para todos los repositories SQLite de AudioRep.

    Args:
        db: Conexión activa a la base de datos.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Ejecuta una sentencia DML/DDL y retorna el cursor."""
        return self._db.execute(sql, params)

    def _fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Ejecuta un SELECT y retorna todas las filas."""
        return self._db.fetchall(sql, params)

    def _fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Ejecuta un SELECT y retorna la primera fila o None."""
        return self._db.fetchone(sql, params)

    def _commit(self) -> None:
        """Confirma la transacción activa."""
        self._db.commit()
