"""
EqualizerWidget — Panel embebido del ecualizador gráfico.

Se inserta en el layout de MainWindow entre el separador y la PlayerBar.
Oculto por defecto; se muestra/oculta con el botón EQ de la PlayerBar.

Layout:
    Fila superior:  [✓ Activar EQ]   Preset: [combobox ▼]   [Guardar]  [Eliminar]  → stretch → [Resetear a 0]
    Sliders:        Preamp | 60Hz | 170Hz | 310Hz | 600Hz | 1kHz | 3kHz | 6kHz | 12kHz | 14kHz | 16kHz
                    (sliders verticales -20 dB a +20 dB, etiqueta de valor bajo cada uno)

Signals:
    enabled_toggled(bool)             — checkbox Activar EQ
    preset_selected(str)              — selección en el combobox
    bands_changed(float, list)        — preamp + 10 bandas modificadas
    save_requested(str, float, list)  — guardar preset con nombre
    delete_requested(str)             — eliminar preset seleccionado
    reset_requested()                 — resetear todos los sliders a 0
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.eq_preset import EqPreset
from audiorep.services.equalizer_service import EQ_BAND_LABELS

_SEPARATOR     = "──────────────"
_SLIDER_LABELS = ["Preamp"] + EQ_BAND_LABELS


class EqualizerWidget(QWidget):
    """Panel embebido del ecualizador gráfico de 10 bandas."""

    enabled_toggled  = pyqtSignal(bool)
    preset_selected  = pyqtSignal(str)
    bands_changed    = pyqtSignal(float, list)
    save_requested   = pyqtSignal(str, float, list)
    delete_requested = pyqtSignal(str)
    reset_requested  = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("eqPanel")
        self._suppress_signals = False
        self._build_ui()
        self._connect_internal()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 6, 16, 6)
        root.setSpacing(4)

        # ── Fila superior ────────────────────────────────────────────── #
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._enable_check = QCheckBox("Activar EQ")
        self._enable_check.setObjectName("eqEnableCheck")
        top_row.addWidget(self._enable_check)

        top_row.addSpacing(8)

        preset_label = QLabel("Preset:")
        preset_label.setObjectName("eqLabel")
        top_row.addWidget(preset_label)

        self._preset_combo = QComboBox()
        self._preset_combo.setObjectName("eqPresetCombo")
        self._preset_combo.setMinimumWidth(150)
        top_row.addWidget(self._preset_combo)

        self._save_btn = QPushButton("Guardar preset")
        self._save_btn.setObjectName("eqSaveBtn")
        top_row.addWidget(self._save_btn)

        self._delete_btn = QPushButton("Eliminar preset")
        self._delete_btn.setObjectName("eqDeleteBtn")
        self._delete_btn.setEnabled(False)
        top_row.addWidget(self._delete_btn)

        top_row.addStretch()

        self._reset_btn = QPushButton("Resetear a 0")
        self._reset_btn.setObjectName("eqResetBtn")
        top_row.addWidget(self._reset_btn)

        root.addLayout(top_row)

        # ── Sliders verticales ────────────────────────────────────────── #
        sliders_row = QHBoxLayout()
        sliders_row.setContentsMargins(0, 0, 0, 0)
        sliders_row.setSpacing(4)
        sliders_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._sliders: list[QSlider] = []
        self._value_labels: list[QLabel] = []

        for label_text in _SLIDER_LABELS:
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            freq_lbl = QLabel(label_text)
            freq_lbl.setObjectName("eqFreqLabel")
            freq_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(freq_lbl)

            slider = QSlider(Qt.Orientation.Vertical)
            slider.setObjectName("eqSlider")
            slider.setRange(-200, 200)
            slider.setValue(0)
            slider.setFixedWidth(28)
            slider.setMinimumHeight(90)
            slider.setMaximumHeight(110)
            slider.setTickInterval(100)
            slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
            slider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            col.addWidget(slider, alignment=Qt.AlignmentFlag.AlignHCenter)

            val_lbl = QLabel("0.0")
            val_lbl.setObjectName("eqValueLabel")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_lbl.setFixedWidth(40)
            col.addWidget(val_lbl)

            self._sliders.append(slider)
            self._value_labels.append(val_lbl)

            col_widget = QWidget()
            col_widget.setLayout(col)
            sliders_row.addWidget(col_widget)

        sliders_row.addStretch()
        root.addLayout(sliders_row)

    # ------------------------------------------------------------------
    # Conexiones internas
    # ------------------------------------------------------------------

    def _connect_internal(self) -> None:
        self._enable_check.toggled.connect(self._on_enable_toggled)
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        for slider in self._sliders:
            slider.valueChanged.connect(self._on_any_slider_changed)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_enable_toggled(self, checked: bool) -> None:
        if not self._suppress_signals:
            self.enabled_toggled.emit(checked)

    def _on_preset_changed(self, name: str) -> None:
        if name == _SEPARATOR or self._suppress_signals:
            return
        is_user = name in self._user_preset_names()
        self._delete_btn.setEnabled(is_user)
        self.preset_selected.emit(name)

    def _on_any_slider_changed(self) -> None:
        for i, s in enumerate(self._sliders):
            val = s.value() / 10.0
            self._value_labels[i].setText(f"{val:+.1f}" if val != 0 else "0.0")
        if not self._suppress_signals:
            preamp, bands = self._read_sliders()
            self.bands_changed.emit(preamp, bands)

    def _on_save_clicked(self) -> None:
        current = self._preset_combo.currentText()
        if current == _SEPARATOR:
            current = ""
        is_user = current in self._user_preset_names()
        default = current if is_user else ""
        name, ok = QInputDialog.getText(
            self, "Guardar preset", "Nombre del preset:", text=default
        )
        if not ok or not name.strip():
            return
        preamp, bands = self._read_sliders()
        self.save_requested.emit(name.strip(), preamp, bands)

    def _on_delete_clicked(self) -> None:
        name = self._preset_combo.currentText()
        if not name or name == _SEPARATOR:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Eliminar preset")
        msg.setText(f'¿Eliminar el preset "{name}"?')
        msg.setIcon(QMessageBox.Icon.Question)
        yes_btn = msg.addButton("Sí", QMessageBox.ButtonRole.YesRole)
        msg.addButton("No", QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() == yes_btn:
            self.delete_requested.emit(name)

    def _on_reset_clicked(self) -> None:
        self.reset_requested.emit()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def populate_presets(self, presets: list[EqPreset]) -> None:
        self._suppress_signals = True
        current = self._preset_combo.currentText()
        self._preset_combo.clear()
        builtin = [p for p in presets if p.is_builtin]
        user    = [p for p in presets if not p.is_builtin]
        for p in builtin:
            self._preset_combo.addItem(p.name)
        if user:
            self._preset_combo.addItem(_SEPARATOR)
            idx = self._preset_combo.count() - 1
            self._preset_combo.model().item(idx).setEnabled(False)
            for p in user:
                self._preset_combo.addItem(p.name)
        idx = self._preset_combo.findText(current)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._suppress_signals = False

    def set_preset(self, preset: EqPreset) -> None:
        self._suppress_signals = True
        self._sliders[0].setValue(round(preset.preamp * 10))
        for i, amp in enumerate(preset.bands[:10]):
            self._sliders[i + 1].setValue(round(amp * 10))
        for i, s in enumerate(self._sliders):
            val = s.value() / 10.0
            self._value_labels[i].setText(f"{val:+.1f}" if val != 0 else "0.0")
        idx = self._preset_combo.findText(preset.name)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)
        self._delete_btn.setEnabled(preset.name in self._user_preset_names())
        self._suppress_signals = False

    def set_enabled(self, enabled: bool) -> None:
        self._suppress_signals = True
        self._enable_check.setChecked(enabled)
        self._suppress_signals = False

    def reset_sliders(self) -> None:
        self._suppress_signals = True
        for s in self._sliders:
            s.setValue(0)
        for lbl in self._value_labels:
            lbl.setText("0.0")
        self._suppress_signals = False
        self.bands_changed.emit(0.0, [0.0] * 10)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_sliders(self) -> tuple[float, list[float]]:
        preamp = self._sliders[0].value() / 10.0
        bands  = [self._sliders[i + 1].value() / 10.0 for i in range(10)]
        return preamp, bands

    def _user_preset_names(self) -> list[str]:
        names: list[str] = []
        found_sep = False
        for i in range(self._preset_combo.count()):
            text = self._preset_combo.itemText(i)
            if text == _SEPARATOR:
                found_sep = True
                continue
            if found_sep:
                names.append(text)
        return names
