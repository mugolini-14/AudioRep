# AudioRep — Bus de Eventos

## Descripción

AudioRep utiliza un **bus de eventos global** implementado con señales de PyQt6.
El singleton `app_events` (instancia de `_AppEvents`) permite que cualquier
componente emita o escuche eventos sin acoplarse directamente al emisor.

Archivo: `audiorep/core/events.py`

---

## Uso

```python
# Emitir un evento (desde un Service)
from audiorep.core.events import app_events
app_events.track_changed.emit(track)

# Escuchar un evento (desde un Widget)
from audiorep.core.events import app_events
app_events.track_changed.connect(self._on_track_changed)
```

---

## Catálogo de Señales

### Reproducción

| Señal | Argumentos | Cuándo se emite |
|---|---|---|
| `track_changed` | `Track` | Cambia la pista en reproducción |
| `playback_started` | — | Arranca la reproducción |
| `playback_paused` | — | Se pausa |
| `playback_resumed` | — | Se reanuda desde pausa |
| `playback_stopped` | — | Se detiene completamente |
| `position_changed` | `(int, int)` | Cada ~500ms: (posición_ms, duración_ms) |
| `track_finished` | — | La pista terminó naturalmente |
| `volume_changed` | `int` | Cambio de volumen (0–100) |

### Biblioteca

| Señal | Argumentos | Cuándo se emite |
|---|---|---|
| `library_updated` | — | Se agregan, modifican o eliminan pistas |
| `scan_started` | `str` (path) | Inicia escaneo de directorio |
| `scan_finished` | `int` (cant.) | Escaneo completado |
| `scan_progress` | `(int, int)` | Progreso: (procesadas, total) |

### CD y Ripeo

| Señal | Argumentos | Cuándo se emite |
|---|---|---|
| `cd_inserted` | `str` (disc_id) | Se detecta un CD en la lectora |
| `cd_identified` | `CDDisc` | El disco fue reconocido online |
| `cd_ejected` | — | CD removido de la unidad |
| `rip_progress` | `(int, int, int)` | (pista actual, total, % de la pista) |
| `rip_track_done` | `(int, str)` | (número de pista, ruta del archivo) |
| `rip_track_error` | `(int, str)` | (número de pista, mensaje de error) |
| `rip_finished` | — | Ripeo completo finalizado |

### Radio por Internet

| Señal | Argumentos | Cuándo se emite |
|---|---|---|
| `radio_station_changed` | `RadioStation` | Cambia la emisora en reproducción |
| `radio_stations_updated` | — | Se guarda, elimina o modifica una emisora |
| `radio_playback_started` | — | Comienza la reproducción de una emisora |
| `radio_playback_stopped` | — | Se detiene la reproducción de radio |

### UI General

| Señal | Argumentos | Cuándo se emite |
|---|---|---|
| `status_message` | `str` | Mensaje para la barra de estado |
| `error_occurred` | `(str, str)` | (título, detalle del error) |

---

## Diagrama de Flujo de Eventos

```
VLCPlayer ──────→ app_events.position_changed ──────→ PlayerBar (barra de progreso)
                                                  └──→ NowPlaying (tiempo restante)

CDReader ────────→ app_events.cd_inserted ──────────→ CDPanel (muestra pistas)
                       │
CDService ─────────────→ app_events.cd_identified ──→ CDPanel (muestra metadatos)

RipperService ──────→ app_events.rip_progress ──────→ RipperDialog (barra de progreso)
              └─────→ app_events.rip_track_done ────→ CDPanel (marca pista como ripeada)
```

---

## Consideraciones

- **Thread safety**: Los services pueden correr en hilos secundarios (QThread).
  Las señales de PyQt6 son thread-safe cuando se conectan entre hilos diferentes
  usando `Qt.ConnectionType.QueuedConnection`.
- **No abusar del bus**: Las señales son para comunicación 1-a-muchos o
  entre capas no acopladas. La comunicación directa service→service se hace
  mediante llamadas a métodos normales.
