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
from audiorep.services.enrichment_service import EnrichmentService
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
        library_service:    LibraryService,
        player_service:     PlayerService,
        library_panel:      LibraryPanel,
        stats_service:      StatsService,
        export_service:     ExportService,
        enrichment_service: EnrichmentService | None = None,
    ) -> None:
        self._library            = library_service
        self._player             = player_service
        self._panel              = library_panel
        self._stats_service      = stats_service
        self._export_service     = export_service
        self._enrichment_service = enrichment_service
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
        panel.export_library_requested.connect(self._on_export_library_requested)
        panel.export_stats_requested.connect(self._on_export_stats_requested)

        self._stats_service.stats_ready.connect(self._on_stats_ready)

    # ------------------------------------------------------------------
    # Conexiones: app_events
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.library_updated.connect(self._on_library_updated)
        app_events.scan_started.connect(
            lambda path: app_events.status_message.emit(f"Escaneando: {path} …")
        )
        app_events.scan_finished.connect(self._on_scan_finished)
        app_events.scan_progress.connect(
            lambda p, t: self._panel.set_scan_progress(p, t)
        )
        app_events.cd_identified.connect(self._on_cd_identified)
        app_events.enrichment_requested.connect(self._start_enrichment)
        app_events.enrichment_progress.connect(self._on_enrichment_progress)
        app_events.enrichment_finished.connect(self._on_enrichment_finished)
        app_events.enrichment_cancelled.connect(
            lambda: app_events.status_message.emit("Actualización de metadatos cancelada.")
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
        tracks            = self._library.get_all_tracks()
        albums            = self._library.get_all_albums()
        artists           = self._library.get_all_artists()
        label_country_map = self._library.get_label_country_map()
        self._stats_service.compute(tracks, albums, artists, label_country_map)
        app_events.status_message.emit("Calculando estadísticas…")

    def _on_stats_ready(self, stats: LibraryStats) -> None:
        self._last_stats = stats
        self._panel.set_stats(stats)
        app_events.status_message.emit("Estadísticas listas.")

    def _on_export_library_requested(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
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
                self._export_service.export_library_xlsx(tracks, filepath)
            elif filepath.lower().endswith(".pdf"):
                stats = self._get_or_compute_stats(tracks)
                self._export_service.export_library_pdf(tracks, stats, filepath)
            else:
                if not filepath.lower().endswith(".csv"):
                    filepath += ".csv"
                self._export_service.export_csv(tracks, filepath)
            app_events.status_message.emit(f"Exportación completada: {filepath}")
            logger.info("Biblioteca exportada a: %s", filepath)
        except Exception as exc:
            logger.exception("Error al exportar biblioteca: %s", exc)
            app_events.status_message.emit(f"Error al exportar: {exc}")
            QMessageBox.critical(self._panel, "Error de exportación",
                                 f"No se pudo exportar la biblioteca:\n{exc}")

    def _on_export_stats_requested(self) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self._panel,
            "Exportar estadísticas",
            "estadisticas",
            "Excel (*.xlsx);;PDF (*.pdf);;CSV (*.csv)",
        )
        if not filepath:
            return
        tracks = self._library.get_all_tracks()
        stats  = self._get_or_compute_stats(tracks)
        try:
            if filepath.lower().endswith(".xlsx"):
                self._export_service.export_stats_xlsx(stats, filepath)
            elif filepath.lower().endswith(".pdf"):
                self._export_service.export_stats_pdf(stats, filepath)
            else:
                if not filepath.lower().endswith(".csv"):
                    filepath += ".csv"
                self._export_service.export_stats_csv(stats, filepath)
            app_events.status_message.emit(f"Exportación completada: {filepath}")
            logger.info("Estadísticas exportadas a: %s", filepath)
        except Exception as exc:
            logger.exception("Error al exportar estadísticas: %s", exc)
            app_events.status_message.emit(f"Error al exportar: {exc}")
            QMessageBox.critical(self._panel, "Error de exportación",
                                 f"No se pudo exportar las estadísticas:\n{exc}")

    def _on_scan_finished(self, n: int) -> None:
        app_events.status_message.emit(f"Importación completada: {n} pistas.")
        self._start_enrichment()

    def _start_enrichment(self) -> None:
        if self._enrichment_service:
            self._enrichment_service.start()
            app_events.status_message.emit("Actualizando metadatos en segundo plano…")

    def _on_enrichment_progress(self, current: int, total: int) -> None:
        app_events.status_message.emit(
            f"Actualizando metadatos: {current}/{total} pistas…"
        )

    def _on_enrichment_finished(self, updated: int) -> None:
        msg = (
            f"Metadatos actualizados: {updated} pistas modificadas."
            if updated > 0
            else "Actualización de metadatos completada. Sin cambios."
        )
        app_events.status_message.emit(msg)

    def _on_cd_identified(self, disc: object) -> None:
        """Enriquece la biblioteca con los metadatos del disco identificado."""
        try:
            from audiorep.domain.cd_disc import CDDisc
            if not isinstance(disc, CDDisc):
                return
            disc_data = {
                "album":          disc.album_title,
                "artist":         disc.artist_name,
                "artist_country": disc.artist_country,
                "label":          disc.label,
                "label_country":  disc.label_country,
                "release_type":   disc.release_type,
            }
            self._library.enrich_from_cd_disc(disc_data)
        except Exception as exc:
            logger.debug("enrich_from_cd_disc: %s", exc)

    def _get_or_compute_stats(self, tracks: list[Track]) -> LibraryStats:
        """Devuelve estadísticas cacheadas o las calcula sincrónicamente."""
        if self._last_stats is not None:
            return self._last_stats
        albums            = self._library.get_all_albums()
        artists           = self._library.get_all_artists()
        label_country_map = self._library.get_label_country_map()
        stats = compute_stats(tracks, albums, artists, label_country_map)
        self._last_stats = stats
        return stats

    def _refresh(self) -> None:
        tracks = self._library.get_all_tracks()
        self._panel.set_tracks(tracks)

    def _on_library_updated(self) -> None:
        had_stats = self._last_stats is not None
        self._last_stats = None   # invalidar caché de stats
        self._refresh()
        if had_stats:
            self._on_stats_requested()
