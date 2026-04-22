"""
CDMetadataPanel — Panel lateral de búsqueda manual de metadatos de CD.

Ubicación: columna derecha del tab CD (a la izquierda del NowPlaying).

Layout:
    [Label "Servicio"] [QComboBox servicios  ▼]  [Buscar]
    ──────────────────────────────────────────────────────
    Resultados (QListWidget — un ítem por release):
        "Artista — Álbum (Año)"
    ──────────────────────────────────────────────────────
    Detalle del resultado seleccionado:
        Artista / Álbum / Año / Género
        Lista de pistas (QListWidget)
    ──────────────────────────────────────────────────────
    [Aplicar al disco]

Signals:
    search_requested(str)       — nombre del servicio seleccionado
    apply_requested(dict)       — resultado normalizado a aplicar al CDDisc
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class CDMetadataPanel(QWidget):
    """Panel de búsqueda y aplicación manual de metadatos de CD."""

    search_requested = pyqtSignal(str)   # nombre del servicio
    apply_requested  = pyqtSignal(dict)  # resultado normalizado seleccionado

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cdMetadataPanel")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(220)
        self.setMaximumWidth(340)
        self._results: list[dict] = []
        self._selected: dict | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Título de sección
        title = QLabel("Búsqueda de metadatos")
        title.setObjectName("cdMetaTitle")
        layout.addWidget(title)

        # ── Fila de servicio + búsqueda ───────────────────────────── #
        svc_row = QHBoxLayout()
        svc_row.setSpacing(6)

        svc_label = QLabel("Servicio:")
        svc_label.setObjectName("cdMetaLabel")
        svc_label.setFixedWidth(58)
        svc_row.addWidget(svc_label)

        self._service_combo = QComboBox()
        self._service_combo.setObjectName("cdMetaServiceCombo")
        self._service_combo.setToolTip("Seleccionar servicio de búsqueda")
        svc_row.addWidget(self._service_combo, stretch=1)

        layout.addLayout(svc_row)

        self._search_btn = QPushButton("🔍 Buscar")
        self._search_btn.setObjectName("cdMetaSearchBtn")
        self._search_btn.setEnabled(False)
        self._search_btn.clicked.connect(self._on_search)
        layout.addWidget(self._search_btn)

        # ── Separador ─────────────────────────────────────────────── #
        layout.addWidget(self._make_separator())

        # ── Lista de resultados ───────────────────────────────────── #
        results_label = QLabel("Resultados:")
        results_label.setObjectName("cdMetaLabel")
        layout.addWidget(results_label)

        self._results_list = QListWidget()
        self._results_list.setObjectName("cdMetaResultsList")
        self._results_list.setAlternatingRowColors(True)
        self._results_list.setMaximumHeight(120)
        self._results_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._results_list.currentRowChanged.connect(self._on_result_selected)
        layout.addWidget(self._results_list)

        # ── Separador ─────────────────────────────────────────────── #
        layout.addWidget(self._make_separator())

        # ── Detalle del resultado seleccionado ────────────────────── #
        detail_label = QLabel("Detalle:")
        detail_label.setObjectName("cdMetaLabel")
        layout.addWidget(detail_label)

        self._album_row  = self._make_detail_row("Nombre del Disco:")
        self._artist_row = self._make_detail_row("Artista:")
        self._label_row  = self._make_detail_row("Sello Musical:")
        self._year_row   = self._make_detail_row("Año:")

        for _lbl, _val, row_w in (self._album_row, self._artist_row,
                                   self._label_row, self._year_row):
            layout.addWidget(row_w)

        # Lista de pistas del resultado
        self._track_list = QListWidget()
        self._track_list.setObjectName("cdMetaTrackList")
        self._track_list.setAlternatingRowColors(True)
        self._track_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._track_list, stretch=1)

        # ── Botón Aplicar ─────────────────────────────────────────── #
        layout.addWidget(self._make_separator())

        self._apply_btn = QPushButton("✔ Aplicar al disco")
        self._apply_btn.setObjectName("cdMetaApplyBtn")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(self._apply_btn)

        # Estado inicial del Detalle (todos los campos instanciados ya)
        self._clear_detail()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_services(self, service_names: list[str]) -> None:
        """Puebla el desplegable con los nombres de los servicios disponibles."""
        self._service_combo.clear()
        for name in service_names:
            self._service_combo.addItem(name)
        self._search_btn.setEnabled(bool(service_names))

    def set_disc_available(self, available: bool) -> None:
        """Habilita o deshabilita la búsqueda según si hay un CD detectado."""
        self._search_btn.setEnabled(available and self._service_combo.count() > 0)

    def show_results(self, results: list[dict]) -> None:
        """Muestra los resultados de búsqueda en la lista."""
        self._results = results
        self._results_list.clear()
        self._clear_detail()
        self._apply_btn.setEnabled(False)

        if not results:
            item = QListWidgetItem("Sin resultados")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._results_list.addItem(item)
            return

        for r in results:
            artist = r.get("artist", "") or "Desconocido"
            album  = r.get("album", "") or "Álbum desconocido"
            year   = r.get("year", "")
            label  = f"{artist} — {album}"
            if year:
                label += f"  ({year})"
            self._results_list.addItem(QListWidgetItem(label))

    def show_searching(self) -> None:
        """Indica que la búsqueda está en curso."""
        self._results_list.clear()
        self._clear_detail()
        item = QListWidgetItem("Buscando…")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._results_list.addItem(item)
        self._apply_btn.setEnabled(False)

    def show_error(self, message: str) -> None:
        """Muestra un mensaje de error."""
        self._results_list.clear()
        self._clear_detail()
        item = QListWidgetItem(f"Error: {message}")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self._results_list.addItem(item)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_search(self) -> None:
        service = self._service_combo.currentText()
        if service:
            self.show_searching()
            self.search_requested.emit(service)

    def _on_result_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._results):
            self._clear_detail()
            self._apply_btn.setEnabled(False)
            return
        result = self._results[row]
        self._selected = result
        self._show_detail(result)
        self._apply_btn.setEnabled(True)

    def _on_apply(self) -> None:
        if self._selected:
            self.apply_requested.emit(self._selected)

    def _show_detail(self, result: dict) -> None:
        album  = result.get("album", "") or ""
        artist = result.get("artist", "") or ""
        label  = result.get("label", "") or ""
        year   = result.get("year", "") or ""

        self._set_detail_row(self._album_row,  album,  show_if_empty=True)
        self._set_detail_row(self._artist_row, artist, show_if_empty=True)
        self._set_detail_row(self._label_row,  label,  show_if_empty=False)
        self._set_detail_row(self._year_row,   year,   show_if_empty=False)

        self._track_list.clear()
        for t in result.get("tracks", []):
            num   = t.get("number", "")
            title = t.get("title", "")
            self._track_list.addItem(f"{num:02d}. {title}" if isinstance(num, int) else f"{num}. {title}")

    def _clear_detail(self) -> None:
        self._selected = None
        self._set_detail_row(self._album_row,  "—", show_if_empty=True)
        self._set_detail_row(self._artist_row, "—", show_if_empty=True)
        self._set_detail_row(self._label_row,  "",  show_if_empty=False)
        self._set_detail_row(self._year_row,   "",  show_if_empty=False)
        self._track_list.clear()

    def _make_detail_row(self, label_text: str) -> tuple:
        """Crea una fila 'Label: Valor' y retorna (lbl_widget, val_widget, row_widget)."""
        row_w = QWidget()
        row_w.setObjectName("cdMetaDetailRow")
        row_layout = QHBoxLayout(row_w)
        row_layout.setContentsMargins(0, 1, 0, 1)
        row_layout.setSpacing(4)

        lbl = QLabel(label_text)
        lbl.setObjectName("cdMetaDetailKey")
        lbl.setFixedWidth(100)
        lbl.setWordWrap(False)
        row_layout.addWidget(lbl)

        val = QLabel("")
        val.setObjectName("cdMetaDetailVal")
        val.setWordWrap(True)
        row_layout.addWidget(val, stretch=1)

        return lbl, val, row_w

    @staticmethod
    def _set_detail_row(row_tuple: tuple, value: str, show_if_empty: bool) -> None:
        _lbl, val, row_w = row_tuple
        val.setText(value)
        row_w.setVisible(show_if_empty or bool(value))

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setObjectName("cdMetaSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        return sep
