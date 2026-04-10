"""
Utilidades generales de AudioRep.

Funciones puras reutilizables en cualquier capa del proyecto.
No importan nada de infrastructure ni de UI.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Extensiones de audio reconocidas por la aplicación
AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".flac", ".ogg", ".opus", ".aac",
    ".m4a", ".wma", ".wav", ".ape", ".mpc",
})


def is_audio_file(path: str | Path) -> bool:
    """Retorna True si la extensión corresponde a un formato de audio soportado."""
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def format_duration(duration_ms: int) -> str:
    """
    Convierte milisegundos a cadena legible.

    Ejemplos:
        3_661_000 ms → "1:01:01"
          183_000 ms → "3:03"
    """
    total_seconds = duration_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_file_size(size_bytes: int) -> str:
    """
    Convierte bytes a cadena legible.

    Ejemplos:
        1_048_576 → "1.0 MB"
          102_400 → "100.0 KB"
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} TB"


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """
    Elimina caracteres inválidos en nombres de archivo/directorio.

    Args:
        name:        Nombre a sanitizar.
        replacement: Caracter de reemplazo (por defecto '_').
    """
    # Caracteres prohibidos en Windows y Linux
    invalid = r'[\\/:*?"<>|]'
    sanitized = re.sub(invalid, replacement, name)
    # Eliminar puntos/espacios al inicio o final
    return sanitized.strip(". ")


def build_track_path(
    base_dir: str,
    artist: str,
    album: str,
    track_number: int,
    title: str,
    ext: str = "flac",
) -> Path:
    """
    Construye la ruta destino para un archivo de audio ripeado o importado,
    siguiendo la convención: base_dir/Artist/Album/NN - Title.ext

    Args:
        base_dir:     Directorio raíz de la biblioteca.
        artist:       Nombre del artista.
        album:        Título del álbum.
        track_number: Número de pista.
        title:        Título de la pista.
        ext:          Extensión sin punto (ej. "flac", "mp3").
    """
    artist_dir = sanitize_filename(artist) or "Desconocido"
    album_dir  = sanitize_filename(album)  or "Sin álbum"
    filename   = f"{track_number:02d} - {sanitize_filename(title)}.{ext}"
    return Path(base_dir) / artist_dir / album_dir / filename


def file_md5(file_path: str | Path, chunk_size: int = 65536) -> str:
    """
    Calcula el MD5 de un archivo (para detección de duplicados).

    Args:
        file_path:  Ruta al archivo.
        chunk_size: Tamaño del bloque de lectura en bytes.
    """
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def clamp(value: int | float, min_val: int | float, max_val: int | float) -> int | float:
    """Limita un valor al rango [min_val, max_val]."""
    return max(min_val, min(value, max_val))
