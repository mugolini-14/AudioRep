# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
python main.py
# or:
python -m audiorep

# Run all tests
pytest

# Run a single test file
pytest tests/unit/services/test_player_service.py

# Lint
ruff check audiorep/

# Format
ruff format audiorep/

# Type check
mypy audiorep/
```

## Architecture

AudioRep follows **Clean Architecture** with strict one-way dependency flow:

```
domain → core → services ← infrastructure
                    ↑
                   UI (controllers → widgets)
```

- **`domain/`** — Pure dataclasses (`Track`, `Album`, `Artist`, `Playlist`, `CDDisc`). No dependencies on anything else.
- **`core/interfaces.py`** — `Protocol`-based contracts (e.g., `IAudioPlayer`, `ITrackRepository`, `IMetadataProvider`). Services import *only* from here, never from `infrastructure/`.
- **`core/events.py`** — Global singleton `app_events` (`_AppEvents(QObject)`). Used for 1-to-many broadcast across layers (services emit, widgets connect). Import the instance, not the class.
- **`core/settings.py`** — `AppSettings` wraps `QSettings` (Windows registry). Typed properties for `acoustid_api_key`, `ripper_format`, `ripper_output_dir`, `theme`.
- **`services/`** — Business logic. Each service is a `QObject`. Long-running operations (import, rip, fingerprint) are delegated to inner `QThread` worker classes defined in the same file.
- **`infrastructure/`** — Concrete implementations of core interfaces. Never imported by services directly — only injected via `main.py`.
- **`ui/widgets/`** — Pure PyQt6 widgets. Emit signals, never call services. Know only domain objects.
- **`ui/controllers/`** — Connect widget signals to service calls. One controller per feature area.
- **`ui/dialogs/`** — Modal dialogs (`RipperDialog`, `TagEditorDialog`, `SettingsDialog`).
- **`ui/style/dark.qss`** — All visual styling via Qt object names. No inline styles.
- **`main.py`** — Composition root. All dependency injection happens here. No business logic.

## Key conventions

**Dependency injection**: Everything is wired in `main.py`. Services receive infrastructure objects through their constructors; controllers receive services and widgets. Never instantiate infrastructure inside a service.

**Threading**: All blocking operations use an inner `_XxxWorker(QThread)` class inside the service file. Workers emit signals back to the service; the service re-emits as `app_events`. UI never starts threads directly.

**Repository pattern**: `infrastructure/database/repositories/` implement the `IXxxRepository` protocols. SQLite via a raw `DatabaseConnection` (no ORM). The `get_or_create` pattern is used for artists and albums during import.

**Widget signals are the API**: Widgets expose named `pyqtSignal`s at the top of the class. Controllers connect these signals in their `__init__`. Widgets never import controllers or services.

**objectName for QSS**: Every styled widget has `setObjectName(...)` called. All styles are in `dark.qss` targeting those names. When adding new widgets, always assign an `objectName` and add the corresponding QSS rule.

**Action button standard**: All action buttons (below tables/lists in every panel) must follow this unified style:
- **QSS**: `background-color: #4a3480; color: #ffffff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: bold;` — hover: `#5a409a` — disabled: bg `#252538` color `#55557a`.
- **Layout**: use `btn_row.addWidget(btn, stretch=1)` (equal-width distribution). Never use `setSizePolicy(Expanding, Fixed)` on action buttons.
- **Container margins**: `setContentsMargins(8, 8, 8, 8)` and `setSpacing(8)` for the `QHBoxLayout` that holds the buttons. The outer panel layout must provide at least 8px bottom margin so buttons don't appear flush against the window edge.

## Building installers

These steps must be run **after every feature release** (version bump in `pyproject.toml` + `main.py` + both `setWindowTitle` calls in `main_window.py`).

### Windows (.exe — directory bundle)

Requires all project dependencies installed in the active Python environment:

```bash
pip install -r requirements.txt
pip install pyinstaller

pyinstaller audiorep.spec \
    --distpath installers/windows \
    --workpath build/pyinstaller \
    --noconfirm
```

Output: `installers/windows/AudioRep/AudioRep.exe` + `_internal/` (~202 MB, VLC included).  
The bundle includes `libvlc.dll`, `libvlccore.dll` and the VLC `plugins/` directory — no external VLC installation required on the end user's machine.  
**Requirement:** VLC must be installed on the **build machine** at `C:/Program Files/VideoLAN/VLC/` so the DLLs can be copied into the bundle.

### Linux (.deb — Debian / Ubuntu)

Must be run on a Linux system or WSL2 (cannot be cross-compiled from Windows without WSL):

```bash
bash installers/linux/build_deb.sh
```

Output: `installers/linux/audiorep_<version>_amd64.deb`.  
Full instructions: `installers/linux/README.txt`.

### Data directory (frozen vs. source)

`main.py` detects `sys.frozen` to pick the right data path:
- **Frozen (bundle):** `%APPDATA%\AudioRep\` on Windows, `~/.local/share/AudioRep/` on Linux
- **Source:** `project/data/`

This affects `audiorep.db` and the cover art cache. No changes needed when adding new features — the logic is already in place.

### Version bump checklist (do this before building)

1. `pyproject.toml` → `version = "X.Y.Z"`
2. `main.py` → `app.setApplicationVersion("X.Y.Z")`
3. `audiorep/ui/main_window.py` → both `setWindowTitle` calls → `"AudioRep X.Y"`

## System dependencies

- **VLC Media Player** must be installed (used by `python-vlc` for both playback and CD ripping via `sout` transcoding).
- **fpcalc** (chromaprint) must be in PATH for AcoustID fingerprinting (`pyacoustid` uses it as a subprocess).
- **AcoustID API key**: stored in `QSettings`. Seed it via `_ACOUSTID_KEY_SEED` in `main.py` on first run, or enter it through *Archivo → Configuración*.

