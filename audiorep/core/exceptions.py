"""AudioRep — Jerarquía de excepciones del dominio."""
from __future__ import annotations


class AudioRepError(Exception):
    """Excepción base de AudioRep."""


class PlayerError(AudioRepError):
    """Error en la reproducción de audio."""


class LibraryError(AudioRepError):
    """Error en la biblioteca musical."""


class CDError(AudioRepError):
    """Error relacionado con el CD físico."""


class RipperError(AudioRepError):
    """Error durante el ripeo de CD."""


class TaggerError(AudioRepError):
    """Error al leer o escribir tags."""


class MetadataError(AudioRepError):
    """Error al obtener metadatos online."""


class DatabaseError(AudioRepError):
    """Error de acceso a la base de datos."""


class RadioError(AudioRepError):
    """Error en la reproducción de radio."""
