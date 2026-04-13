"""
TaggerService — Identificación y edición de metadatos de pistas.

Responsabilidades:
    - Identificar pistas por huella cromática (AcoustID).
    - Obtener metadatos de MusicBrainz.
    - Escribir tags en los archivos de audio.
    - Actualizar la base de datos.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import (
    IAlbumRepository,
    IArtistRepository,
    IFileTagger,
    IFingerprintProvider,
    IMetadataProvider,
    ITrackRepository,
)
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class _FingerprintWorker(QThread):
    """Identifica una pista por huella cromática y busca sus metadatos."""

    result  = pyqtSignal(object, list)  # (track, candidates)
    error   = pyqtSignal(object, str)   # (track, message)

    def __init__(
        self,
        track: Track,
        fingerprinter: IFingerprintProvider,
        metadata_provider: IMetadataProvider,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._track    = track
        self._fp       = fingerprinter
        self._provider = metadata_provider

    def run(self) -> None:
        try:
            if not self._track.file_path:
                self.error.emit(self._track, "Sin ruta de archivo.")
                return
            candidates = self._fp.identify(self._track.file_path)
            enriched: list[dict] = []
            for c in candidates:
                recording_id = c.get("recording_id", "")
                if recording_id:
                    info = self._provider.get_track_info(recording_id)
                    if info:
                        c.update(info)
                enriched.append(c)
            self.result.emit(self._track, enriched)
        except Exception as exc:
            logger.exception("Error en fingerprint: %s", exc)
            self.error.emit(self._track, str(exc))


class TaggerService(QObject):
    """
    Servicio de tags y metadatos.

    Args:
        fingerprinter:     Implementación de IFingerprintProvider.
        metadata_provider: Implementación de IMetadataProvider.
        tagger:            Implementación de IFileTagger.
        track_repo:        Repositorio de pistas.
        artist_repo:       Repositorio de artistas.
        album_repo:        Repositorio de álbumes.
    """

    fingerprint_result = pyqtSignal(object, list)   # (track, candidates)
    fingerprint_error  = pyqtSignal(object, str)    # (track, message)

    def __init__(
        self,
        fingerprinter:     IFingerprintProvider,
        metadata_provider: IMetadataProvider,
        tagger:            IFileTagger,
        track_repo:        ITrackRepository,
        artist_repo:       IArtistRepository,
        album_repo:        IAlbumRepository,
        parent:            QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._fingerprinter = fingerprinter
        self._provider      = metadata_provider
        self._tagger        = tagger
        self._track_repo    = track_repo
        self._artist_repo   = artist_repo
        self._album_repo    = album_repo
        self._worker: _FingerprintWorker | None = None

    # ------------------------------------------------------------------
    # Identificación por huella
    # ------------------------------------------------------------------

    def identify_track(self, track: Track) -> None:
        """Lanza identificación asíncrona de una pista."""
        if self._worker and self._worker.isRunning():
            logger.warning("Ya hay una identificación en progreso.")
            return
        self._worker = _FingerprintWorker(
            track=track,
            fingerprinter=self._fingerprinter,
            metadata_provider=self._provider,
            parent=self,
        )
        self._worker.result.connect(self.fingerprint_result)
        self._worker.error.connect(self.fingerprint_error)
        self._worker.start()

    # ------------------------------------------------------------------
    # Aplicar metadatos
    # ------------------------------------------------------------------

    def apply_metadata(self, track: Track, metadata: dict) -> None:
        """Escribe metadatos en archivo y actualiza la base de datos."""
        track.title         = metadata.get("title", track.title)
        track.artist_name   = metadata.get("artist", track.artist_name)
        track.album_title   = metadata.get("album", track.album_title)
        track.year          = metadata.get("year", track.year)
        track.genre         = metadata.get("genre", track.genre)
        track.track_number  = metadata.get("track_number", track.track_number)
        track.musicbrainz_id = metadata.get("recording_id", track.musicbrainz_id)

        if track.file_path:
            self._tagger.write_tags(track.file_path, {
                "title":           track.title,
                "artist":          track.artist_name,
                "album":           track.album_title,
                "date":            str(track.year) if track.year else "",
                "genre":           track.genre,
                "tracknumber":     str(track.track_number),
                "musicbrainz_trackid": track.musicbrainz_id or "",
            })

        if track.id is not None:
            self._track_repo.update_tags(track)

        app_events.library_updated.emit()
        logger.info("Metadatos aplicados: %s", track)

    def write_tags_to_file(self, track: Track, tags: dict) -> None:
        """Escribe tags directamente al archivo sin tocar la DB."""
        if track.file_path:
            self._tagger.write_tags(track.file_path, tags)
