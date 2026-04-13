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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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

    def _on_accept(self) -> None:
        self._settings.acoustid_api_key  = self._acoustid_edit.text().strip()
        self._settings.ripper_format     = self._format_combo.currentText()
        self._settings.ripper_output_dir = self._dir_edit.text().strip()
        self._settings.sync()
        self.settings_saved.emit()
        self.accept()
        logger.info("Configuración guardada.")
