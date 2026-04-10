"""
Modelo de dominio: Playlist.

Representa una lista de reproducción creada por el usuario.
Contiene referencias a Track por ID para evitar duplicar datos.
No tiene dependencias externas; es un dato puro.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PlaylistEntry:
    """
    Entrada individual en una playlist.

    Attributes:
        track_id:   ID del Track en la biblioteca local.
        position:   Posición (orden) dentro de la playlist (base 1).
        added_at:   Fecha/hora en que se agregó la pista a la playlist.
    """
    track_id: int
    position: int
    added_at: datetime = field(default_factory=datetime.now)


@dataclass
class Playlist:
    """
    Lista de reproducción definida por el usuario.

    Attributes:
        id:          Identificador interno en base de datos local.
        name:        Nombre de la playlist.
        description: Descripción opcional.
        entries:     Entradas ordenadas de la playlist.
        created_at:  Fecha de creación.
        updated_at:  Última modificación.
        is_smart:    Si es True, la playlist se genera automáticamente
                     según criterios (futuro: smart playlists).
        smart_query: Consulta que define la smart playlist (JSON serializable).
    """

    name: str
    id: int | None = None
    description: str = ""
    entries: list[PlaylistEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_smart: bool = False
    smart_query: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Propiedades calculadas
    # ------------------------------------------------------------------

    @property
    def track_count(self) -> int:
        """Cantidad de pistas en la playlist."""
        return len(self.entries)

    @property
    def track_ids(self) -> list[int]:
        """Lista ordenada de IDs de pistas."""
        return [e.track_id for e in sorted(self.entries, key=lambda e: e.position)]

    # ------------------------------------------------------------------
    # Mutaciones
    # ------------------------------------------------------------------

    def add_track(self, track_id: int) -> None:
        """Agrega una pista al final de la playlist."""
        next_position = (max((e.position for e in self.entries), default=0)) + 1
        self.entries.append(PlaylistEntry(track_id=track_id, position=next_position))
        self.updated_at = datetime.now()

    def remove_track_at(self, position: int) -> None:
        """Elimina la pista en la posición indicada y reordena."""
        self.entries = [e for e in self.entries if e.position != position]
        # Reindexar posiciones
        for i, entry in enumerate(sorted(self.entries, key=lambda e: e.position), start=1):
            entry.position = i
        self.updated_at = datetime.now()

    def move_track(self, from_position: int, to_position: int) -> None:
        """Mueve una entrada de una posición a otra."""
        entry_map = {e.position: e for e in self.entries}
        if from_position not in entry_map or to_position not in entry_map:
            return
        entry_map[from_position].position = to_position
        entry_map[to_position].position = from_position
        self.updated_at = datetime.now()

    def clear(self) -> None:
        """Vacía la playlist."""
        self.entries.clear()
        self.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return self.track_count

    def __str__(self) -> str:
        return f"{self.name} ({self.track_count} pistas)"

    def __repr__(self) -> str:
        return f"Playlist(id={self.id!r}, name={self.name!r}, tracks={self.track_count})"
