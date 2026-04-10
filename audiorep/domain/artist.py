"""
Modelo de dominio: Artist.

Representa un artista o banda musical.
No tiene dependencias externas; es un dato puro.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Artist:
    """
    Artista o banda musical.

    Attributes:
        id:              Identificador interno en base de datos local (None si aún no persistido).
        name:            Nombre del artista / banda.
        sort_name:       Nombre para ordenar (ej. "Beatles, The").
        musicbrainz_id:  MBID del artista en MusicBrainz (puede ser None).
        biography:       Texto biográfico opcional.
        genres:          Lista de géneros asociados.
    """

    name: str
    id: int | None = None
    sort_name: str = ""
    musicbrainz_id: str | None = None
    biography: str = ""
    genres: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sort_name:
            # Valor por defecto: igual al nombre
            self.sort_name = self.name

    def display_name(self) -> str:
        """Nombre para mostrar en la interfaz."""
        return self.name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Artist(id={self.id!r}, name={self.name!r})"
