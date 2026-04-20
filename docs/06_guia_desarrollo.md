# AudioRep — Guía de Desarrollo

## Requisitos del Entorno

- Python 3.11 o superior
- VLC Media Player instalado en el sistema (para python-vlc)
- En Windows: unidad lectora de CDs para funciones de CD

---

## Instalación del Entorno de Desarrollo

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd audiorep

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Instalar dependencias (incluye las de dev)
pip install -r requirements.txt

# 5. Ejecutar la aplicación
python main.py
# o bien:
python -m audiorep
```

---

## Ejecutar Tests

```bash
# Todos los tests con cobertura
pytest

# Solo tests unitarios
pytest tests/unit/

# Solo tests de un módulo
pytest tests/unit/domain/test_track.py

# Con reporte de cobertura en HTML
pytest --cov-report=html
```

---

## Linting y Type Checking

```bash
# Lint con ruff
ruff check audiorep/

# Formatear código
ruff format audiorep/

# Type checking con mypy
mypy audiorep/
```

---

## Cómo Agregar un Nuevo Feature

### Ejemplo: agregar soporte para scrobbling a Last.fm

**1. Agregar el cliente en infrastructure/api/**

```python
# audiorep/infrastructure/api/lastfm_client.py
class LastFMClient:
    def scrobble(self, track: Track) -> None: ...
    def update_now_playing(self, track: Track) -> None: ...
```

**2. Definir la interfaz en core/interfaces.py**

```python
class IScrobbler(Protocol):
    def scrobble(self, track: Track) -> None: ...
    def update_now_playing(self, track: Track) -> None: ...
```

**3. Agregar la lógica en el service correspondiente**

```python
# audiorep/services/player_service.py
class PlayerService:
    def __init__(self, ..., scrobbler: IScrobbler | None = None):
        self._scrobbler = scrobbler

    def play_track(self, track: Track) -> None:
        self._player.play(track)
        if self._scrobbler:
            self._scrobbler.update_now_playing(track)
```

**4. Conectar en main.py**

```python
lastfm = LastFMClient(api_key=settings.lastfm_key)
player_service = PlayerService(player=vlc_player, repo=track_repo, scrobbler=lastfm)
```

**5. Agregar configuración en el diálogo de Settings**

---

## Cómo Agregar un Nuevo Widget

1. Crear el archivo en `audiorep/ui/widgets/mi_widget.py`
2. El widget solo conoce el dominio y emite señales; no llama services directamente
3. Crear o actualizar el controller en `audiorep/ui/controllers/`
4. Conectar el widget al controller en `main_window.py`

```python
# El widget emite señales
class MiWidget(QWidget):
    accion_solicitada = pyqtSignal(int)  # track_id

# El controller conecta la señal con el service
class MiController:
    def __init__(self, widget: MiWidget, service: MiService):
        widget.accion_solicitada.connect(self._on_accion)

    def _on_accion(self, track_id: int) -> None:
        self._service.hacer_algo(track_id)
```

---

## Pasos de Implementación del Proyecto

| Paso | Módulos | Estado |
|---|---|---|
| 1 | `domain/`, `core/` | ✅ Completo |
| 2 | `infrastructure/database/` | ✅ Completo |
| 3 | `infrastructure/audio/vlc_player.py`, `services/player_service.py` | ✅ Completo |
| 4 | UI mínima: `main_window.py`, `player_bar.py`, `PlayerController` | ✅ Completo |
| 5 | `infrastructure/filesystem/`, `services/library_service.py` | ✅ Completo |
| 6 | `infrastructure/api/musicbrainz_client.py`, `services/cd_service.py` | ✅ Completo |
| 7 | `services/ripper_service.py` | ✅ Completo |
| 8 | Tags automáticos: `tagger_service.py`, `acoustid_client.py` | ✅ Completo |
| 9 | `playlist_service.py`, `PlaylistPanel`, `PlaylistController`, smart playlists | ✅ Completo |
| 10 | `AppSettings`, `SettingsDialog`, menú, tema QSS completo | ✅ Completo — v0.10 |
| 11 | Radio por internet: `radio_browser_client.py`, `RadioService`, `RadioPanel` | ✅ Completo — v0.20 |
| 12 | UI v0.25: pestañas, controles, CD multi-lectora, VU meter, NowPlaying | ✅ Completo — v0.25 |
| 13 | CD fix: CDDA URIs, GnuDB, panel de metadatos manual (`CDMetadataPanel`) | ✅ Completo — v0.30 |
| 14 | VU metro real (PCM vía sounddevice), tabla CD con cabeceras | ✅ Completo — v0.35 |
| 15 | `RadioResultsTable`, CD sin portada inline, `PlayerBar` barra tiempo + volumen | ✅ Completo — v0.40 |
| 16 | Fix crash radio, fix tema QSS en listas CD | ✅ Completo — v0.40 |
| 17 | `RadioSavedTable` (tabla), fix volumen inicial en `PlayerController` | ✅ Completo — v0.42 |
| 18 | Filtros en las 3 sub-tabs de Radio, `RadioFavsTable`, fix volumen PCM callback | ✅ Completo — v0.44 |
| 19 | Fix hover menú (`QMenuBar`/`QMenu` QSS), mute toggle en ícono de volumen | ✅ Completo — v0.46 |
| 20 | Números de tiempo de reproducción más grandes (font-size 16px, fixedWidth 52px) | ✅ Completo — v0.47 |
| 21 | Rediseño pestaña CD: fila única lectora+estado+info, tabla más alta, botones a ancho completo | ✅ Completo — v0.48 |
| 22 | Estandarización de todos los botones de acción, fix alineación botón play (46×46) | ✅ Completo — v0.49 |
| 23 | Dropdowns unificados (QComboBox global + arrow_down.svg), refactor performance reproductor | ✅ Completo — v0.50 |
| 24 | Hilo RMS dedicado (`_RMSAnalyzer`), backpressure con log de underruns en `_SDAudioBridge` | ✅ Completo — v0.51 |
| 25 | Columnas ordenables en Biblioteca (`TrackTableModel.sort()` + `setSortingEnabled`) | ✅ Completo — v0.52 |
| 26 | Columnas ordenables en Playlists; fix doble-clic siempre reproducía desde pista 1 | ✅ Completo — v0.53–v0.54 |
| 27 | Columnas ordenables en Radio (Buscar, Guardadas, Favoritas); `_BitrateItem` para orden numérico | ✅ Completo — v0.54–v0.56 |
| 28 | `trackLabel` 16px en PlayerBar; botones de transporte sin highlight de foco (NoFocus) | ✅ Completo — v0.56–v0.57 |
| 29 | NowPlaying: campo año, campos opcionales con `setVisible`, portada limpia al cambiar pista | ✅ Completo — v0.57 |
| 30 | Estándar de diálogos modales: QLineEdit global, QDialogButtonBox, "Sí"/"No" en confirmaciones | ✅ Completo — v0.58 |
| 31 | Título de ventana estático; Play tras Stop reproduce última pista (`replay_current()`) | ✅ Completo — v0.59 |

---

## Convenciones de Código

- **Estilo**: PEP 8, máximo 100 caracteres por línea (ruff)
- **Tipos**: Usar type hints en todas las funciones públicas
- **Docstrings**: Solo en clases y funciones públicas no triviales
- **Tests**: Cada service debe tener tests unitarios con mocks de sus dependencias
- **Commits**: `tipo(módulo): descripción` — ej. `feat(player): agregar soporte de gapless`
