"""
EqualizerService — Gestión del ecualizador gráfico de AudioRep.

Responsabilidades:
    - Cargar presets predefinidos de VLC (18 built-in).
    - Cargar presets de usuario desde la base de datos.
    - Aplicar / desactivar el EQ sobre VLCPlayer.
    - Persistir el estado activo (enabled, preset_name) en AppSettings.
    - Guardar y eliminar presets de usuario.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal

from audiorep.core.interfaces import IEqPresetRepository
from audiorep.core.settings import AppSettings
from audiorep.domain.eq_preset import EqPreset

logger = logging.getLogger(__name__)

# Bandas de frecuencia del ecualizador de VLC (10 bandas)
EQ_BAND_LABELS = ["60Hz", "170Hz", "310Hz", "600Hz", "1kHz",
                  "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"]


class EqualizerService(QObject):
    """Orquesta el estado del ecualizador y su aplicación al reproductor."""

    # El widget y el controller se suscriben a estas señales
    presets_changed = pyqtSignal()          # la lista de presets cambió

    def __init__(
        self,
        vlc_player:   object,
        preset_repo:  IEqPresetRepository,
        settings:     AppSettings,
    ) -> None:
        super().__init__()
        self._player      = vlc_player
        self._repo        = preset_repo
        self._settings    = settings
        self._builtin:    list[EqPreset] = []
        self._user:       list[EqPreset] = []
        self._load_builtins()
        self._user = self._repo.get_all()
        logger.debug("EqualizerService listo (%d presets builtin, %d usuario).",
                     len(self._builtin), len(self._user))

    # ------------------------------------------------------------------
    # Carga de presets
    # ------------------------------------------------------------------

    def _load_builtins(self) -> None:
        from audiorep.infrastructure.audio.vlc_player import VLCPlayer
        count = VLCPlayer.get_eq_preset_count()
        for i in range(count):
            name           = VLCPlayer.get_eq_preset_name(i)
            preamp, bands  = VLCPlayer.get_eq_preset_bands(i)
            self._builtin.append(EqPreset(name=name, preamp=preamp, bands=bands, is_builtin=True))

    # ------------------------------------------------------------------
    # Acceso a presets
    # ------------------------------------------------------------------

    def get_all_presets(self) -> list[EqPreset]:
        """Retorna built-in primero, luego usuario, ordenados."""
        return list(self._builtin) + sorted(self._user, key=lambda p: p.name.lower())

    def get_preset_by_name(self, name: str) -> EqPreset | None:
        for p in self._builtin + self._user:
            if p.name == name:
                return p
        return None

    # ------------------------------------------------------------------
    # Aplicar / desactivar EQ
    # ------------------------------------------------------------------

    def apply(self, preamp: float, bands: list[float]) -> None:
        """Aplica los valores actuales al player."""
        self._player.apply_equalizer(preamp, bands)  # type: ignore[attr-defined]

    def disable(self) -> None:
        """Desactiva el EQ en el player."""
        self._player.disable_equalizer()  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Estado persistente
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._settings.eq_enabled

    def set_enabled(self, enabled: bool, preamp: float, bands: list[float]) -> None:
        self._settings.eq_enabled = enabled
        self._settings.sync()
        if enabled:
            self.apply(preamp, bands)
        else:
            self.disable()

    def save_last_preset_name(self, name: str) -> None:
        self._settings.eq_preset_name = name
        self._settings.sync()

    @property
    def last_preset_name(self) -> str:
        return self._settings.eq_preset_name

    # ------------------------------------------------------------------
    # CRUD de presets de usuario
    # ------------------------------------------------------------------

    def save_user_preset(self, name: str, preamp: float, bands: list[float]) -> None:
        preset = EqPreset(name=name, preamp=preamp, bands=list(bands), is_builtin=False)
        self._repo.save(preset)
        self._user = self._repo.get_all()
        self.presets_changed.emit()
        logger.info("EqualizerService: preset de usuario guardado '%s'.", name)

    def delete_user_preset(self, name: str) -> None:
        self._repo.delete(name)
        self._user = self._repo.get_all()
        self.presets_changed.emit()
        logger.info("EqualizerService: preset de usuario eliminado '%s'.", name)

    def is_user_preset(self, name: str) -> bool:
        return any(p.name == name for p in self._user)

    # ------------------------------------------------------------------
    # Restaurar estado al iniciar
    # ------------------------------------------------------------------

    def restore_state(self) -> EqPreset | None:
        """
        Si el EQ estaba activo en la sesión anterior, lo reactiva y retorna
        el preset activo para que el widget pueda inicializarse correctamente.
        """
        if not self._settings.eq_enabled:
            return None
        preset = self.get_preset_by_name(self._settings.eq_preset_name)
        if preset is None:
            preset = self._builtin[0] if self._builtin else None
        if preset:
            self.apply(preset.preamp, preset.bands)
            logger.info("EqualizerService: EQ restaurado con preset '%s'.", preset.name)
        return preset
