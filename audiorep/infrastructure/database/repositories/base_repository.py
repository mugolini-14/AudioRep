"""
Clase base para todos los repositories SQLite de AudioRep.

Provee:
    - Acceso directo a DatabaseConnection.
    - Helpers para ejecutar queries y mapear resultados.
    - Manejo centralizado de errores de BD.
"""
from __future__ import annotations

import sqlite3
import logging
from typing import TypeVar, Callable, Any

from audiorep.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository:
    """
    Repository base con acceso a DatabaseConnection.

    Subclases deben implementar `_row_to_entity` para el mapeo
    de sqlite3.Row al objeto de dominio correspondiente.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._db.execute(sql, params)

    def _fetch_one(
        self,
        sql: str,
        params: tuple,
        mapper: Callable[[sqlite3.Row], T],
    ) -> T | None:
        """Ejecuta una query y mapea la primera fila, o retorna None."""
        row = self._db.execute(sql, params).fetchone()
        return mapper(row) if row else None

    def _fetch_all(
        self,
        sql: str,
        params: tuple,
        mapper: Callable[[sqlite3.Row], T],
    ) -> list[T]:
        """Ejecuta una query y mapea todas las filas."""
        rows = self._db.execute(sql, params).fetchall()
        return [mapper(r) for r in rows]

    def _insert(self, sql: str, params: tuple) -> int:
        """Ejecuta un INSERT, hace commit y retorna el rowid."""
        cursor = self._db.execute(sql, params)
        self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def _update(self, sql: str, params: tuple) -> None:
        """Ejecuta un UPDATE y hace commit."""
        self._db.execute(sql, params)
        self._db.commit()

    def _delete(self, sql: str, params: tuple) -> None:
        """Ejecuta un DELETE y hace commit."""
        self._db.execute(sql, params)
        self._db.commit()

    @staticmethod
    def _like(query: str) -> str:
        """Envuelve un string para búsqueda LIKE insensible."""
        escaped = query.replace("%", r"\%").replace("_", r"\_")
        return f"%{escaped}%"
