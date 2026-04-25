"""
LibraryController — Bisagra entre LibraryPanel y LibraryService / PlayerService.

Responsabilidades:
    - Conectar señales de LibraryPanel con LibraryService y PlayerService.
    - Conectar señales stats_requested y export_requested con StatsService y ExportService.
    - Escuchar app_events (library_updated, scan_*).
    - Refrescar la tabla de pistas cuando la biblioteca cambia.
"""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from audiorep.core.events import app_events
from audiorep.domain.track import Track
from audiorep.services.export_service import ExportService
from audiorep.services.library_service import LibraryService
from audiorep.services.player_service import PlayerService
from audiorep.services.stats_service import LibraryStats, StatsService, compute_stats
from audiorep.ui.widgets.library_panel import LibraryPanel

logger = logging.getLogger(__name__)


class LibraryController:
    """
    Controller de la biblioteca.

    Args:
        library_service: Servicio de biblioteca.
        player_service:  Servicio de reproducción.
        library_panel:   Widget del panel de biblioteca.
        stats_service:   Servicio de estadísticas.
        export_service:  Servicio de exportación.
    """

    def __init__(
        self,
        library_service: LibraryService,
        player_service:  PlayerService,
        library_panel:   LibraryPanel,
        stats_service:   StatsService,
        export_service:  ExportService,
    ) -> None:
        self._library        = library_service
        self._player         = player_service
        self._panel          = library_panel
        self._stats_service  = stats_service
        self._export_service = export_service
        self._last_stats:  LibraryStats | None = None

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
        panel.stats_requested.connect(self._on_stats_requested)
        panel.export_requested.connect(self._on_export_requested)

        self._stats_service.stats_ready.connect(self._on_stats_ready)

    # ------------------------------------------------------------------
    # Conexiones: app_events
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.library_updated.connect(self._on_library_updated)
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

    def _on_stats_requested(self) -> None:
        tracks = self._library.get_all_tracks()
        self._stats_service.compute(tracks)
        app_events.status_message.emit("Calculando estadísticas…")

    def _on_stats_ready(self, stats: LibraryStats) -> None:
        self._last_stats = stats
        self._panel.set_stats(stats)
        app_events.status_message.emit("Estadísticas listas.")

    def _on_export_requested(self) -> None:
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self._panel,
            "Exportar biblioteca",
            "biblioteca",
            "Excel (*.xlsx);;PDF (*.pdf);;CSV (*.csv)",
        )
        if not filepath:
            return

        tracks = self._library.get_all_tracks()

        try:
            if filepath.lower().endswith(".xlsx"):
                stats = self._get_or_compute_stats(tracks)
                self._export_service.export_xlsx(tracks, stats, filepath)
            elif filepath.lower().endswith(".pdf"):
                stats = self._get_or_compute_stats(tracks)
                self._export_service.export_pdf(tracks, stats, filepath)
            else:
                # CSV — agrega extensión si no la tiene
                if not filepath.lower().endswith(".csv"):
                    filepath += ".csv"
                self._export_service.export_csv(tracks, filepath)
                self._show_csv_note()

            app_events.status_message.emit(f"Exportación completada: {filepath}")
            logger.info("Biblioteca exportada a: %s", filepath)

        except Exception as exc:
            logger.exception("Error al exportar: %s", exc)
            app_events.status_message.emit(f"Error al exportar: {exc}")
            QMessageBox.critical(
                self._panel,
                "Error de exportación",
                f"No se pudo exportar la biblioteca:\n{exc}",
            )

    def _get_or_compute_stats(self, tracks: list[Track]) -> LibraryStats:
        """Devuelve estadísticas cacheadas o las calcula sincrónicamente."""
        if self._last_stats is not None:
            return self._last_stats
        stats = compute_stats(tracks)
        self._last_stats = stats
        return stats

    def _show_csv_note(self) -> None:
        msg = QMessageBox(self._panel)
        msg.setWindowTitle("Exportación CSV")
        msg.setText(
            "El archivo CSV contiene solo los datos de la biblioteca.\n"
            "Para incluir estadísticas, exportá en formato Excel (.xlsx) o PDF."
        )
        msg.setIcon(QMessageBox.Icon.Information)
        msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

    def _refresh(self) -> None:
        tracks = self._library.get_all_tracks()
        self._panel.set_tracks(tracks)

    def _on_library_updated(self) -> None:
        self._last_stats = None   # invalidar caché de stats
        self._refresh()
