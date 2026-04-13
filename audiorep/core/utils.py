"""AudioRep — Funciones utilitarias puras."""
from __future__ import annotations

import os
from pathlib import Path


AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".opus", ".aac", ".m4a",
    ".wav", ".wma", ".ape", ".mpc",
}


def is_audio_file(path: str | Path) -> bool:
    """Retorna True si la ruta tiene extensión de audio soportada."""
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def ms_to_str(ms: int) -> str:
    """Convierte milisegundos a string 'MM:SS'."""
    total_s = max(0, ms) // 1000
    return f"{total_s // 60}:{total_s % 60:02d}"


def safe_filename(name: str) -> str:
    """Sanitiza un string para usarlo como nombre de archivo."""
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name.strip(". ")


def ensure_dir(path: str | Path) -> Path:
    """Crea el directorio (y padres) si no existe. Retorna el Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
