"""Label — Entidad de dominio que representa un sello discográfico."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Label:
    """Sello discográfico. Almacena nombre y país de origen."""

    name:    str
    country: str           = ""   # Nombre del país/área (ej. "United States", "United Kingdom")
    id:      int | None    = None

    def __str__(self) -> str:
        return self.name
