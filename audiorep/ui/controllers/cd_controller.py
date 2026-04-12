"""
CDController — Bisagra entre CDPanel y CDService / RipperService.

Responsabilidades:
    - Conectar las señales de CDPanel con CDService y RipperService.
    - Escuchar app_events (cd_inserted, cd_identified, cd_ejected).
    - Actualizar CDPanel cuando cambia el estado del disco.
    - Pasar pistas del CD al PlayerService para reproducción.
    - Abrir RipperDialog y lanzar el ripeo cuando el usuario lo solicita.
    - Actualizar NowPlaying con la portada del CD al reproducir.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from audiorep.core.events import app_events
from audiorep.domain.cd_disc import CDDisc, RipStatus
from audiorep.services.cd_service import CDService
from audiorep.services.player_service import PlayerService
from audiorep.services.ripper_service import RipperService
from audiorep.ui.widgets.cd_panel import CDPanel
from audiorep.ui.widgets.now_playing import NowPlaying

logger = logging.getLogger(__name__)


class CDController:
    """
    Controller del CD.

    Args:
        cd_service:     Servicio de CD (detección, identificación).
        player_service: Servicio de reproducción.
        cd_panel:       Widget del panel de CD.
        now_playing:    Widget de información de pista actual.
        ripper_service: Servicio de ripeo (opcional).
        settings:       Configuración persistente (para directorio de ripeo).
    """

    def __init__(
        self,
        cd_service:     CDService,
        player_service: PlayerService,
        cd_panel:       CDPanel,
        now_playing:    NowPlaying,
        ripper_service: RipperService | None = None,
        settings:       object = None,
    ) -> None:
        self._cd_service    = cd_service
        self._player        = player_service
        self._panel         = cd_panel
        self._now_playing   = now_playing
        self._ripper        = ripper_service
        self._settings      = settings

        self._connect_panel()
        self._connect_app_events()
        self._connect_cd_service()

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

    def _connect_cd_service(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Handlers: CDPanel
    # ------------------------------------------------------------------

    def _on_detect_requested(self) -> None:
        self._panel.show_reading()
        disc = self._cd_service.detect_cd()
        if disc:
            self._panel.show_disc(disc)
        else:
            self._panel.show_no_cd()
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
        """Ripear todas las pistas del disco."""
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
        """Ripear una pista individual del disco."""
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
    # Helpers
    # ------------------------------------------------------------------

    def _get_output_dir(self, disc: CDDisc) -> str:
        """
        Determina el directorio de salida para el ripeo.
        Si está configurado en settings, lo usa directamente.
        Si no, abre un diálogo de selección de carpeta.
        """
        if self._settings and hasattr(self._settings, "ripper_output_dir"):
            saved = self._settings.ripper_output_dir  # type: ignore[union-attr]
            if saved and Path(saved).is_dir():
                album  = disc.album_title or "CD"
                artist = disc.artist_name or "Desconocido"
                return str(Path(saved) / artist / album)

        # Pedir al usuario que elija una carpeta
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
        app_events.status_message.emit(f"CD detectado (ID: {disc_id[:8]}…) — Identificando …")

    def _on_cd_identified(self, disc: CDDisc) -> None:
        self._panel.show_identified(disc)
        if disc.cover_data:
            self._panel.update_cover(disc.cover_data)
            self._now_playing.update_cover(disc.cover_data)

    def _on_cd_ejected(self) -> None:
        self._panel.show_no_cd()
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
