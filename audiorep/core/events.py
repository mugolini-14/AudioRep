"""
Bus de eventos global de AudioRep.

Utiliza señales de PyQt6 para comunicación desacoplada entre
servicios y la interfaz gráfica. Es un singleton: se importa
la instancia `app_events` en lugar de la clase.

Uso típico:
    # Emitir desde un service:
    from audiorep.core.events import app_events
    app_events.track_changed.emit(track)

    # Conectar desde un widget:
    from audiorep.core.events import app_events
    app_events.track_changed.connect(self._on_track_changed)
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from audiorep.domain.track import Track
from audiorep.domain.cd_disc import CDDisc


class _AppEvents(QObject):
    """
    Señales globales de la aplicación.

    Categorías:
        - Reproducción
        - Biblioteca
        - CD / Ripeo
        - UI general
    """

    # ------------------------------------------------------------------
    # Reproducción
    # ------------------------------------------------------------------

    # Se emite cuando la pista en reproducción cambia
    track_changed = pyqtSignal(Track)

    # Se emite cuando la reproducción arranca / pausa / reanuda / detiene
    playback_started = pyqtSignal()
    playback_paused  = pyqtSignal()
    playback_resumed = pyqtSignal()
    playback_stopped = pyqtSignal()

    # Se emite periódicamente con la posición actual (ms) y la duración (ms)
    position_changed = pyqtSignal(int, int)

    # Se emite cuando termina de reproducirse la pista actual
    track_finished = pyqtSignal()

    # Cambio de volumen (0–100)
    volume_changed = pyqtSignal(int)

    # ------------------------------------------------------------------
    # Biblioteca
    # ------------------------------------------------------------------

    # La biblioteca fue modificada (pistas agregadas, tags actualizados, etc.)
    library_updated = pyqtSignal()

    # Se inició / terminó un escaneo de directorio
    scan_started   = pyqtSignal(str)        # path escaneado
    scan_finished  = pyqtSignal(int)        # cantidad de pistas encontradas
    scan_progress  = pyqtSignal(int, int)   # (pistas procesadas, total)

    # ------------------------------------------------------------------
    # CD
    # ------------------------------------------------------------------

    # CD insertado: disc_id como string
    cd_inserted = pyqtSignal(str)

    # CD identificado online: objeto CDDisc con metadatos completos
    cd_identified = pyqtSignal(CDDisc)

    # CD eyectado / removido
    cd_ejected = pyqtSignal()

    # Progreso del ripeo: (pista actual, total de pistas, porcentaje de la pista)
    rip_progress  = pyqtSignal(int, int, int)

    # Una pista de CD fue ripeada correctamente (número de pista, ruta del archivo)
    rip_track_done  = pyqtSignal(int, str)

    # Error durante el ripeo (número de pista, mensaje de error)
    rip_track_error = pyqtSignal(int, str)

    # Ripeo completo finalizado
    rip_finished = pyqtSignal()

    # ------------------------------------------------------------------
    # UI general
    # ------------------------------------------------------------------

    # Solicita mostrar un mensaje de estado en la barra inferior
    status_message = pyqtSignal(str)

    # Solicita mostrar un error crítico al usuario
    error_occurred = pyqtSignal(str, str)   # (título, detalle)


# Singleton: importar esta instancia en toda la aplicación
app_events = _AppEvents()
