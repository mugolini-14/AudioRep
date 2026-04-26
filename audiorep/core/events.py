"""
AudioRep — Bus de eventos global.

El singleton `app_events` permite comunicación desacoplada entre capas.
Los services emiten señales; los widgets las escuchan.

Uso:
    from audiorep.core.events import app_events

    # Emitir (desde un service o worker)
    app_events.track_changed.emit(track)

    # Escuchar (desde un widget o controller)
    app_events.track_changed.connect(self._on_track_changed)
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from audiorep.domain.cd_disc import CDDisc
from audiorep.domain.radio_station import RadioStation
from audiorep.domain.track import Track


class _AppEvents(QObject):
    """
    Contenedor de todas las señales globales de la aplicación.
    No instanciar directamente; usar el singleton `app_events`.
    """

    # ------------------------------------------------------------------
    # Reproducción de música local / CD
    # ------------------------------------------------------------------
    track_changed      = pyqtSignal(Track)        # nueva pista en reproducción
    playback_started   = pyqtSignal()
    playback_paused    = pyqtSignal()
    playback_resumed   = pyqtSignal()
    playback_stopped   = pyqtSignal()
    position_changed   = pyqtSignal(int, int)     # (posición_ms, duración_ms)
    track_finished     = pyqtSignal()
    volume_changed     = pyqtSignal(int)          # 0–100
    queue_changed      = pyqtSignal()

    # ------------------------------------------------------------------
    # Biblioteca musical
    # ------------------------------------------------------------------
    library_updated    = pyqtSignal()
    scan_started       = pyqtSignal(str)          # path del directorio
    scan_finished      = pyqtSignal(int)          # cantidad de pistas importadas
    scan_progress      = pyqtSignal(int, int)     # (procesadas, total)

    # ------------------------------------------------------------------
    # CD físico y ripeo
    # ------------------------------------------------------------------
    cd_inserted        = pyqtSignal(str)          # disc_id
    cd_identified      = pyqtSignal(CDDisc)
    cd_ejected         = pyqtSignal()
    rip_progress       = pyqtSignal(int, int, int)  # (pista actual, total, %)
    rip_track_done     = pyqtSignal(int, str)     # (número de pista, ruta archivo)
    rip_track_error    = pyqtSignal(int, str)     # (número de pista, mensaje)
    rip_finished       = pyqtSignal()

    # ------------------------------------------------------------------
    # Radio por internet
    # ------------------------------------------------------------------
    radio_station_changed  = pyqtSignal(RadioStation)  # nueva emisora en reproducción
    radio_stations_updated = pyqtSignal()               # lista de guardadas cambió
    radio_playback_started = pyqtSignal()
    radio_playback_stopped = pyqtSignal()

    # ------------------------------------------------------------------
    # Enriquecimiento de metadatos
    # ------------------------------------------------------------------
    enrichment_started   = pyqtSignal()
    enrichment_progress  = pyqtSignal(int, int)   # (pista_actual, total)
    enrichment_finished  = pyqtSignal(int)         # tracks_actualizados
    enrichment_cancelled = pyqtSignal()
    enrichment_requested = pyqtSignal()            # disparado desde Settings

    # ------------------------------------------------------------------
    # UI general
    # ------------------------------------------------------------------
    status_message     = pyqtSignal(str)
    error_occurred     = pyqtSignal(str, str)     # (título, detalle)


# Singleton global — importar esta instancia, nunca la clase
app_events = _AppEvents()
