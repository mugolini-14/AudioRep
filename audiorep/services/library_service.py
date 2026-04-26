"""
LibraryService — Gestiona la biblioteca de música local.

Responsabilidades:
    - Escanear directorios y agregar pistas a la base de datos.
    - Delegar el escaneo a un worker thread para no bloquear la UI.
    - Exponer métodos de búsqueda y listado.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import (
    IAlbumRepository,
    IArtistRepository,
    IFileTagger,
    ILabelRepository,
    ILibraryScanner,
    ITrackRepository,
)
from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


def _parse_slash_int(value: object, default: int) -> int:
    """Parsea enteros en formato "3" o "3/12" (estilo mutagen)."""
    try:
        return int(str(value).split("/")[0])
    except (ValueError, TypeError, AttributeError):
        return default


def _parse_year(value: object) -> int | None:
    """Parsea año desde strings como '2023', '2023-01-15' o None."""
    if not value:
        return None
    try:
        return int(str(value)[:4])
    except (ValueError, TypeError):
        return None


class _ScanWorker(QThread):
    """Worker de escaneo de directorio. No accede a la UI."""

    finished = pyqtSignal(int)   # cantidad de pistas importadas
    progress = pyqtSignal(int, int)  # (procesadas, total)
    error    = pyqtSignal(str)

    def __init__(
        self,
        directory: str,
        scanner: ILibraryScanner,
        tagger: IFileTagger,
        track_repo: ITrackRepository,
        artist_repo: IArtistRepository,
        album_repo: IAlbumRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._directory  = directory
        self._scanner    = scanner
        self._tagger     = tagger
        self._track_repo = track_repo
        self._artist_repo = artist_repo
        self._album_repo = album_repo

    def run(self) -> None:
        try:
            paths = self._scanner.scan(self._directory)
            total = len(paths)
            imported = 0
            for i, path in enumerate(paths):
                self._import_file(path)
                imported += 1
                self.progress.emit(i + 1, total)
            self.finished.emit(imported)
        except Exception as exc:
            logger.exception("Error en escaneo: %s", exc)
            self.error.emit(str(exc))

    def _import_file(self, file_path: str) -> None:
        try:
            tags = self._tagger.read_tags(file_path)
            artist_name = tags.get("artist", "") or ""
            album_title = tags.get("album", "") or ""

            artist = self._artist_repo.get_or_create(artist_name)
            album  = self._album_repo.get_or_create(
                title=album_title,
                artist_id=artist.id or 0,
                artist_name=artist_name,
            )

            from audiorep.domain.track import AudioFormat, TrackSource
            ext = Path(file_path).suffix.upper().lstrip(".")
            try:
                fmt = AudioFormat(ext)
            except ValueError:
                fmt = AudioFormat.UNKNOWN

            track = Track(
                title=tags.get("title", "") or Path(file_path).stem,
                artist_name=artist_name,
                album_title=album_title,
                track_number=_parse_slash_int(tags.get("tracknumber"), 0),
                disc_number=_parse_slash_int(tags.get("discnumber"), 1),
                duration_ms=int(tags.get("duration_ms", 0) or 0),
                year=_parse_year(tags.get("date")),
                genre=tags.get("genre", "") or "",
                file_path=file_path,
                format=fmt,
                source=TrackSource.LOCAL,
                bitrate_kbps=int(tags.get("bitrate_kbps", 0) or 0),
                musicbrainz_id=tags.get("musicbrainz_trackid"),
                artist_id=artist.id,
                album_id=album.id,
            )
            self._track_repo.save(track)
        except Exception as exc:
            logger.warning("No se pudo importar %s: %s", file_path, exc)


class LibraryService(QObject):
    """
    Servicio de biblioteca musical.

    Args:
        track_repo:  Repositorio de pistas.
        artist_repo: Repositorio de artistas.
        album_repo:  Repositorio de álbumes.
        scanner:     Escáner de directorios.
        tagger:      Lector de tags de archivos de audio.
    """

    def __init__(
        self,
        track_repo:  ITrackRepository,
        artist_repo: IArtistRepository,
        album_repo:  IAlbumRepository,
        scanner:     ILibraryScanner,
        tagger:      IFileTagger,
        label_repo:  ILabelRepository | None = None,
        parent:      QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._track_repo  = track_repo
        self._artist_repo = artist_repo
        self._album_repo  = album_repo
        self._label_repo  = label_repo
        self._scanner     = scanner
        self._tagger      = tagger
        self._worker: _ScanWorker | None = None

    # ------------------------------------------------------------------
    # Escaneo
    # ------------------------------------------------------------------

    def import_directory(self, directory: str) -> None:
        """Inicia el escaneo asíncrono de un directorio."""
        if self._worker and self._worker.isRunning():
            logger.warning("Ya hay un escaneo en progreso.")
            return
        app_events.scan_started.emit(directory)
        self._worker = _ScanWorker(
            directory=directory,
            scanner=self._scanner,
            tagger=self._tagger,
            track_repo=self._track_repo,
            artist_repo=self._artist_repo,
            album_repo=self._album_repo,
            parent=self,
        )
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.progress.connect(lambda p, t: app_events.scan_progress.emit(p, t))
        self._worker.error.connect(lambda e: app_events.error_occurred.emit("Error de escaneo", e))
        self._worker.start()

    def _on_scan_finished(self, count: int) -> None:
        app_events.scan_finished.emit(count)
        app_events.library_updated.emit()
        logger.info("Escaneo terminado: %d pistas importadas.", count)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_all_tracks(self) -> list[Track]:
        return self._track_repo.get_all()

    def get_all_albums(self) -> list[Album]:
        return self._album_repo.get_all()

    def get_all_artists(self) -> list[Artist]:
        return self._artist_repo.get_all()

    def get_label_country_map(self) -> dict[str, str]:
        """Retorna {nombre_sello: país} para todos los sellos con país conocido."""
        if self._label_repo is None:
            return {}
        return self._label_repo.get_country_map()

    def search_tracks(self, query: str) -> list[Track]:
        return self._track_repo.search(query)

    # ------------------------------------------------------------------
    # Enriquecimiento de metadatos desde identificación MB
    # ------------------------------------------------------------------

    def enrich_from_cd_disc(self, disc_data: dict) -> None:
        """
        Actualiza Album.release_type, Artist.country y Label.country
        usando los datos de un disco identificado por MusicBrainz.

        disc_data keys: album, artist, artist_country, label, label_country, release_type
        """
        album_title    = disc_data.get("album", "")
        artist_name    = disc_data.get("artist", "")
        artist_country = disc_data.get("artist_country", "")
        label_name     = disc_data.get("label", "")
        label_country  = disc_data.get("label_country", "")
        release_type   = disc_data.get("release_type", "")

        if release_type and album_title and artist_name:
            try:
                self._album_repo.update_release_type(  # type: ignore[attr-defined]
                    album_title, artist_name, release_type
                )
            except Exception:
                pass

        if artist_country and artist_name:
            try:
                self._artist_repo.update_country(  # type: ignore[attr-defined]
                    artist_name, artist_country
                )
            except Exception:
                pass

        if label_name and label_country and self._label_repo is not None:
            try:
                self._label_repo.upsert_country(label_name, label_country)
            except Exception:
                pass

    def get_recently_added(self, limit: int = 50) -> list[Track]:
        return self._track_repo.get_recently_added(limit)

    def get_most_played(self, limit: int = 25) -> list[Track]:
        return self._track_repo.get_most_played(limit)

    def get_highest_rated(self, limit: int = 25) -> list[Track]:
        return self._track_repo.get_highest_rated(limit)

    def delete_track(self, track_id: int) -> None:
        self._track_repo.delete(track_id)
        app_events.library_updated.emit()
