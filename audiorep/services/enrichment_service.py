"""
EnrichmentService — Enriquecimiento masivo de metadatos de la biblioteca.

Responsabilidades:
    - Recorrer todas las pistas locales de la biblioteca.
    - Para cada pista, consultar MusicBrainz (y opcionalmente Last.fm)
      para obtener género, sello, tipo de álbum y país de artista/sello.
    - Actualizar los registros en la base de datos y los tags de los archivos.
    - Operar en background con rate-limiting (1 req/s de MusicBrainz).
    - Emitir progreso vía app_events.
    - Ser cancelable en cualquier momento.
"""
from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import (
    IAlbumRepository,
    IArtistRepository,
    IFileTagger,
    ILabelRepository,
    ITrackRepository,
)
from audiorep.domain.track import TrackSource

logger = logging.getLogger(__name__)

# Pausa entre llamadas a la API de MusicBrainz (política: 1 req/s)
_MB_RATE_LIMIT_S = 1.1


class _EnrichmentWorker(QThread):
    """Worker que procesa la biblioteca pista por pista."""

    progress  = pyqtSignal(int, int)   # (procesada, total)
    finished  = pyqtSignal(int)        # tracks_actualizadas
    cancelled = pyqtSignal()

    def __init__(
        self,
        track_repo:   ITrackRepository,
        album_repo:   IAlbumRepository,
        artist_repo:  IArtistRepository,
        label_repo:   ILabelRepository,
        tagger:       IFileTagger,
        mb_client:    object,
        lastfm_client: object | None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._track_repo   = track_repo
        self._album_repo   = album_repo
        self._artist_repo  = artist_repo
        self._label_repo   = label_repo
        self._tagger       = tagger
        self._mb           = mb_client
        self._lastfm       = lastfm_client
        self._cancel       = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        all_tracks = self._track_repo.get_all()
        # Solo pistas locales con ruta de archivo
        eligible = [
            t for t in all_tracks
            if t.file_path and t.source == TrackSource.LOCAL
        ]
        total   = len(eligible)
        updated = 0

        logger.info("EnrichmentWorker: %d pistas elegibles para enriquecimiento.", total)

        for i, track in enumerate(eligible):
            if self._cancel:
                logger.info("EnrichmentWorker: cancelado en pista %d/%d.", i, total)
                self.cancelled.emit()
                return

            self.progress.emit(i + 1, total)

            try:
                enriched = self._mb.enrich_track(  # type: ignore[attr-defined]
                    artist=track.artist_name or "",
                    title=track.title or "",
                    album=track.album_title or "",
                    mbid=track.musicbrainz_id,
                )

                # Rate limiting: respetar política de MB (1 req/s)
                time.sleep(_MB_RATE_LIMIT_S)

                if enriched is None:
                    continue

                # Complementar género con Last.fm si MB no tiene
                genre = enriched.get("genre", "")
                if not genre and self._lastfm and track.artist_name and track.title:
                    try:
                        lfm_genres = self._lastfm.get_track_genres(  # type: ignore[attr-defined]
                            track.artist_name, track.title, limit=3
                        )
                        genre = lfm_genres[0] if lfm_genres else ""
                    except Exception:
                        pass

                # ── Actualizar pista ────────────────────────────────── #
                track_changed = False

                if not track.genre and genre:
                    track.genre = genre
                    track_changed = True

                if not track.musicbrainz_id and enriched.get("mbid"):
                    track.musicbrainz_id = enriched["mbid"]
                    track_changed = True

                if not track.year and enriched.get("year"):
                    try:
                        track.year = int(enriched["year"])
                        track_changed = True
                    except (ValueError, TypeError):
                        pass

                if track_changed:
                    self._track_repo.update_tags(track)
                    self._write_file_tags(track)
                    updated += 1

                # ── Actualizar álbum ────────────────────────────────── #
                if track.album_id:
                    self._enrich_album(
                        track.album_id,
                        enriched.get("label", ""),
                        enriched.get("release_type", ""),
                    )

                # ── Actualizar artista ──────────────────────────────── #
                if track.artist_id and enriched.get("artist_country"):
                    self._enrich_artist(track.artist_id, enriched["artist_country"])

                # ── Actualizar sello ────────────────────────────────── #
                if enriched.get("label") and enriched.get("label_country"):
                    try:
                        self._label_repo.upsert_country(
                            enriched["label"], enriched["label_country"]
                        )
                    except Exception:
                        pass

            except Exception as exc:
                logger.warning(
                    "EnrichmentWorker: error procesando '%s' — %s", track.title, exc
                )

        logger.info("EnrichmentWorker: terminado. %d pistas actualizadas.", updated)
        self.finished.emit(updated)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _write_file_tags(self, track) -> None:
        """Escribe los tags actualizados al archivo de audio (no crítico)."""
        if not track.file_path:
            return
        try:
            tags: dict = {}
            if track.genre:
                tags["genre"] = track.genre
            if track.musicbrainz_id:
                tags["musicbrainz_trackid"] = track.musicbrainz_id
            if track.year:
                tags["date"] = str(track.year)
            if tags:
                self._tagger.write_tags(track.file_path, tags)
        except Exception as exc:
            logger.debug("EnrichmentWorker: no se pudo escribir tag en %s: %s",
                         track.file_path, exc)

    def _enrich_album(self, album_id: int, label: str, release_type: str) -> None:
        if not label and not release_type:
            return
        try:
            album = self._album_repo.get_by_id(album_id)
            if not album:
                return
            changed = False
            if not album.label and label:
                album.label = label
                changed = True
            if not album.release_type and release_type:
                album.release_type = release_type
                changed = True
            if changed:
                self._album_repo.save(album)
        except Exception as exc:
            logger.debug("EnrichmentWorker._enrich_album: %s", exc)

    def _enrich_artist(self, artist_id: int, country: str) -> None:
        if not country:
            return
        try:
            artist = self._artist_repo.get_by_id(artist_id)
            if artist and not artist.country:
                artist.country = country
                self._artist_repo.save(artist)
        except Exception as exc:
            logger.debug("EnrichmentWorker._enrich_artist: %s", exc)


class EnrichmentService(QObject):
    """
    Servicio de enriquecimiento masivo de metadatos.

    Triggers:
        - Al importar una carpeta (scan_finished).
        - Al arrancar la app si el intervalo configurado se cumplió.
        - Manualmente desde Configuración ("Actualizar ahora").
    """

    def __init__(
        self,
        track_repo:    ITrackRepository,
        album_repo:    IAlbumRepository,
        artist_repo:   IArtistRepository,
        label_repo:    ILabelRepository,
        tagger:        IFileTagger,
        mb_client:     object,
        lastfm_client: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._track_repo   = track_repo
        self._album_repo   = album_repo
        self._artist_repo  = artist_repo
        self._label_repo   = label_repo
        self._tagger       = tagger
        self._mb           = mb_client
        self._lastfm       = lastfm_client
        self._worker: _EnrichmentWorker | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia el enriquecimiento. Si ya hay uno en curso, lo ignora."""
        if self._worker and self._worker.isRunning():
            logger.info("EnrichmentService: ya hay un enriquecimiento en curso.")
            return

        self._worker = _EnrichmentWorker(
            track_repo=self._track_repo,
            album_repo=self._album_repo,
            artist_repo=self._artist_repo,
            label_repo=self._label_repo,
            tagger=self._tagger,
            mb_client=self._mb,
            lastfm_client=self._lastfm,
            parent=self,
        )
        self._worker.progress.connect(
            lambda cur, tot: app_events.enrichment_progress.emit(cur, tot)
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.cancelled.connect(app_events.enrichment_cancelled.emit)
        self._worker.start()
        app_events.enrichment_started.emit()
        logger.info("EnrichmentService: enriquecimiento iniciado.")

    def cancel(self) -> None:
        """Solicita cancelar el enriquecimiento en curso."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _on_finished(self, updated: int) -> None:
        app_events.enrichment_finished.emit(updated)
        if updated > 0:
            app_events.library_updated.emit()
        logger.info("EnrichmentService: %d pistas actualizadas.", updated)
