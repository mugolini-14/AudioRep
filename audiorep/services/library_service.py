"""
LibraryService — Gestión de la biblioteca musical local.

Responsabilidades:
    - Importar carpetas: escanear archivos, leer tags, persistir en BD.
    - Exponer la biblioteca (artistas, álbumes, pistas) a la UI.
    - Búsqueda full-text en la biblioteca.

La importación se ejecuta en un QThread (LibraryImporter) para no
bloquear el event loop de Qt. El progreso se comunica via app_events.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.exceptions import DuplicateTrackError, TaggerError
from audiorep.core.interfaces import IFileTagger, ILibraryScanner
from audiorep.core.interfaces import IArtistRepository, IAlbumRepository, ITrackRepository
from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.track import Track, AudioFormat, TrackSource

logger = logging.getLogger(__name__)


# ==================================================================
# Hilo de importación
# ==================================================================

class LibraryImporter(QThread):
    """
    QThread que importa archivos de audio a la biblioteca en segundo plano.

    Señales:
        progress(current, total)   — progreso de importación.
        track_imported(track)      — una pista fue importada exitosamente.
        finished_import(ok, skip)  — importación completa (ok importadas, skip omitidas).
    """

    progress       = pyqtSignal(int, int)   # (current, total)
    track_imported = pyqtSignal(object)     # Track
    finished_import = pyqtSignal(int, int)  # (imported, skipped)

    def __init__(
        self,
        directory: str,
        scanner: ILibraryScanner,
        tagger: IFileTagger,
        track_repo: ITrackRepository,
        artist_repo: IArtistRepository,
        album_repo: IAlbumRepository,
    ) -> None:
        super().__init__()
        self._directory  = directory
        self._scanner    = scanner
        self._tagger     = tagger
        self._track_repo = track_repo
        self._artist_repo = artist_repo
        self._album_repo  = album_repo
        self._cancelled   = False

    def cancel(self) -> None:
        """Solicita cancelar la importación en curso."""
        self._cancelled = True

    def run(self) -> None:
        """Ejecutado en el hilo secundario."""
        logger.info("Iniciando importación de: %s", self._directory)
        app_events.scan_started.emit(self._directory)

        files = self._scanner.scan(self._directory)
        total = len(files)
        app_events.scan_progress.emit(0, total)

        imported = 0
        skipped  = 0

        for i, file_path in enumerate(files, start=1):
            if self._cancelled:
                logger.info("Importación cancelada por el usuario.")
                break

            try:
                track = self._import_file(file_path)
                imported += 1
                self.track_imported.emit(track)
            except DuplicateTrackError:
                skipped += 1
            except TaggerError as exc:
                logger.warning("Error de tags en '%s': %s", file_path, exc)
                skipped += 1
            except Exception as exc:
                logger.error("Error inesperado importando '%s': %s", file_path, exc)
                skipped += 1

            self.progress.emit(i, total)
            app_events.scan_progress.emit(i, total)

        logger.info("Importación finalizada: %d importadas, %d omitidas.", imported, skipped)
        self.finished_import.emit(imported, skipped)
        app_events.scan_finished.emit(imported)
        app_events.library_updated.emit()

    def _import_file(self, file_path: str) -> Track:
        """
        Importa un único archivo. Lanza DuplicateTrackError si ya existe.
        Crea o reutiliza el Artist y Album correspondientes.
        """
        if self._track_repo.exists_by_path(file_path):
            raise DuplicateTrackError(file_path)

        tags = self._tagger.read_tags(file_path)

        # ── Artist ──────────────────────────────────────────────────
        artist_name = tags.get("artist") or "Desconocido"
        artist = self._artist_repo.get_or_create(artist_name)

        # ── Album ───────────────────────────────────────────────────
        album_title = tags.get("album") or "Sin álbum"
        album = self._album_repo.get_or_create(
            title=album_title,
            artist_id=artist.id,
            artist_name=artist.name,
        )
        # Actualizar año del álbum si aún no lo tiene
        if album.year is None and tags.get("year"):
            album.year = tags["year"]
            self._album_repo.save(album)

        # ── Track ───────────────────────────────────────────────────
        track = Track(
            title=tags.get("title") or Path(file_path).stem,
            artist_id=artist.id,
            artist_name=artist.name,
            album_id=album.id,
            album_title=album.title,
            track_number=tags.get("track_number", 0),
            disc_number=tags.get("disc_number", 1),
            duration_ms=tags.get("duration_ms", 0),
            year=tags.get("year"),
            genre=tags.get("genre", ""),
            file_path=file_path,
            format=AudioFormat.from_extension(Path(file_path).suffix),
            source=TrackSource.LOCAL,
            bitrate_kbps=tags.get("bitrate_kbps", 0),
            sample_rate_hz=tags.get("sample_rate_hz", 0),
            channels=tags.get("channels", 2),
            file_size_bytes=tags.get("file_size_bytes", 0),
            comment=tags.get("comment", ""),
        )
        return self._track_repo.save(track)


# ==================================================================
# Service
# ==================================================================

class LibraryService:
    """
    Fachada de la biblioteca musical.

    Args:
        track_repo:  Repositorio de pistas.
        artist_repo: Repositorio de artistas.
        album_repo:  Repositorio de álbumes.
        scanner:     Escáner de directorios (ILibraryScanner).
        tagger:      Lector/escritor de tags (IFileTagger).
    """

    def __init__(
        self,
        track_repo:  ITrackRepository,
        artist_repo: IArtistRepository,
        album_repo:  IAlbumRepository,
        scanner:     ILibraryScanner,
        tagger:      IFileTagger,
    ) -> None:
        self._track_repo  = track_repo
        self._artist_repo = artist_repo
        self._album_repo  = album_repo
        self._scanner     = scanner
        self._tagger      = tagger
        self._importer: LibraryImporter | None = None

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------

    def import_directory(self, directory: str) -> LibraryImporter:
        """
        Inicia la importación de un directorio en segundo plano.

        Returns:
            El LibraryImporter (QThread) ya iniciado.
            Conectar sus señales antes de llamar a este método
            o usar las señales globales app_events.scan_*.
        """
        if self._importer and self._importer.isRunning():
            logger.warning("Ya hay una importación en curso.")
            return self._importer

        self._importer = LibraryImporter(
            directory=directory,
            scanner=self._scanner,
            tagger=self._tagger,
            track_repo=self._track_repo,
            artist_repo=self._artist_repo,
            album_repo=self._album_repo,
        )
        self._importer.start()
        app_events.status_message.emit(f"Importando: {directory} …")
        return self._importer

    def cancel_import(self) -> None:
        """Cancela la importación en curso si existe."""
        if self._importer and self._importer.isRunning():
            self._importer.cancel()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_all_artists(self) -> list[Artist]:
        return self._artist_repo.get_all()

    def get_albums_by_artist(self, artist_id: int) -> list[Album]:
        return self._album_repo.get_by_artist(artist_id)

    def get_all_albums(self) -> list[Album]:
        return self._album_repo.get_all()

    def get_tracks_by_album(self, album_id: int) -> list[Track]:
        return self._track_repo.get_by_album(album_id)

    def get_tracks_by_artist(self, artist_id: int) -> list[Track]:
        return self._track_repo.get_by_artist(artist_id)

    def get_all_tracks(self) -> list[Track]:
        return self._track_repo.get_all()

    def get_recently_added(self, limit: int = 50) -> list[Track]:
        return self._track_repo.get_recently_added(limit)

    def get_most_played(self, limit: int = 25) -> list[Track]:
        return self._track_repo.get_most_played(limit)

    def search(self, query: str) -> dict[str, list]:
        """
        Búsqueda en toda la biblioteca.

        Returns:
            {"artists": [...], "albums": [...], "tracks": [...]}
        """
        return {
            "artists": self._artist_repo.search(query),
            "albums":  self._album_repo.search(query),
            "tracks":  self._track_repo.search(query),
        }
