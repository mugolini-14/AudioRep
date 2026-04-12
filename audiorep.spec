# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para AudioRep.

Uso (Windows):
    pyinstaller audiorep.spec

Uso (Linux / WSL):
    pyinstaller audiorep.spec --distpath build/linux/dist --workpath build/linux/pyinstaller

Salida Windows: installers/windows/AudioRep/AudioRep.exe
Salida Linux:   build/linux/dist/AudioRep/AudioRep
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

block_cipher = None

# ── Binarios y datos dependientes de la plataforma ───────────────────────────
if sys.platform == "win32":
    VLC_DIR = Path("C:/Program Files/VideoLAN/VLC")
    platform_binaries = [
        (str(VLC_DIR / "libvlc.dll"),     "."),
        (str(VLC_DIR / "libvlccore.dll"), "."),
        (str(ROOT / "build" / "discid.dll"), "."),
    ]
    platform_datas = [
        (str(VLC_DIR / "plugins"), "plugins"),
    ]
else:
    # En Linux las librerías de VLC vienen del sistema (libvlc-dev)
    # PyInstaller las detecta automáticamente via ldd; no hace falta listarlas.
    platform_binaries = []
    platform_datas    = []

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=platform_binaries,
    datas=[
        # Estilos QSS (ambas plataformas)
        (str(ROOT / "audiorep" / "ui" / "style" / "dark.qss"),
         "audiorep/ui/style"),
        *platform_datas,
    ],
    hiddenimports=[
        # PyQt6 — módulos que PyInstaller no detecta automáticamente
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtMultimedia",
        # Backends opcionales (importados con try/except en el código)
        "acoustid",
        "musicbrainzngs",
        "discid",
        "mutagen",
        "mutagen.mp3",
        "mutagen.flac",
        "mutagen.oggvorbis",
        "mutagen.mp4",
        "mutagen.id3",
        "PIL",
        "PIL.Image",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AudioRep",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # sin ventana de consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # TODO: agregar AudioRep.ico cuando esté disponible
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AudioRep",
)
