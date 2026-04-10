"""
Excepciones de dominio de AudioRep.

Jerarquía:
    AudioRepError
    ├── PlayerError
    │   ├── TrackNotAvailableError
    │   └── PlayerBackendError
    ├── LibraryError
    │   ├── TrackNotFoundError
    │   └── DuplicateTrackError
    ├── CDError
    │   ├── NoCDInsertedError
    │   ├── CDReadError
    │   └── CDIdentificationError
    ├── RipperError
    ├── TaggerError
    └── APIError
        ├── APIConnectionError
        └── APIRateLimitError
"""


class AudioRepError(Exception):
    """Base de todas las excepciones de AudioRep."""


# ------------------------------------------------------------------
# Player
# ------------------------------------------------------------------

class PlayerError(AudioRepError):
    """Error relacionado con la reproducción de audio."""


class TrackNotAvailableError(PlayerError):
    """La pista no se puede reproducir (archivo inexistente o CD ausente)."""
    def __init__(self, track_title: str) -> None:
        super().__init__(f"La pista '{track_title}' no está disponible.")
        self.track_title = track_title


class PlayerBackendError(PlayerError):
    """Error interno del backend de reproducción (VLC u otro)."""


# ------------------------------------------------------------------
# Library
# ------------------------------------------------------------------

class LibraryError(AudioRepError):
    """Error relacionado con la gestión de la biblioteca."""


class TrackNotFoundError(LibraryError):
    """No se encontró una pista con el ID o criterio dado."""
    def __init__(self, track_id: int) -> None:
        super().__init__(f"No se encontró la pista con id={track_id}.")
        self.track_id = track_id


class DuplicateTrackError(LibraryError):
    """Se intentó agregar una pista que ya existe en la biblioteca."""
    def __init__(self, file_path: str) -> None:
        super().__init__(f"La pista ya existe en la biblioteca: {file_path}")
        self.file_path = file_path


# ------------------------------------------------------------------
# CD
# ------------------------------------------------------------------

class CDError(AudioRepError):
    """Error relacionado con operaciones de CD."""


class NoCDInsertedError(CDError):
    """No hay ningún CD en la unidad lectora."""
    def __init__(self) -> None:
        super().__init__("No hay ningún CD insertado en la unidad lectora.")


class CDReadError(CDError):
    """Error al leer el CD (disco dañado, unidad sin permisos, etc.)."""


class CDIdentificationError(CDError):
    """No se pudo identificar el disco en ningún servicio online."""
    def __init__(self, disc_id: str) -> None:
        super().__init__(f"No se pudo identificar el disco con Disc ID: {disc_id}")
        self.disc_id = disc_id


# ------------------------------------------------------------------
# Ripper
# ------------------------------------------------------------------

class RipperError(AudioRepError):
    """Error durante el proceso de ripeo de CD."""


# ------------------------------------------------------------------
# Tagger
# ------------------------------------------------------------------

class TaggerError(AudioRepError):
    """Error al leer o escribir tags en un archivo de audio."""


# ------------------------------------------------------------------
# API / Servicios externos
# ------------------------------------------------------------------

class APIError(AudioRepError):
    """Error al comunicarse con una API externa."""


class APIConnectionError(APIError):
    """No se pudo conectar al servicio externo."""
    def __init__(self, service: str) -> None:
        super().__init__(f"No se pudo conectar al servicio: {service}")
        self.service = service


class APIRateLimitError(APIError):
    """Se superó el límite de peticiones al servicio externo."""
    def __init__(self, service: str, retry_after_seconds: int = 0) -> None:
        msg = f"Límite de peticiones alcanzado en {service}."
        if retry_after_seconds:
            msg += f" Reintentar en {retry_after_seconds}s."
        super().__init__(msg)
        self.service = service
        self.retry_after_seconds = retry_after_seconds
