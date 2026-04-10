"""
Modelo de dominio: Album.

Representa un álbum o lanzamiento musical.
No tiene dependencias externas; es un dato puro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Album:
    """
    Álbum o lanzamiento musical.

    Attributes:
        id:              Identificador interno en base de datos local.
        title:           Título del álbum.
        artist_id:       FK al Artist principal.
        artist_name:     Nombre desnormalizado del artista (para mostrar sin JOIN).
        year:            Año de lanzamiento.
        release_date:    Fecha exacta de lanzamiento (opcional).
        genre:           Género principal.
        genres:          Lista completa de géneros.
        label:           Sello discográfico.
        catalog_number:  Número de catálogo del sello.
        musicbrainz_id:  MBID del release en MusicBrainz.
        cover_path:      Ruta local a la imagen de portada (None si no descargada).
        cover_url:       URL remota de la portada (None si desconocida).
        total_tracks:    Total de pistas del álbum.
        total_discs:     Total de discos (p.ej. 2 en un álbum doble).
        comment:         Notas adicionales.
    """

    title: str
    id: int | None = None
    artist_id: int | None = None
    artist_name: str = ""
    year: int | None = None
    release_date: date | None = None
    genre: str = ""
    genres: list[str] = field(default_factory=list)
    label: str = ""
    catalog_number: str = ""
    musicbrainz_id: str | None = None
    cover_path: str | None = None
    cover_url: str | None = None
    total_tracks: int = 0
    total_discs: int = 1
    comment: str = ""

    def has_cover(self) -> bool:
        """Indica si hay portada disponible localmente."""
        return self.cover_path is not None

    def display_title(self) -> str:
        """Título para mostrar, con año si está disponible."""
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    def __str__(self) -> str:
        return self.display_title()

    def __repr__(self) -> str:
        return f"Album(id={self.id!r}, title={self.title!r}, artist={self.artist_name!r})"
