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

Diseño de threading:
    El worker abre su propia DatabaseConnection al mismo archivo .db.
    Esto evita conflictos con la conexión del hilo principal: sqlite3.Connection
    no es thread-safe aunque se use check_same_thread=False.
"""
from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import IFileTagger
from audiorep.domain.track import TrackSource

logger = logging.getLogger(__name__)

# Pausa entre llamadas a la API de MusicBrainz (política: 1 req/s)
_MB_RATE_LIMIT_S = 1.1


class _EnrichmentWorker(QThread):
    """Worker que procesa la biblioteca pista por pista.

    Abre su propia DatabaseConnection para garantizar aislamiento de
    transacciones respecto al hilo principal.
    """

    progress  = pyqtSignal(int, int)    # (procesada, total)
    finished  = pyqtSignal(int, bool)   # (tracks_actualizadas, any_changed)
    cancelled = pyqtSignal()

    def __init__(
        self,
        db_path:       str,
        tagger:        IFileTagger,
        mb_client:     object,
        lastfm_client: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path  = db_path
        self._tagger   = tagger
        self._mb       = mb_client
        self._lastfm   = lastfm_client
        self._cancel   = False

    def cancel(self) -> None:
        self._cancel = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancel

    @staticmethod
    def _metadata_priority(track) -> int:
        """Orden de procesamiento: pistas con más metadatos primero.

        0 = MBID disponible (lookup directo, máxima confianza)
        1 = artista + álbum conocidos (búsqueda de texto confiable)
        2 = solo artista conocido
        3 = metadata mínima
        """
        if track.musicbrainz_id:
            return 0
        if (track.artist_name or "").strip() and (track.album_title or "").strip():
            return 1
        if (track.artist_name or "").strip():
            return 2
        return 3

    def run(self) -> None:
        # Abrir conexión propia — aislada del hilo principal
        from audiorep.infrastructure.database.connection import DatabaseConnection
        from audiorep.infrastructure.database.repositories.album_repository import AlbumRepository
        from audiorep.infrastructure.database.repositories.artist_repository import ArtistRepository
        from audiorep.infrastructure.database.repositories.label_repository import LabelRepository
        from audiorep.infrastructure.database.repositories.track_repository import TrackRepository

        db = DatabaseConnection(self._db_path)
        db.connect()
        track_repo  = TrackRepository(db)
        album_repo  = AlbumRepository(db)
        artist_repo = ArtistRepository(db)
        label_repo  = LabelRepository(db)

        try:
            self._process(track_repo, album_repo, artist_repo, label_repo)
        finally:
            db.close()

    def _process(self, track_repo, album_repo, artist_repo, label_repo) -> None:
        """
        Fase 1 — Enriquecimiento por álbum (1 llamada API por álbum único):
            year, label, label_country, release_type, artist_country.

        Fase 2 — Enriquecimiento por pista (solo pistas sin género):
            genre via recordings endpoint + Last.fm como fallback.
        """
        all_tracks = track_repo.get_all()
        eligible = [t for t in all_tracks if t.file_path and t.source == TrackSource.LOCAL]

        # ── Fase 1: álbumes únicos ──────────────────────────────────── #
        # Mapear album_id → (Album, artist_id) evitando repetidos
        album_map: dict[int, tuple] = {}
        for t in eligible:
            if t.album_id and t.album_id not in album_map:
                album = album_repo.get_by_id(t.album_id)
                if album:
                    album_map[t.album_id] = (album, t.artist_id)

        total_albums = len(album_map)
        tracks_no_genre = [t for t in eligible if not t.genre]
        total = total_albums + len(tracks_no_genre)

        updated     = 0
        any_changed = False

        logger.info(
            "EnrichmentWorker: %d álbumes, %d pistas sin género.",
            total_albums, len(tracks_no_genre),
        )

        for i, (album_id, (album, artist_id)) in enumerate(album_map.items()):
            if self._cancel:
                logger.info("EnrichmentWorker: cancelado en álbum %d/%d.", i, total_albums)
                self.cancelled.emit()
                return

            self.progress.emit(i + 1, total)

            try:
                enriched = self._mb.enrich_album(  # type: ignore[attr-defined]
                    artist=album.artist_name or "",
                    title=album.title or "",
                )

                time.sleep(_MB_RATE_LIMIT_S)

                if enriched is None:
                    continue

                # Actualizar álbum
                album_changed = False
                if not album.label and enriched.get("label"):
                    album.label = enriched["label"]
                    album_changed = True
                if not album.release_type and enriched.get("release_type"):
                    album.release_type = enriched["release_type"]
                    album_changed = True
                if not album.year and enriched.get("year"):
                    try:
                        album.year = int(enriched["year"])
                        album_changed = True
                    except (ValueError, TypeError):
                        pass
                if album_changed:
                    album_repo.save(album)
                    any_changed = True

                # Actualizar artista
                if artist_id and enriched.get("artist_country"):
                    if self._enrich_artist(
                        artist_repo, artist_id, enriched["artist_country"]
                    ):
                        any_changed = True

                # Actualizar sello
                if enriched.get("label") and enriched.get("label_country"):
                    try:
                        label_repo.upsert_country(
                            enriched["label"], enriched["label_country"]
                        )
                        any_changed = True
                    except Exception as exc:
                        logger.debug("EnrichmentWorker.label: %s", exc)

            except Exception as exc:
                logger.warning(
                    "EnrichmentWorker: error álbum '%s' — %s", album.title, exc
                )

        # ── Fase 2: pistas sin género ───────────────────────────────── #
        for j, track in enumerate(tracks_no_genre):
            if self._cancel:
                self.cancelled.emit()
                return

            self.progress.emit(total_albums + j + 1, total)

            try:
                enriched = self._mb.enrich_track(  # type: ignore[attr-defined]
                    artist=track.artist_name or "",
                    title=track.title or "",
                    album=track.album_title or "",
                    mbid=track.musicbrainz_id,
                )

                time.sleep(_MB_RATE_LIMIT_S)

                if enriched is None:
                    continue

                genre = enriched.get("genre", "")
                if not genre and self._lastfm and track.artist_name and track.title:
                    try:
                        lfm_genres = self._lastfm.get_track_genres(  # type: ignore[attr-defined]
                            track.artist_name, track.title, limit=3
                        )
                        genre = lfm_genres[0] if lfm_genres else ""
                    except Exception:
                        pass

                track_changed = False
                if not track.genre and genre:
                    track.genre = genre
                    track_changed = True
                if not track.musicbrainz_id and enriched.get("mbid"):
                    track.musicbrainz_id = enriched["mbid"]
                    track_changed = True
                if track_changed:
                    track_repo.update_tags(track)
                    self._write_file_tags(track)
                    updated += 1
                    any_changed = True

            except Exception as exc:
                logger.warning("EnrichmentWorker: error pista '%s' — %s", track.title, exc)

        logger.info(
            "EnrichmentWorker: terminado. %d pistas actualizadas, any_changed=%s.",
            updated, any_changed,
        )
        self.finished.emit(updated, any_changed)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _write_file_tags(self, track) -> None:
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

    @staticmethod
    def _enrich_album(album_repo, album_id: int, label: str, release_type: str) -> bool:
        if not label and not release_type:
            return False
        try:
            album = album_repo.get_by_id(album_id)
            if not album:
                return False
            changed = False
            if not album.label and label:
                album.label = label
                changed = True
            if not album.release_type and release_type:
                album.release_type = release_type
                changed = True
            if changed:
                album_repo.save(album)
            return changed
        except Exception as exc:
            logger.debug("EnrichmentWorker._enrich_album: %s", exc)
            return False

    @staticmethod
    def _enrich_artist(artist_repo, artist_id: int, country: str) -> bool:
        if not country:
            return False
        try:
            artist = artist_repo.get_by_id(artist_id)
            if artist and not artist.country:
                artist.country = country
                artist_repo.save(artist)
                logger.debug(
                    "EnrichmentWorker: artista %d → país '%s' guardado.", artist_id, country
                )
                return True
            return False
        except Exception as exc:
            logger.debug("EnrichmentWorker._enrich_artist: %s", exc)
            return False


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
        db_path:       str,
        tagger:        IFileTagger,
        mb_client:     object,
        lastfm_client: object | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db_path  = db_path
        self._tagger   = tagger
        self._mb       = mb_client
        self._lastfm   = lastfm_client
        self._worker: _EnrichmentWorker | None = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia el enriquecimiento.

        Si hay un worker en curso que fue cancelado, espera a que termine
        (máx. 3 s) antes de arrancar el nuevo. Si hay uno activo sin cancelar,
        lo ignora.
        """
        if self._worker and self._worker.isRunning():
            if self._worker.is_cancelled:
                self._worker.wait(3000)  # deja que el sleep de 1.1 s termine
            else:
                logger.info("EnrichmentService: ya hay un enriquecimiento en curso.")
                return

        self._worker = _EnrichmentWorker(
            db_path=self._db_path,
            tagger=self._tagger,
            mb_client=self._mb,
            lastfm_client=self._lastfm,
            parent=self,
        )
        self._worker.progress.connect(
            lambda cur, tot: app_events.enrichment_progress.emit(cur, tot)
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.cancelled.connect(lambda: app_events.enrichment_cancelled.emit())
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

    def _on_finished(self, updated: int, any_changed: bool) -> None:
        app_events.enrichment_finished.emit(updated)
        if any_changed:
            app_events.library_updated.emit()
        logger.info(
            "EnrichmentService: %d pistas actualizadas, any_changed=%s.", updated, any_changed
        )
