"""
FileScanner — Escáner de directorios de audio.

Implementa ILibraryScanner.
Recorre un directorio recursivamente y devuelve las rutas absolutas
de todos los archivos de audio reconocidos.
"""
from __future__ import annotations

import os
import logging
from pathlib import Path

from audiorep.core.utils import AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)


class FileScanner:
    """
    Escáner de sistema de archivos para archivos de audio.

    Implementa ILibraryScanner.
    """

    def scan(self, directory: str) -> list[str]:
        """
        Recorre `directory` recursivamente y retorna las rutas absolutas
        de todos los archivos de audio soportados.

        Args:
            directory: Ruta al directorio raíz a escanear.

        Returns:
            Lista de rutas absolutas ordenadas por (artista, álbum, pista).
        """
        root = Path(directory)
        if not root.is_dir():
            logger.warning("El directorio no existe o no es válido: %s", directory)
            return []

        found: list[str] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in filenames:
                if Path(fname).suffix.lower() in AUDIO_EXTENSIONS:
                    found.append(str(Path(dirpath) / fname))

        found.sort()
        logger.debug("Escáner: %d archivos encontrados en '%s'.", len(found), directory)
        return found

    def scan_multiple(self, directories: list[str]) -> list[str]:
        """Escanea múltiples directorios y devuelve todas las rutas sin duplicados."""
        seen: set[str] = set()
        result: list[str] = []
        for directory in directories:
            for path in self.scan(directory):
                if path not in seen:
                    seen.add(path)
                    result.append(path)
        return result
