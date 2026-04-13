"""FileOrganizer — Mueve y renombra archivos de audio según sus tags."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from audiorep.core.utils import ensure_dir, safe_filename
from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Organiza archivos en la estructura Artista/Álbum/NN - Título."""

    def organize(self, track: Track, base_dir: str) -> str | None:
        """Mueve el archivo de la pista a la estructura organizada. Retorna la nueva ruta."""
        if not track.file_path or not Path(track.file_path).exists():
            return None
        artist = safe_filename(track.artist_name or "Desconocido")
        album = safe_filename(track.album_title or "Sin álbum")
        ext = Path(track.file_path).suffix
        title = safe_filename(track.title or "Sin título")
        filename = f"{track.track_number:02d} - {title}{ext}"
        dest_dir = ensure_dir(Path(base_dir) / artist / album)
        dest = dest_dir / filename
        if Path(track.file_path) == dest:
            return str(dest)
        shutil.move(track.file_path, dest)
        logger.info("FileOrganizer: '%s' → '%s'", track.file_path, dest)
        return str(dest)
