"""
CDService — Gestiona la detección e identificación de CDs.

Responsabilidades:
    - Sondear la unidad de CD periódicamente.
    - Identificar el disco en MusicBrainz.
    - Descargar portada y emitir CDDisc completo vía app_events.
    - Convertir pistas de CD a objetos Track con URIs CDDA para VLC.
    - Exponer la lista de lectoras disponibles y permitir cambiar la lectora activa.
"""
from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import ICDReader, IMetadataProvider
from audiorep.domain.cd_disc import CDDisc
from audiorep.domain.track import AudioFormat, Track, TrackSource

logger = logging.getLogger(__name__)


class _IdentifyWorker(QThread):
    """Worker que busca metadatos del disco en MusicBrainz."""

    identified = pyqtSignal(object)  # CDDisc con metadatos
    error      = pyqtSignal(str)

    def __init__(
        self,
        disc: CDDisc,
        metadata_provider: IMetadataProvider,
        cover_client: object,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._disc     = disc
        self._provider = metadata_provider
        self._covers   = cover_client

    def run(self) -> None:
        try:
            results = self._provider.search_by_disc_id(self._disc.disc_id)
            if not results:
                self.error.emit("No se encontró información para este disco.")
                return

            best = results[0]
            self._disc.album_title    = best.get("album", self._disc.album_title)
            self._disc.artist_name    = best.get("artist", self._disc.artist_name)
            self._disc.year           = best.get("year", self._disc.year)
            self._disc.musicbrainz_id = best.get("release_id", "")
            self._disc.genre          = best.get("genre", "")
            self._disc.label          = best.get("label", "")

            # Actualizar títulos y musicbrainz_id de pistas si están disponibles.
            # Formato normalizado esperado: [{"number": int, "title": str, "recording_id": str}]
            mb_tracks = best.get("tracks", [])
            track_by_number = {t.number: t for t in self._disc.tracks}
            for mt in mb_tracks:
                num = mt.get("number")
                cd_track = track_by_number.get(num) if num else None
                if cd_track is None and mb_tracks:
                    # Fallback: asignar por posición
                    idx = mb_tracks.index(mt)
                    if idx < len(self._disc.tracks):
                        cd_track = self._disc.tracks[idx]
                if cd_track:
                    cd_track.title          = mt.get("title", cd_track.title)
                    cd_track.musicbrainz_id = mt.get("recording_id", "")

            # Descargar portada
            if self._disc.musicbrainz_id:
                try:
                    cover_data = self._covers.get_cover(self._disc.musicbrainz_id)
                    if cover_data:
                        self._disc.cover_data = cover_data
                except Exception as exc:
                    logger.warning("No se pudo obtener la portada: %s", exc)

            self.identified.emit(self._disc)
        except Exception as exc:
            logger.exception("Error identificando disco: %s", exc)
            self.error.emit(str(exc))


class CDService(QObject):
    """
    Servicio de CD.

    Args:
        reader:            Implementación de ICDReader.
        metadata_provider: Implementación de IMetadataProvider.
        cover_client:      Cliente para descargar portadas (CoverArtClient).
    """

    def __init__(
        self,
        reader: ICDReader,
        metadata_provider: IMetadataProvider,
        cover_client: object,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._reader          = reader
        self._provider        = metadata_provider
        self._covers          = cover_client
        self._current_disc: CDDisc | None = None
        self._last_disc_id: str | None    = None
        self._selected_drive: str         = ""
        self._worker: _IdentifyWorker | None = None

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(3000)
        self._poll_timer.timeout.connect(self._poll_drive)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def start_polling(self) -> None:
        self._poll_timer.start()

    def stop_polling(self) -> None:
        self._poll_timer.stop()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_disc(self) -> CDDisc | None:
        return self._current_disc

    def set_drive(self, drive: str) -> None:
        """Cambia la lectora activa. El próximo sondeo usará esta unidad."""
        self._selected_drive = drive
        logger.info("CDService: lectora activa → %r", drive)

    def list_drives(self) -> list[str]:
        """Retorna la lista de lectoras disponibles."""
        return self._reader.list_drives()

    def detect_cd(self) -> CDDisc | None:
        """Detecta el CD en la unidad activa de forma síncrona."""
        try:
            disc = self._reader.read_disc(self._selected_drive)
            self._current_disc = disc
            return disc
        except Exception:
            self._current_disc = None
            return None

    def identify_current_disc(self) -> None:
        """Lanza identificación asíncrona del disco actual."""
        if self._current_disc is None:
            return
        if self._worker and self._worker.isRunning():
            return
        self._worker = _IdentifyWorker(
            disc=self._current_disc,
            metadata_provider=self._provider,
            cover_client=self._covers,
            parent=self,
        )
        self._worker.identified.connect(self._on_identified)
        self._worker.error.connect(
            lambda e: app_events.error_occurred.emit("Error CD", e)
        )
        self._worker.start()

    def get_tracks_as_domain(self) -> list[Track]:
        """
        Convierte las pistas del CDDisc actual en objetos Track con
        URIs CDDA compatibles con VLC (cdda://<device>@<track>).
        """
        if self._current_disc is None:
            return []
        drive = self._current_disc.drive_path or self._selected_drive or ""
        device_uri = self._build_cdda_uri(drive)
        tracks: list[Track] = []
        for cd_track in self._current_disc.tracks:
            file_path = device_uri
            track = Track(
                title=cd_track.title or f"Pista {cd_track.number}",
                artist_name=self._current_disc.artist_name or "",
                album_title=self._current_disc.album_title or "",
                track_number=cd_track.number,
                duration_ms=cd_track.duration_ms,
                year=self._current_disc.year,
                label=self._current_disc.label or "",
                format=AudioFormat.CD,
                source=TrackSource.CD,
                musicbrainz_id=cd_track.musicbrainz_id,
                file_path=file_path,
            )
            tracks.append(track)
        return tracks

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_cdda_uri(drive: str) -> str:
        """
        Construye el URI CDDA del dispositivo para VLC.

        El número de pista NO va en el URI; se pasa como media option
        ':cdda-track=N' en VLCPlayer.play() para cada pista individual.

        Formatos:
            Linux:   cdda:///dev/sr0
            Windows: cdda:///D:/
        """
        if not drive:
            return "cdda://"
        drive = drive.rstrip("/\\")
        if drive.startswith("/"):
            # Linux: /dev/sr0
            return f"cdda://{drive}"
        # Windows: D: → cdda:///D:/
        return f"cdda:///{drive}/"

    def _poll_drive(self) -> None:
        try:
            disc = self._reader.read_disc(self._selected_drive)
            if disc.disc_id != self._last_disc_id:
                self._last_disc_id = disc.disc_id
                self._current_disc = disc
                app_events.cd_inserted.emit(disc.disc_id)
                self.identify_current_disc()
        except Exception:
            if self._last_disc_id is not None:
                self._last_disc_id = None
                self._current_disc = None
                app_events.cd_ejected.emit()

    def _on_identified(self, disc: CDDisc) -> None:
        self._current_disc = disc
        app_events.cd_identified.emit(disc)
        logger.info("Disco identificado: %s — %s", disc.artist_name, disc.album_title)
