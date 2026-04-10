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
| 2 | `infrastructure/database/` | ⬜ Pendiente |
| 3 | `infrastructure/audio/vlc_player.py`, `services/player_service.py` | ⬜ Pendiente |
| 4 | UI mínima: `main_window.py`, `player_bar.py`, `PlayerController` | ⬜ Pendiente |
| 5 | `infrastructure/filesystem/`, `services/library_service.py` | ⬜ Pendiente |
| 6 | `infrastructure/api/musicbrainz_client.py`, `services/cd_service.py` | ⬜ Pendiente |
| 7 | `services/ripper_service.py` | ⬜ Pendiente |
| 8 | Tags automáticos: `tagger_service.py`, `acoustid_client.py` | ⬜ Pendiente |
| 9 | Playlists, búsqueda, smart playlists | ⬜ Pendiente |
| 10 | Temas visuales, settings, pulido general | ⬜ Pendiente |

---

## Convenciones de Código

- **Estilo**: PEP 8, máximo 100 caracteres por línea (ruff)
- **Tipos**: Usar type hints en todas las funciones públicas
- **Docstrings**: Solo en clases y funciones públicas no triviales
- **Tests**: Cada service debe tener tests unitarios con mocks de sus dependencias
- **Commits**: `tipo(módulo): descripción` — ej. `feat(player): agregar soporte de gapless`
