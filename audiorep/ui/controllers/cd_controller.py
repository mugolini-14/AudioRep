"""
CDController — Bisagra entre CDPanel y CDService.

Responsabilidades:
    - Conectar las señales de CDPanel con CDService.
    - Escuchar app_events (cd_inserted, cd_identified, cd_ejected).
    - Actualizar CDPanel cuando cambia el estado del disco.
    - Pasar pistas del CD al PlayerService para reproducción.
    - Actualizar NowPlaying con la portada del CD al reproducir.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.cd_disc import CDDisc, RipStatus
from audiorep.services.cd_service import CDService
from audiorep.services.player_service import PlayerService
from audiorep.ui.widgets.cd_panel import CDPanel
from audiorep.ui.widgets.now_playing import NowPlaying

logger = logging.getLogger(__name__)


class CDController:
    """
    Controller del CD.

    Args:
        cd_service:    Servicio de CD (detección, identificación).
        player_service: Servicio de reproducción.
        cd_panel:      Widget del panel de CD.
        now_playing:   Widget de información de pista actual.
    """

    def __init__(
        self,
        cd_service: CDService,
        player_service: PlayerService,
        cd_panel: CDPanel,
        now_playing: NowPlaying,
    ) -> None:
        self._cd_service    = cd_service
        self._player        = player_service
        self._panel         = cd_panel
        self._now_playing   = now_playing

        self._connect_panel()
        self._connect_app_events()
        self._connect_cd_service()

        # Iniciar detección automática
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
        """Conecta el CDIdentifier para recibir la portada cuando llega."""
        # La portada llega a través del CDService._on_cover_ready
        # que emite al CDIdentifier. Conectamos cuando se crea el identificador.
        # Lo hacemos escuchando cd_identified y luego verificando cover_data.
        pass

    # ------------------------------------------------------------------
    # Handlers: CDPanel
    # ------------------------------------------------------------------

    def _on_detect_requested(self) -> None:
        """El usuario presionó "Detectar CD" manualmente."""
        self._panel.show_reading()
        disc = self._cd_service.detect_cd()
        if disc:
            self._panel.show_disc(disc)
        else:
            self._panel.show_no_cd()
            app_events.status_message.emit("No se detectó ningún CD en la unidad.")

    def _on_identify_requested(self) -> None:
        """El usuario solicitó re-identificar el disco."""
        self._cd_service.identify_current_disc()
        app_events.status_message.emit("Identificando disco en MusicBrainz …")

    def _on_play_cd(self) -> None:
        """Reproducir todas las pistas del CD."""
        tracks = self._cd_service.get_tracks_as_domain()
        if not tracks:
            return
        self._player.set_queue(tracks, start_index=0)
        logger.info("Reproduciendo CD: %d pistas.", len(tracks))

    def _on_play_track(self, track_number: int) -> None:
        """Reproducir desde una pista específica del CD."""
        tracks = self._cd_service.get_tracks_as_domain()
        if not tracks:
            return
        # Encontrar el índice de la pista solicitada
        start = next(
            (i for i, t in enumerate(tracks) if t.track_number == track_number),
            0,
        )
        self._player.set_queue(tracks, start_index=start)
        logger.info("Reproduciendo pista CD nro. %d.", track_number)

    def _on_rip_all(self) -> None:
        """Ripear todas las pistas (delegado al RipperService, Paso 7)."""
        app_events.status_message.emit(
            "Ripeo de CD: función disponible en el Paso 7 (RipperService)."
        )
        logger.info("Rip all solicitado (pendiente implementación RipperService).")

    def _on_rip_track(self, track_number: int) -> None:
        app_events.status_message.emit(
            f"Ripeo de pista {track_number}: pendiente (Paso 7)."
        )

    # ------------------------------------------------------------------
    # Handlers: app_events
    # ------------------------------------------------------------------

    def _on_cd_inserted(self, disc_id: str) -> None:
        """CD detectado: mostrar estado provisional y esperar identificación."""
        disc = self._cd_service.current_disc
        if disc:
            self._panel.show_disc(disc)
        app_events.status_message.emit(f"CD detectado (ID: {disc_id[:8]}…) — Identificando …")

    def _on_cd_identified(self, disc: CDDisc) -> None:
        """Disco identificado: actualizar panel con metadatos completos."""
        self._panel.show_identified(disc)
        # Si tiene portada en memoria, mostrarla
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
