"""
RadioStation — Entidad de dominio que representa una emisora de radio.

Una emisora puede ser:
  - Encontrada via búsqueda en radio-browser.info y guardada por el usuario.
  - Creada manualmente por el usuario con una URL de stream propia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RadioStation:
    """
    Emisora de radio (stream de internet).

    Attributes:
        id:          ID interno en la base de datos (None si no persistida).
        name:        Nombre de la emisora.
        stream_url:  URL del stream de audio (HTTP/HTTPS, M3U, PLS, etc.).
        country:     País de origen (código ISO o nombre completo).
        genre:       Género o categoría principal (ej. "Rock", "Noticias").
        logo_url:    URL del logo/ícono de la emisora (puede estar vacía).
        is_favorite: True si el usuario la marcó como favorita.
        added_at:    Fecha y hora en que fue guardada.
        bitrate_kbps: Bitrate del stream en kbps (0 si desconocido).
        radio_browser_id: UUID de la emisora en radio-browser.info (vacío si es manual).
    """

    name:             str
    stream_url:       str
    country:          str               = ""
    genre:            str               = ""
    logo_url:         str               = ""
    is_favorite:      bool              = False
    added_at:         datetime          = field(default_factory=datetime.now)
    bitrate_kbps:     int               = 0
    radio_browser_id: str               = ""
    id:               int | None        = None

    def __str__(self) -> str:
        return self.name
