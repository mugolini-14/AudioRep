"""
SettingsDialog — Diálogo de configuración de AudioRep.

Permite editar:
    - Clave de API de AcoustID
    - Formato de ripeo (FLAC, MP3, OGG)
    - Directorio de salida del ripeo
    - Tema visual (dark / light)
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from audiorep.core.settings import AppSettings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """
    Diálogo de preferencias.

    Args:
        settings: AppSettings con la configuración actual.
        parent:   Widget padre.

    Signals:
        settings_saved: Emitido cuando el usuario acepta los cambios.
    """

    settings_saved = pyqtSignal()

    def __init__(
        self,
        settings: AppSettings,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings

        self.setWindowTitle("Configuración")
        self.setMinimumWidth(480)
        self.setObjectName("SettingsDialog")

        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # AcoustID API key
        self._acoustid_edit = QLineEdit(settings.acoustid_api_key or "")
        self._acoustid_edit.setObjectName("SettingsAcoustID")
        self._acoustid_edit.setPlaceholderText("Introducí tu clave de AcoustID")
        form.addRow("Clave AcoustID:", self._acoustid_edit)

        # Formato de ripeo
        self._format_combo = QComboBox()
        self._format_combo.setObjectName("SettingsRipFormat")
        self._format_combo.addItems(["flac", "mp3", "ogg"])
        current_fmt = settings.ripper_format or "flac"
        idx = self._format_combo.findText(current_fmt)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)
        form.addRow("Formato de ripeo:", self._format_combo)

        # Directorio de ripeo
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self._dir_edit = QLineEdit(settings.ripper_output_dir or "")
        self._dir_edit.setObjectName("SettingsRipDir")
        self._dir_edit.setPlaceholderText("Seleccioná una carpeta…")
        dir_btn = QPushButton("…")
        dir_btn.setObjectName("SettingsDirBtn")
        dir_btn.setFixedWidth(30)
        dir_btn.clicked.connect(self._pick_dir)
        dir_layout.addWidget(self._dir_edit)
        dir_layout.addWidget(dir_btn)
        form.addRow("Carpeta de ripeo:", dir_row)

        layout.addLayout(form)

        # ── Separador ─────────────────────────────────────────────── #
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #33334a;")
        layout.addWidget(sep)

        # ── Sección: Actualización automática de metadatos ─────────── #
        enrich_form = QFormLayout()
        enrich_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._enrich_check = QCheckBox("Activar actualización automática de metadatos")
        self._enrich_check.setChecked(settings.enrichment_enabled)
        layout.addWidget(self._enrich_check)

        interval_row = QWidget()
        interval_layout = QHBoxLayout(interval_row)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 365)
        self._interval_spin.setValue(settings.enrichment_interval_days)
        self._interval_spin.setSuffix(" días")
        interval_layout.addWidget(self._interval_spin)
        interval_layout.addStretch()
        enrich_form.addRow("Intervalo:", interval_row)

        last_run = settings.enrichment_last_run or "Nunca"
        self._last_run_label = QLabel(f"Última actualización: {last_run}")
        self._last_run_label.setStyleSheet("color: #8888aa; font-size: 11px;")
        enrich_form.addRow("", self._last_run_label)

        # Last.fm API Key (opcional)
        self._lastfm_edit = QLineEdit(settings.lastfm_api_key or "")
        self._lastfm_edit.setPlaceholderText("Opcional — para mejor cobertura de géneros")
        self._lastfm_edit.setObjectName("SettingsLastFm")
        enrich_form.addRow("Last.fm API Key:", self._lastfm_edit)

        layout.addLayout(enrich_form)

        # Botón "Actualizar ahora"
        enrich_btn_row = QHBoxLayout()
        self._enrich_now_btn = QPushButton("Actualizar metadatos ahora")
        self._enrich_now_btn.setObjectName("importButton")
        self._enrich_now_btn.clicked.connect(self._on_enrich_now)
        enrich_btn_row.addWidget(self._enrich_now_btn)
        enrich_btn_row.addStretch()
        layout.addLayout(enrich_btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _pick_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccioná la carpeta de destino para el ripeo",
            self._dir_edit.text() or str(Path.home()),
        )
        if folder:
            self._dir_edit.setText(folder)

    def _on_enrich_now(self) -> None:
        """Guarda la configuración y solicita el enriquecimiento inmediato."""
        self._save_settings()
        from audiorep.core.events import app_events
        app_events.enrichment_requested.emit()
        self.accept()

    def _on_accept(self) -> None:
        self._save_settings()
        self.settings_saved.emit()
        self.accept()
        logger.info("Configuración guardada.")

    def _save_settings(self) -> None:
        self._settings.acoustid_api_key        = self._acoustid_edit.text().strip()
        self._settings.ripper_format           = self._format_combo.currentText()
        self._settings.ripper_output_dir       = self._dir_edit.text().strip()
        self._settings.enrichment_enabled      = self._enrich_check.isChecked()
        self._settings.enrichment_interval_days = self._interval_spin.value()
        self._settings.lastfm_api_key          = self._lastfm_edit.text().strip()
        self._settings.sync()
