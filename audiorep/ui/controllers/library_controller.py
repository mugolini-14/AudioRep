"""
LibraryController — Bisagra entre LibraryPanel y LibraryService / PlayerService.

Responsabilidades:
    - Conectar señales de LibraryPanel con LibraryService y PlayerService.
    - Escuchar app_events (library_updated, scan_*).
    - Refrescar la tabla de pistas cuando la biblioteca cambia.
"""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QFileDialog

from audiorep.core.events import app_events
from audiorep.domain.track import Track
from audiorep.services.library_service import LibraryService
from audiorep.services.player_service import PlayerService
from audiorep.ui.widgets.library_panel import LibraryPanel

logger = logging.getLogger(__name__)


class LibraryController:
    """
    Controller de la biblioteca.

    Args:
        library_service: Servicio de biblioteca.
        player_service:  Servicio de reproducción.
        library_panel:   Widget del panel de biblioteca.
    """

    def __init__(
        self,
        library_service: LibraryService,
        player_service:  PlayerService,
        library_panel:   LibraryPanel,
    ) -> None:
        self._library = library_service
        self._player  = player_service
        self._panel   = library_panel

        self._connect_panel()
        self._connect_app_events()
        self._refresh()

        logger.debug("LibraryController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: LibraryPanel → services
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        panel = self._panel
        panel.import_requested.connect(self._on_import_requested)
        panel.play_requested.connect(self._on_play_requested)
        panel.search_changed.connect(self._on_search_changed)

    # ------------------------------------------------------------------
    # Conexiones: app_events
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.library_updated.connect(self._refresh)
        app_events.scan_started.connect(
            lambda path: app_events.status_message.emit(f"Escaneando: {path} …")
        )
        app_events.scan_finished.connect(
            lambda n: app_events.status_message.emit(f"Importación completada: {n} pistas.")
        )
        app_events.scan_progress.connect(
            lambda p, t: self._panel.set_scan_progress(p, t)
        )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_import_requested(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self._panel,
            "Seleccioná la carpeta de música",
        )
        if folder:
            self._library.import_directory(folder)

    def _on_play_requested(self, tracks: list[Track], start_index: int) -> None:
        self._player.set_queue(tracks, start_index=start_index)

    def _on_search_changed(self, query: str) -> None:
        if query.strip():
            tracks = self._library.search_tracks(query)
        else:
            tracks = self._library.get_all_tracks()
        self._panel.set_tracks(tracks)

    def _refresh(self) -> None:
        tracks = self._library.get_all_tracks()
        self._panel.set_tracks(tracks)
