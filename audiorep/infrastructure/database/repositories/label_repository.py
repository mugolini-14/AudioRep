"""LabelRepository — Implementa ILabelRepository usando SQLite."""
from __future__ import annotations

import logging

from audiorep.domain.label import Label
from audiorep.infrastructure.database.connection import DatabaseConnection
from audiorep.infrastructure.database.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class LabelRepository(BaseRepository):
    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__(db)

    def get_by_id(self, label_id: int) -> Label | None:
        row = self._fetchone("SELECT * FROM labels WHERE id = ?", (label_id,))
        return self._row_to_label(row) if row else None

    def get_by_name(self, name: str) -> Label | None:
        row = self._fetchone("SELECT * FROM labels WHERE name = ?", (name,))
        return self._row_to_label(row) if row else None

    def get_all(self) -> list[Label]:
        rows = self._fetchall("SELECT * FROM labels ORDER BY name ASC")
        return [self._row_to_label(r) for r in rows]

    def save(self, label: Label) -> Label:
        if label.id is None:
            return self._insert(label)
        return self._update(label)

    def delete(self, label_id: int) -> None:
        self._execute("DELETE FROM labels WHERE id = ?", (label_id,))
        self._commit()

    def upsert_country(self, name: str, country: str) -> None:
        """Inserta el sello si no existe, o actualiza su país si estaba vacío."""
        if not name or not country:
            return
        existing = self.get_by_name(name)
        if existing is None:
            self._insert(Label(name=name, country=country))
        elif not existing.country:
            self._execute(
                "UPDATE labels SET country=? WHERE name=?",
                (country, name),
            )
            self._commit()

    def get_country_map(self) -> dict[str, str]:
        """Retorna {nombre_sello: país} para todos los sellos con país conocido."""
        rows = self._fetchall(
            "SELECT name, country FROM labels WHERE country != '' ORDER BY name ASC"
        )
        return {r["name"]: r["country"] for r in rows}

    def _insert(self, label: Label) -> Label:
        try:
            cur = self._execute(
                "INSERT INTO labels (name, country) VALUES (?, ?)",
                (label.name, label.country),
            )
            self._commit()
            return Label(id=cur.lastrowid, name=label.name, country=label.country)
        except Exception:
            # Unique constraint violation — ignorar
            existing = self.get_by_name(label.name)
            return existing or label

    def _update(self, label: Label) -> Label:
        self._execute(
            "UPDATE labels SET name=?, country=? WHERE id=?",
            (label.name, label.country, label.id),
        )
        self._commit()
        return label

    @staticmethod
    def _row_to_label(row) -> Label:
        return Label(id=row["id"], name=row["name"], country=row["country"] or "")
