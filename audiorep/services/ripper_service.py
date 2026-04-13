"""
RipperService — Ripeo de CDs a archivos de audio.

Responsabilidades:
    - Delegar el ripeo al ICDRipper en un worker thread.
    - Emitir progreso vía app_events.
    - Importar las pistas ripeadas a la biblioteca.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.core.events import app_events
from audiorep.core.interfaces import ICDRipper, IFileTagger
from audiorep.domain.cd_disc import CDDisc, RipStatus
from audiorep.services.library_service import LibraryService

logger = logging.getLogger(__name__)


class _RipWorker(QThread):
    """Worker de ripeo. Ejecuta el ripeo de todas las pistas."""

    progress    = pyqtSignal(int, int, int)  # (pista, total, %)
    track_done  = pyqtSignal(int, str)       # (número de pista, ruta)
    track_error = pyqtSignal(int, str)       # (número de pista, mensaje)
    finished    = pyqtSignal()

    def __init__(
        self,
        ripper: ICDRipper,
        disc: CDDisc,
        output_dir: str,
        fmt: str,
        track_numbers: list[int] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._ripper        = ripper
        self._disc          = disc
        self._output_dir    = output_dir
        self._fmt           = fmt
        self._track_numbers = track_numbers  # None = todas

    def run(self) -> None:
        tracks = self._disc.tracks
        if self._track_numbers is not None:
            tracks = [t for t in tracks if t.number in self._track_numbers]
        total = len(tracks)
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        for i, cd_track in enumerate(tracks):
            try:
                safe_title = "".join(
                    c if c.isalnum() or c in " ._-" else "_"
                    for c in (cd_track.title or f"track{cd_track.number:02d}")
                )
                filename = f"{cd_track.number:02d}-{safe_title}.{self._fmt}"
                out_path = str(Path(self._output_dir) / filename)
                self.progress.emit(i + 1, total, 0)
                self._ripper.rip_track(
                    disc=self._disc,
                    track_number=cd_track.number,
                    output_path=out_path,
                    format=self._fmt,
                )
                self.progress.emit(i + 1, total, 100)
                self.track_done.emit(cd_track.number, out_path)
                cd_track.file_path = out_path
                cd_track.rip_status = RipStatus.DONE
            except Exception as exc:
                logger.error("Error ripeando pista %d: %s", cd_track.number, exc)
                self.track_error.emit(cd_track.number, str(exc))
                cd_track.rip_status = RipStatus.ERROR
        self.finished.emit()


class RipperService(QObject):
    """
    Servicio de ripeo de CD.

    Args:
        ripper:          Implementación de ICDRipper.
        tagger:          Tagger para escribir metadatos post-ripeo.
        library_service: Servicio de biblioteca para importar pistas ripeadas.
    """

    def __init__(
        self,
        ripper: ICDRipper,
        tagger: IFileTagger,
        library_service: LibraryService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._ripper  = ripper
        self._tagger  = tagger
        self._library = library_service
        self._worker: _RipWorker | None = None

    def rip_all(self, disc: CDDisc, output_dir: str, fmt: str = "flac") -> None:
        self._start_worker(disc, output_dir, fmt, track_numbers=None)

    def rip_track(
        self,
        disc: CDDisc,
        track_number: int,
        output_dir: str,
        fmt: str = "flac",
    ) -> None:
        self._start_worker(disc, output_dir, fmt, track_numbers=[track_number])

    def _start_worker(
        self,
        disc: CDDisc,
        output_dir: str,
        fmt: str,
        track_numbers: list[int] | None,
    ) -> None:
        if self._worker and self._worker.isRunning():
            logger.warning("Ya hay un ripeo en progreso.")
            return
        self._worker = _RipWorker(
            ripper=self._ripper,
            disc=disc,
            output_dir=output_dir,
            fmt=fmt,
            track_numbers=track_numbers,
            parent=self,
        )
        self._worker.progress.connect(
            lambda cur, tot, pct: app_events.rip_progress.emit(cur, tot, pct)
        )
        self._worker.track_done.connect(
            lambda num, path: app_events.rip_track_done.emit(num, path)
        )
        self._worker.track_error.connect(
            lambda num, msg: app_events.rip_track_error.emit(num, msg)
        )
        self._worker.finished.connect(self._on_rip_finished)
        self._worker.start()

    def _on_rip_finished(self) -> None:
        app_events.rip_finished.emit()
        logger.info("Ripeo terminado.")
