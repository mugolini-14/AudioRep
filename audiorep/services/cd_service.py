"""
CDService — Servicio de gestión del CD físico.

Responsabilidades:
    - Detectar automáticamente la inserción/extracción del CD (polling).
    - Leer el Disc ID y las pistas con CDReader.
    - Identificar el disco en MusicBrainz en un hilo secundario.
    - Descargar la portada con CoverArtClient.
    - Proveer pistas del CD como Track del dominio para reproducción.
    - Notificar a la app via app_events.

El polling de la unidad corre en un QTimer en el hilo principal
(chequeo liviano: solo verifica si el disco ID cambió).
La identificación en MusicBrainz corre en CDIdentifier (QThread)
porque hace peticiones de red.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.exceptions import CDReadError, NoCDInsertedError, CDIdentificationError
from audiorep.core.interfaces import ICDReader, IMetadataProvider
from audiorep.domain.cd_disc import CDDisc
from audiorep.domain.track import Track, AudioFormat, TrackSource
from audiorep.infrastructure.api.coverart_client import CoverArtClient

logger = logging.getLogger(__name__)

# Intervalo de polling de la unidad (ms)
_POLL_INTERVAL_MS = 5_000


# ==================================================================
# Hilo de identificación
# ==================================================================

class CDIdentifier(QThread):
    """
    QThread que identifica el disco en MusicBrainz y descarga la portada.

    Señales:
        identified(CDDisc)  — identificación exitosa, CDDisc con metadatos.
        not_found(str)      — disc_id no encontrado en ningún servicio.
        error(str)          — error de red u otro error irrecuperable.
        cover_ready(bytes)  — portada descargada (puede llegar después).
    """

    identified  = pyqtSignal(object)  # CDDisc completo
    not_found   = pyqtSignal(str)     # disc_id
    error       = pyqtSignal(str)     # mensaje
    cover_ready = pyqtSignal(bytes)   # imagen en bytes

    def __init__(
        self,
        disc: CDDisc,
        metadata_provider: IMetadataProvider,
        cover_client: CoverArtClient,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._disc     = disc
        self._metadata = metadata_provider
        self._covers   = cover_client

    def run(self) -> None:
        logger.info("Identificando disco: %s", self._disc.disc_id)

        # 1. Buscar en MusicBrainz por Disc ID
        try:
            results = self._metadata.search_by_disc_id(self._disc.disc_id)
        except Exception as exc:
            self.error.emit(f"Error al consultar MusicBrainz: {exc}")
            return

        if not results:
            logger.info("Disco no encontrado: %s", self._disc.disc_id)
            self.not_found.emit(self._disc.disc_id)
            return

        # Tomar el primer resultado (el más probable)
        best = results[0]
        self._disc.apply_metadata(best)
        self._disc.musicbrainz_id = best.get("musicbrainz_id")
        logger.info(
            "Disco identificado: '%s' — '%s'",
            self._disc.artist_name, self._disc.album_title,
        )
        self.identified.emit(self._disc)

        # 2. Descargar portada (después de identificar, no bloquea)
        cover_url = best.get("cover_url")
        mbid      = best.get("musicbrainz_id")

        if mbid:
            try:
                image = self._covers.fetch_cover(mbid)
                if image:
                    self._disc.cover_data = image
                    self.cover_ready.emit(image)
                    return
            except Exception:
                pass  # Intentar con URL directa

        if cover_url:
            try:
                image = self._covers.fetch_cover_from_url(cover_url)
                if image:
                    self._disc.cover_data = image
                    self.cover_ready.emit(image)
            except Exception as exc:
                logger.warning("No se pudo descargar la portada: %s", exc)


# ==================================================================
# Service
# ==================================================================

class CDService(QObject):
    """
    Servicio de CD con detección automática y identificación online.

    Args:
        reader:           Implementación de ICDReader (CDReader).
        metadata_provider: Implementación de IMetadataProvider (MusicBrainzClient).
        cover_client:     CoverArtClient para descargar portadas.
        drive:            Ruta de la unidad lectora ("D:" en Windows).
                          Si está vacía se usa la unidad por defecto.
    """

    def __init__(
        self,
        reader: ICDReader,
        metadata_provider: IMetadataProvider,
        cover_client: CoverArtClient,
        drive: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._reader    = reader
        self._metadata  = metadata_provider
        self._covers    = cover_client
        self._drive     = drive

        self._current_disc: CDDisc | None = None
        self._identifier: CDIdentifier | None = None
        self._last_disc_id: str = ""

        # Timer de polling
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_drive)

    # ------------------------------------------------------------------
    # Control del polling
    # ------------------------------------------------------------------

    def start_polling(self) -> None:
        """Inicia la detección automática de CD."""
        self._poll_timer.start()
        # Verificar inmediatamente al arrancar
        self._poll_drive()
        logger.debug("Polling de unidad CD iniciado.")

    def stop_polling(self) -> None:
        """Detiene la detección automática."""
        self._poll_timer.stop()

    # ------------------------------------------------------------------
    # Operaciones manuales
    # ------------------------------------------------------------------

    def detect_cd(self) -> CDDisc | None:
        """
        Intenta leer el CD de forma manual (sin esperar el timer).
        Retorna el CDDisc si hay un CD presente, o None.
        """
        return self._poll_drive()

    def identify_current_disc(self) -> None:
        """
        Inicia (o reinicia) la identificación del disco actual en MusicBrainz.
        No hace nada si no hay CD presente.
        """
        if self._current_disc is None:
            return
        self._start_identification(self._current_disc)

    @property
    def current_disc(self) -> CDDisc | None:
        return self._current_disc

    # ------------------------------------------------------------------
    # Tracks del CD como entidades de dominio
    # ------------------------------------------------------------------

    def get_tracks_as_domain(self) -> list[Track]:
        """
        Convierte las pistas del CD actual a entidades Track reproducibles.

        Returns:
            Lista de Track con source=CD, listos para el PlayerService.
        """
        if not self._current_disc:
            return []

        disc = self._current_disc
        tracks: list[Track] = []
        for cd_track in disc.tracks:
            tracks.append(Track(
                title=cd_track.title or f"Pista {cd_track.number:02d}",
                artist_name=cd_track.artist_name or disc.artist_name,
                album_title=disc.album_title,
                track_number=cd_track.number,
                duration_ms=cd_track.duration_ms,
                year=disc.year,
                genre=disc.genre,
                file_path=disc.drive_path,   # la unidad lectora
                format=AudioFormat.CD,
                source=TrackSource.CD,
            ))
        return tracks

    # ------------------------------------------------------------------
    # Polling interno
    # ------------------------------------------------------------------

    def _poll_drive(self) -> CDDisc | None:
        """
        Verifica si hay un CD en la unidad. Emite eventos si cambió.
        Retorna el CDDisc actual o None.
        """
        try:
            disc = self._reader.read_disc(self._drive)
        except NoCDInsertedError:
            if self._last_disc_id:
                logger.info("CD retirado.")
                self._current_disc  = None
                self._last_disc_id  = ""
                app_events.cd_ejected.emit()
            return None
        except CDReadError as exc:
            logger.debug("Error al leer unidad CD: %s", exc)
            return None

        # CD nuevo detectado
        if disc.disc_id != self._last_disc_id:
            logger.info("CD insertado: %s", disc.disc_id)
            self._current_disc = disc
            self._last_disc_id = disc.disc_id
            app_events.cd_inserted.emit(disc.disc_id)
            self._start_identification(disc)

        return disc

    def _start_identification(self, disc: CDDisc) -> None:
        """Lanza el CDIdentifier en segundo plano."""
        if self._identifier and self._identifier.isRunning():
            self._identifier.terminate()
            self._identifier.wait()

        self._identifier = CDIdentifier(
            disc=disc,
            metadata_provider=self._metadata,
            cover_client=self._covers,
            parent=self,
        )
        self._identifier.identified.connect(self._on_identified)
        self._identifier.not_found.connect(self._on_not_found)
        self._identifier.error.connect(self._on_identification_error)
        self._identifier.cover_ready.connect(self._on_cover_ready)
        self._identifier.start()

        app_events.status_message.emit("Identificando disco …")

    # ------------------------------------------------------------------
    # Handlers del CDIdentifier
    # ------------------------------------------------------------------

    def _on_identified(self, disc: CDDisc) -> None:
        self._current_disc = disc
        app_events.cd_identified.emit(disc)
        app_events.status_message.emit(
            f"💿  {disc.artist_name} — {disc.album_title}"
        )

    def _on_not_found(self, disc_id: str) -> None:
        app_events.status_message.emit(
            f"Disco no encontrado en MusicBrainz (ID: {disc_id[:8]}…)"
        )

    def _on_identification_error(self, message: str) -> None:
        logger.error("Error de identificación CD: %s", message)
        app_events.status_message.emit(f"⚠ Error al identificar el disco: {message}")

    def _on_cover_ready(self, image_data: bytes) -> None:
        logger.debug("Portada del CD lista (%d bytes).", len(image_data))
        # La NowPlaying se actualiza cuando el Controller escucha cover_ready
        # del CDIdentifier directamente (via CDController)
