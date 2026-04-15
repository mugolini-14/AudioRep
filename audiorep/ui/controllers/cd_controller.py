"""
CDController — Bisagra entre CDPanel / CDMetadataPanel, CDService y RipperService.

Responsabilidades:
    - Conectar las señales de CDPanel con CDService y RipperService.
    - Conectar las señales de CDMetadataPanel con los providers de metadatos.
    - Escuchar app_events (cd_inserted, cd_identified, cd_ejected).
    - Actualizar CDPanel y CDMetadataPanel cuando cambia el estado del disco.
    - Pasar pistas del CD al PlayerService para reproducción.
    - Abrir RipperDialog y lanzar el ripeo cuando el usuario lo solicita.
    - Actualizar NowPlaying con la portada del CD al reproducir.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QFileDialog

from audiorep.core.events import app_events
from audiorep.domain.cd_disc import CDDisc, RipStatus
from audiorep.services.cd_service import CDService
from audiorep.services.player_service import PlayerService
from audiorep.services.ripper_service import RipperService
from audiorep.ui.widgets.cd_metadata_panel import CDMetadataPanel
from audiorep.ui.widgets.cd_panel import CDPanel
from audiorep.ui.widgets.now_playing import NowPlaying

logger = logging.getLogger(__name__)


class _LookupWorker(QThread):
    """Hilo de búsqueda para que la UI no se bloquee durante el request HTTP."""

    finished = pyqtSignal(list)   # list[dict]
    error    = pyqtSignal(str)

    def __init__(self, provider: object, disc: CDDisc, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._provider = provider
        self._disc = disc

    def run(self) -> None:
        try:
            results = self._provider.search_disc(self._disc)  # type: ignore[attr-defined]
            self.finished.emit(results)
        except Exception as exc:
            logger.exception("_LookupWorker: %s", exc)
            self.error.emit(str(exc))


class CDController:
    """
    Controller del CD.

    Args:
        cd_service:          Servicio de CD (detección, identificación).
        player_service:      Servicio de reproducción.
        cd_panel:            Widget del panel de CD.
        cd_metadata_panel:   Widget del panel de búsqueda manual de metadatos.
        now_playing:         Widget de información de pista actual.
        ripper_service:      Servicio de ripeo (opcional).
        settings:            Configuración persistente (para directorio de ripeo).
        cd_lookup_providers: Lista de ICDLookupProvider (MusicBrainz, GnuDB, …).
    """

    def __init__(
        self,
        cd_service:          CDService,
        player_service:      PlayerService,
        cd_panel:            CDPanel,
        cd_metadata_panel:   CDMetadataPanel,
        now_playing:         NowPlaying,
        ripper_service:      RipperService | None = None,
        settings:            object = None,
        cd_lookup_providers: list | None = None,
    ) -> None:
        self._cd_service    = cd_service
        self._player        = player_service
        self._panel         = cd_panel
        self._meta_panel    = cd_metadata_panel
        self._now_playing   = now_playing
        self._ripper        = ripper_service
        self._settings      = settings
        self._providers: dict[str, object] = {
            p.name: p for p in (cd_lookup_providers or [])  # type: ignore[attr-defined]
        }
        self._lookup_worker: _LookupWorker | None = None

        self._connect_panel()
        self._connect_meta_panel()
        self._connect_app_events()

        # Poblar selector de lectoras, selector de servicios y arrancar sondeo
        drives = self._cd_service.list_drives()
        self._panel.set_drives(drives)
        self._meta_panel.set_services(list(self._providers.keys()))
        self._meta_panel.set_disc_available(False)

        self._cd_service.start_polling()

        logger.debug("CDController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: CDPanel → CDService / PlayerService
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        panel = self._panel
        panel.detect_requested.connect(self._on_detect_requested)
        panel.identify_requested.connect(self._on_identify_requested)
        panel.play_cd_requested.connect(self._on_play_cd)
        panel.play_track_requested.connect(self._on_play_track)
        panel.rip_all_requested.connect(self._on_rip_all)
        panel.rip_track_requested.connect(self._on_rip_track)
        panel.drive_changed.connect(self._on_drive_changed)

    # ------------------------------------------------------------------
    # Conexiones: CDMetadataPanel
    # ------------------------------------------------------------------

    def _connect_meta_panel(self) -> None:
        self._meta_panel.search_requested.connect(self._on_meta_search)
        self._meta_panel.apply_requested.connect(self._on_meta_apply)

    # ------------------------------------------------------------------
    # Conexiones: app_events → CDPanel
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.cd_inserted.connect(self._on_cd_inserted)
        app_events.cd_identified.connect(self._on_cd_identified)
        app_events.cd_ejected.connect(self._on_cd_ejected)
        app_events.rip_progress.connect(self._on_rip_progress)
        app_events.rip_track_done.connect(self._on_rip_track_done)
        app_events.rip_track_error.connect(self._on_rip_track_error)

    # ------------------------------------------------------------------
    # Handlers: CDPanel
    # ------------------------------------------------------------------

    def _on_drive_changed(self, drive: str) -> None:
        self._cd_service.set_drive(drive)
        app_events.status_message.emit(f"Lectora seleccionada: {drive}")

    def _on_detect_requested(self) -> None:
        self._panel.show_reading()
        disc = self._cd_service.detect_cd()
        if disc:
            self._panel.show_disc(disc)
            self._meta_panel.set_disc_available(True)
        else:
            self._panel.show_no_cd()
            self._meta_panel.set_disc_available(False)
            app_events.status_message.emit("No se detectó ningún CD en la unidad.")

    def _on_identify_requested(self) -> None:
        self._cd_service.identify_current_disc()
        app_events.status_message.emit("Identificando disco en MusicBrainz …")

    def _on_play_cd(self) -> None:
        tracks = self._cd_service.get_tracks_as_domain()
        if not tracks:
            return
        self._player.set_queue(tracks, start_index=0)
        logger.info("Reproduciendo CD: %d pistas.", len(tracks))

    def _on_play_track(self, track_number: int) -> None:
        tracks = self._cd_service.get_tracks_as_domain()
        if not tracks:
            return
        start = next(
            (i for i, t in enumerate(tracks) if t.track_number == track_number),
            0,
        )
        self._player.set_queue(tracks, start_index=start)
        logger.info("Reproduciendo pista CD nro. %d.", track_number)

    def _on_rip_all(self) -> None:
        disc = self._cd_service.current_disc
        if not disc:
            app_events.status_message.emit("No hay ningún CD en la unidad.")
            return
        if self._ripper is None:
            app_events.status_message.emit("RipperService no disponible.")
            return
        output_dir = self._get_output_dir(disc)
        if not output_dir:
            return
        from audiorep.ui.dialogs.ripper_dialog import RipperDialog
        dialog = RipperDialog(ripper_service=self._ripper, disc=disc, parent=self._panel)
        dialog.show()
        fmt = "flac"
        if self._settings and hasattr(self._settings, "ripper_format"):
            fmt = self._settings.ripper_format  # type: ignore[union-attr]
        self._ripper.rip_all(disc=disc, output_dir=output_dir, fmt=fmt)

    def _on_rip_track(self, track_number: int) -> None:
        disc = self._cd_service.current_disc
        if not disc:
            return
        if self._ripper is None:
            app_events.status_message.emit("RipperService no disponible.")
            return
        output_dir = self._get_output_dir(disc)
        if not output_dir:
            return
        from audiorep.ui.dialogs.ripper_dialog import RipperDialog
        dialog = RipperDialog(ripper_service=self._ripper, disc=disc, parent=self._panel)
        dialog.show()
        fmt = "flac"
        if self._settings and hasattr(self._settings, "ripper_format"):
            fmt = self._settings.ripper_format  # type: ignore[union-attr]
        self._ripper.rip_track(disc=disc, track_number=track_number, output_dir=output_dir, fmt=fmt)

    # ------------------------------------------------------------------
    # Handlers: CDMetadataPanel
    # ------------------------------------------------------------------

    def _on_meta_search(self, service_name: str) -> None:
        """El usuario presionó 'Buscar' en el panel de metadatos."""
        disc = self._cd_service.current_disc
        if not disc:
            self._meta_panel.show_error("No hay ningún CD detectado.")
            return

        provider = self._providers.get(service_name)
        if provider is None:
            self._meta_panel.show_error(f"Servicio '{service_name}' no disponible.")
            return

        # Cancelar búsqueda anterior si está en curso
        if self._lookup_worker and self._lookup_worker.isRunning():
            self._lookup_worker.quit()
            self._lookup_worker.wait(2000)

        self._lookup_worker = _LookupWorker(
            provider=provider, disc=disc, parent=None
        )
        self._lookup_worker.finished.connect(self._on_meta_results)
        self._lookup_worker.error.connect(self._on_meta_error)
        self._lookup_worker.start()
        app_events.status_message.emit(
            f"Buscando en {service_name} … (disc_id: {disc.disc_id[:8]}…)"
        )

    def _on_meta_results(self, results: list) -> None:
        self._meta_panel.show_results(results)
        count = len(results)
        app_events.status_message.emit(
            f"Búsqueda completada: {count} resultado{'s' if count != 1 else ''}."
        )

    def _on_meta_error(self, message: str) -> None:
        self._meta_panel.show_error(message)
        app_events.status_message.emit(f"Error en la búsqueda: {message}")

    def _on_meta_apply(self, result: dict) -> None:
        """El usuario eligió un resultado y presionó 'Aplicar al disco'."""
        disc = self._cd_service.current_disc
        if not disc:
            return

        # Aplicar metadatos al CDDisc actual
        disc.album_title    = result.get("album", disc.album_title) or disc.album_title
        disc.artist_name    = result.get("artist", disc.artist_name) or disc.artist_name
        disc.genre          = result.get("genre", disc.genre) or disc.genre
        year_str = result.get("year", "")
        if year_str:
            try:
                disc.year = int(year_str)
            except (ValueError, TypeError):
                pass

        # Actualizar pistas
        track_by_number = {t.number: t for t in disc.tracks}
        for mt in result.get("tracks", []):
            num = mt.get("number")
            cd_track = track_by_number.get(num)
            if cd_track and mt.get("title"):
                cd_track.title = mt["title"]

        # Refrescar el panel principal
        self._panel.show_identified(disc)
        app_events.status_message.emit(
            f"Metadatos aplicados: {disc.artist_name} — {disc.album_title}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_output_dir(self, disc: CDDisc) -> str:
        if self._settings and hasattr(self._settings, "ripper_output_dir"):
            saved = self._settings.ripper_output_dir  # type: ignore[union-attr]
            if saved and Path(saved).is_dir():
                album  = disc.album_title or "CD"
                artist = disc.artist_name or "Desconocido"
                return str(Path(saved) / artist / album)
        folder = QFileDialog.getExistingDirectory(
            self._panel,
            "Seleccioná la carpeta de destino para el ripeo",
        )
        if not folder:
            return ""
        album  = disc.album_title or "CD"
        artist = disc.artist_name or "Desconocido"
        return str(Path(folder) / artist / album)

    # ------------------------------------------------------------------
    # Handlers: app_events
    # ------------------------------------------------------------------

    def _on_cd_inserted(self, disc_id: str) -> None:
        disc = self._cd_service.current_disc
        if disc:
            self._panel.show_disc(disc)
            self._meta_panel.set_disc_available(True)
        app_events.status_message.emit(f"CD detectado (ID: {disc_id[:8]}…) — Identificando …")

    def _on_cd_identified(self, disc: CDDisc) -> None:
        self._panel.show_identified(disc)
        if disc.cover_data:
            self._panel.update_cover(disc.cover_data)
            self._now_playing.update_cover(disc.cover_data)

    def _on_cd_ejected(self) -> None:
        self._panel.show_no_cd()
        self._meta_panel.set_disc_available(False)
        app_events.status_message.emit("CD retirado de la unidad.")

    def _on_rip_progress(self, track_current: int, total: int, percent: int) -> None:
        app_events.status_message.emit(
            f"Ripeando pista {track_current}/{total} … {percent}%"
        )

    def _on_rip_track_done(self, track_number: int, path: str) -> None:
        self._panel.update_track_rip_status(track_number, RipStatus.DONE)

    def _on_rip_track_error(self, track_number: int, message: str) -> None:
        self._panel.update_track_rip_status(track_number, RipStatus.ERROR)
        logger.error("Error ripeando pista %d: %s", track_number, message)
