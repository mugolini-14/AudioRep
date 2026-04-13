"""FileScanner — Implementa ILibraryScanner. Encuentra archivos de audio en un directorio."""
from __future__ import annotations

import logging
from pathlib import Path

from audiorep.core.utils import AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)


class FileScanner:
    """Escanea directorios recursivamente en busca de archivos de audio."""

    def scan(self, directory: str) -> list[str]:
        """Retorna rutas absolutas de todos los archivos de audio encontrados."""
        root = Path(directory)
        if not root.is_dir():
            logger.warning("FileScanner: directorio no encontrado: %s", directory)
            return []
        found = [
            str(p.resolve())
            for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
        ]
        logger.debug("FileScanner: %d archivos en '%s'", len(found), directory)
        return found
