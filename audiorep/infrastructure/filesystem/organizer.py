"""
FileOrganizer — Organiza archivos de audio en directorios según sus tags.

Convención de directorios:
    base_dir / Artist / Album / NN - Title.ext

No implementa una interfaz formal porque es un servicio de soporte
que el LibraryService (y el futuro TaggerService) usan directamente.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from audiorep.core.utils import build_track_path, sanitize_filename
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    Mueve o copia archivos de audio a una estructura de directorios
    organizada por Artista / Álbum.

    Args:
        base_dir: Directorio raíz de la biblioteca organizada.
        copy:     Si True, copia el archivo (conserva el original).
                  Si False (por defecto), mueve el archivo.
    """

    def __init__(self, base_dir: str, copy: bool = False) -> None:
        self._base_dir = Path(base_dir)
        self._copy = copy

    def organize(self, track: Track) -> str | None:
        """
        Mueve o copia el archivo de la pista al directorio correspondiente.

        Returns:
            Nueva ruta del archivo, o None si el archivo ya está en su lugar
            o no se pudo organizar.

        Raises:
            OSError: si hay un error de sistema de archivos.
        """
        if not track.file_path:
            logger.warning("La pista '%s' no tiene ruta de archivo.", track.title)
            return None

        src = Path(track.file_path)
        if not src.exists():
            logger.warning("Archivo no encontrado: %s", src)
            return None

        ext = src.suffix.lstrip(".")
        dest = build_track_path(
            base_dir=str(self._base_dir),
            artist=track.artist_name or "Desconocido",
            album=track.album_title or "Sin álbum",
            track_number=track.track_number,
            title=track.title,
            ext=ext,
        )

        # Ya está en el lugar correcto
        if src.resolve() == dest.resolve():
            return None

        dest.parent.mkdir(parents=True, exist_ok=True)

        # Evitar sobreescribir si ya existe
        if dest.exists():
            dest = self._unique_path(dest)

        if self._copy:
            shutil.copy2(src, dest)
            logger.info("Copiado: %s → %s", src.name, dest)
        else:
            shutil.move(str(src), dest)
            logger.info("Movido: %s → %s", src.name, dest)

        return str(dest)

    def organize_many(self, tracks: list[Track]) -> dict[int, str]:
        """
        Organiza una lista de pistas.

        Returns:
            Dict {track_id: nueva_ruta} para las pistas que fueron movidas.
        """
        result: dict[int, str] = {}
        for track in tracks:
            if track.id is None:
                continue
            try:
                new_path = self.organize(track)
                if new_path:
                    result[track.id] = new_path
            except OSError as exc:
                logger.error("Error al organizar '%s': %s", track.title, exc)
        return result

    @staticmethod
    def _unique_path(path: Path) -> Path:
        """Agrega un sufijo numérico si la ruta ya existe: file (2).flac"""
        stem   = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 2
        while path.exists():
            path = parent / f"{stem} ({counter}){suffix}"
            counter += 1
        return path
