"""
EqualizerController — Bisagra entre PlayerBar, EqualizerWidget y EqualizerService.

Responsabilidades:
    - Abrir/cerrar el EqualizerWidget cuando el usuario presiona el botón EQ.
    - Conectar las señales del widget con EqualizerService.
    - Restaurar el estado del EQ al iniciar la aplicación.
    - Mantener sincronizado el botón EQ de la PlayerBar con el estado del EQ.
"""
from __future__ import annotations

import logging

from audiorep.services.equalizer_service import EqualizerService
from audiorep.ui.widgets.equalizer_widget import EqualizerWidget
from audiorep.ui.widgets.player_bar import PlayerBar

logger = logging.getLogger(__name__)


class EqualizerController:
    """Controller del ecualizador gráfico."""

    def __init__(
        self,
        player_bar: PlayerBar,
        eq_service:  EqualizerService,
        eq_widget:   EqualizerWidget,
    ) -> None:
        self._bar     = player_bar
        self._service = eq_service
        self._widget  = eq_widget

        self._connect_bar()
        self._connect_widget()
        self._connect_service()
        self._restore_state()

        logger.debug("EqualizerController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def _connect_bar(self) -> None:
        self._bar.eq_toggled.connect(self._on_eq_toggled)

    def _connect_widget(self) -> None:
        self._widget.enabled_toggled.connect(self._on_enabled_toggled)
        self._widget.preset_selected.connect(self._on_preset_selected)
        self._widget.bands_changed.connect(self._on_bands_changed)
        self._widget.save_requested.connect(self._on_save_requested)
        self._widget.delete_requested.connect(self._on_delete_requested)
        self._widget.reset_requested.connect(self._on_reset_requested)

    def _connect_service(self) -> None:
        self._service.presets_changed.connect(self._reload_presets)

    # ------------------------------------------------------------------
    # Handlers: PlayerBar
    # ------------------------------------------------------------------

    def _on_eq_toggled(self, checked: bool) -> None:
        self._widget.setVisible(checked)

    # ------------------------------------------------------------------
    # Handlers: EqualizerWidget
    # ------------------------------------------------------------------

    def _on_enabled_toggled(self, enabled: bool) -> None:
        preamp, bands = self._current_values()
        self._service.set_enabled(enabled, preamp, bands)
        self._bar.set_eq_active(enabled)
        # Si se activa, también mostrar el widget; si se desactiva desde el check,
        # mantener el diálogo abierto pero sin aplicar EQ.

    def _on_preset_selected(self, name: str) -> None:
        preset = self._service.get_preset_by_name(name)
        if preset is None:
            return
        self._widget.set_preset(preset)
        self._service.save_last_preset_name(name)
        if self._service.is_enabled:
            self._service.apply(preset.preamp, preset.bands)

    def _on_bands_changed(self, preamp: float, bands: list) -> None:
        if self._service.is_enabled:
            self._service.apply(preamp, bands)

    def _on_save_requested(self, name: str, preamp: float, bands: list) -> None:
        self._service.save_user_preset(name, preamp, bands)
        self._service.save_last_preset_name(name)

    def _on_delete_requested(self, name: str) -> None:
        self._service.delete_user_preset(name)
        # Seleccionar "Flat" como fallback
        self._on_preset_selected("Flat")

    def _on_reset_requested(self) -> None:
        self._widget.reset_sliders()

    # ------------------------------------------------------------------
    # Handlers: EqualizerService
    # ------------------------------------------------------------------

    def _reload_presets(self) -> None:
        self._widget.populate_presets(self._service.get_all_presets())

    # ------------------------------------------------------------------
    # Estado inicial
    # ------------------------------------------------------------------

    def _restore_state(self) -> None:
        self._widget.populate_presets(self._service.get_all_presets())
        active_preset = self._service.restore_state()
        enabled = self._service.is_enabled
        self._widget.set_enabled(enabled)
        self._bar.set_eq_active(enabled)
        if active_preset:
            self._widget.set_preset(active_preset)
        else:
            # Cargar Flat como preset por defecto
            flat = self._service.get_preset_by_name("Flat")
            if flat:
                self._widget.set_preset(flat)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_values(self) -> tuple[float, list[float]]:
        """Lee preamp y bandas actuales de los sliders del widget."""
        sliders = self._widget._sliders
        preamp = sliders[0].value() / 10.0
        bands  = [sliders[i + 1].value() / 10.0 for i in range(10)]
        return preamp, bands
