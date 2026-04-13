"""
SearchService — Búsqueda en la biblioteca musical.

Delega en LibraryService y aplica filtros adicionales si se necesitan.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject

from audiorep.domain.track import Track
from audiorep.services.library_service import LibraryService

logger = logging.getLogger(__name__)


class SearchService(QObject):
    """
    Servicio de búsqueda.

    Args:
        library_service: Servicio de biblioteca para acceder a los datos.
    """

    def __init__(
        self,
        library_service: LibraryService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._library = library_service

    def search(self, query: str) -> list[Track]:
        """Busca pistas por título, artista o álbum."""
        query = query.strip()
        if not query:
            return []
        return self._library.search_tracks(query)
