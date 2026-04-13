"""
AudioRep — Configuración persistente de la aplicación.

Envuelve QSettings (registro de Windows / archivo en Linux).
Todos los ajustes se acceden como propiedades tipadas.
"""
from __future__ import annotations

from PyQt6.QtCore import QSettings


class AppSettings:
    """
    Configuración persistente de AudioRep.

    Usa QSettings con organización "AudioRep" y aplicación "AudioRep".
    """

    def __init__(self) -> None:
        self._qs = QSettings("AudioRep", "AudioRep")

    # ── AcoustID ──────────────────────────────────────────────────────

    @property
    def acoustid_api_key(self) -> str:
        return str(self._qs.value("acoustid/api_key", ""))

    @acoustid_api_key.setter
    def acoustid_api_key(self, value: str) -> None:
        self._qs.setValue("acoustid/api_key", value)

    # ── Ripeo ─────────────────────────────────────────────────────────

    @property
    def ripper_format(self) -> str:
        return str(self._qs.value("ripper/format", "flac"))

    @ripper_format.setter
    def ripper_format(self, value: str) -> None:
        self._qs.setValue("ripper/format", value)

    @property
    def ripper_output_dir(self) -> str:
        return str(self._qs.value("ripper/output_dir", ""))

    @ripper_output_dir.setter
    def ripper_output_dir(self, value: str) -> None:
        self._qs.setValue("ripper/output_dir", value)

    # ── Tema visual ───────────────────────────────────────────────────

    @property
    def theme(self) -> str:
        return str(self._qs.value("ui/theme", "dark"))

    @theme.setter
    def theme(self, value: str) -> None:
        self._qs.setValue("ui/theme", value)

    # ── Volumen ───────────────────────────────────────────────────────

    @property
    def volume(self) -> int:
        return int(self._qs.value("player/volume", 80))

    @volume.setter
    def volume(self, value: int) -> None:
        self._qs.setValue("player/volume", value)

    # ── Métodos de ciclo de vida ──────────────────────────────────────

    def sync(self) -> None:
        """Fuerza la escritura inmediata al almacenamiento."""
        self._qs.sync()
