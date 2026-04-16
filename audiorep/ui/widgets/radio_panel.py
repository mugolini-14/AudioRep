"""
AudioRep — Panel de radio por internet.

Presenta tres pestañas:
  1. Buscar  — formulario de búsqueda + lista de resultados
  2. Guardadas — emisoras persistidas localmente
  3. Favoritas — subconjunto marcado como favorito

El widget solo emite señales; no llama a ningún service directamente.
El `RadioController` conecta estas señales con `RadioService`.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.radio_station import RadioStation


class RadioPanel(QWidget):
    """
    Panel principal de radio por internet.

    Signals:
        search_requested(query, country, genre):
            El usuario presionó "Buscar".
        play_requested(RadioStation):
            El usuario quiere reproducir la emisora seleccionada.
        stop_requested():
            El usuario presionó "Detener".
        save_requested(RadioStation):
            El usuario quiere guardar la emisora seleccionada del resultado.
        delete_requested(int):
            El usuario quiere eliminar la emisora guardada (station_id).
        favorite_toggled(int):
            El usuario quiere alternar favorita de la emisora guardada (station_id).
    """

    search_requested  = pyqtSignal(str, str, str)   # (query, country, genre)
    play_requested    = pyqtSignal(object)           # RadioStation
    stop_requested    = pyqtSignal()
    save_requested    = pyqtSignal(object)           # RadioStation
    delete_requested  = pyqtSignal(int)              # station_id
    favorite_toggled  = pyqtSignal(int)              # station_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadioPanel")
        self._build_ui()
        self._connect_internal()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Tabs ──────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setObjectName("RadioTabs")
        self._tabs.addTab(self._build_search_tab(),  "Buscar")
        self._tabs.addTab(self._build_saved_tab(),   "Guardadas")
        self._tabs.addTab(self._build_favs_tab(),    "Favoritas")
        root.addWidget(self._tabs)

        # ── Barra de estado de reproducción ──────────────────────────
        self._now_playing_label = QLabel("Sin emisora en reproducción")
        self._now_playing_label.setObjectName("RadioNowPlaying")
        self._now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._now_playing_label)

        # ── Botones de acción (zona inferior) ─────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_play   = QPushButton("▶  Reproducir")
        self._btn_stop   = QPushButton("■  Detener")
        self._btn_save   = QPushButton("＋  Guardar")
        self._btn_delete = QPushButton("✕  Eliminar")
        self._btn_fav    = QPushButton("♥  Favorita")

        self._btn_play.setObjectName("RadioBtnPlay")
        self._btn_stop.setObjectName("RadioBtnStop")
        self._btn_save.setObjectName("RadioBtnSave")
        self._btn_delete.setObjectName("RadioBtnDelete")
        self._btn_fav.setObjectName("RadioBtnFav")

        self._btn_stop.setEnabled(False)

        for btn in (self._btn_play, self._btn_stop, self._btn_save,
                    self._btn_delete, self._btn_fav):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn_row.addWidget(btn)

        root.addLayout(btn_row)

    def _build_search_tab(self) -> QWidget:
        """Pestaña de búsqueda: campos + lista de resultados."""
        tab = QWidget()
        tab.setObjectName("RadioSearchTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(6)

        # Fila de búsqueda
        search_row = QHBoxLayout()
        self._search_input   = QLineEdit()
        self._search_input.setObjectName("RadioSearchInput")
        self._search_input.setPlaceholderText("Nombre de la emisora…")

        self._country_input  = QLineEdit()
        self._country_input.setObjectName("RadioCountryInput")
        self._country_input.setPlaceholderText("País (ej: AR)")
        self._country_input.setMaximumWidth(160)

        self._genre_input    = QLineEdit()
        self._genre_input.setObjectName("RadioGenreInput")
        self._genre_input.setPlaceholderText("Género (ej: rock)")
        self._genre_input.setMaximumWidth(160)

        self._btn_search     = QPushButton("Buscar")
        self._btn_search.setObjectName("RadioBtnSearch")
        self._btn_search.setDefault(True)
        self._btn_search.setMinimumWidth(100)

        search_row.addWidget(self._search_input)
        search_row.addWidget(self._country_input)
        search_row.addWidget(self._genre_input)
        search_row.addWidget(self._btn_search)
        layout.addLayout(search_row)

        # Tabla de resultados
        self._results_list = QTableWidget()
        self._results_list.setObjectName("RadioResultsTable")
        self._results_list.setColumnCount(4)
        self._results_list.setHorizontalHeaderLabels(["Nombre", "País", "Género", "Bitrate"])
        self._results_list.setAlternatingRowColors(True)
        self._results_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._results_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._results_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._results_list.verticalHeader().setVisible(False)
        self._results_list.setShowGrid(False)
        self._results_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        header = self._results_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._results_list.setColumnWidth(1, 60)
        self._results_list.setColumnWidth(2, 110)
        self._results_list.setColumnWidth(3, 75)
        layout.addWidget(self._results_list)

        return tab

    def _build_saved_tab(self) -> QWidget:
        """Pestaña de emisoras guardadas."""
        tab = QWidget()
        tab.setObjectName("RadioSavedTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)

        self._saved_list = QListWidget()
        self._saved_list.setObjectName("RadioSavedList")
        self._saved_list.setAlternatingRowColors(True)
        layout.addWidget(self._saved_list)

        return tab

    def _build_favs_tab(self) -> QWidget:
        """Pestaña de emisoras favoritas."""
        tab = QWidget()
        tab.setObjectName("RadioFavsTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)

        self._favs_list = QListWidget()
        self._favs_list.setObjectName("RadioFavsList")
        self._favs_list.setAlternatingRowColors(True)
        layout.addWidget(self._favs_list)

        return tab

    # ------------------------------------------------------------------
    # Conexiones internas
    # ------------------------------------------------------------------

    def _connect_internal(self) -> None:
        self._btn_search.clicked.connect(self._on_search_clicked)
        self._search_input.returnPressed.connect(self._on_search_clicked)
        self._btn_play.clicked.connect(self._on_play_clicked)
        self._btn_stop.clicked.connect(self.stop_requested)
        self._btn_save.clicked.connect(self._on_save_clicked)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        self._btn_fav.clicked.connect(self._on_fav_clicked)

        # Doble clic en cualquier lista → reproducir
        self._results_list.doubleClicked.connect(self._on_play_clicked)
        self._saved_list.itemDoubleClicked.connect(self._on_play_clicked)
        self._favs_list.itemDoubleClicked.connect(self._on_play_clicked)

        # Actualizar botones según selección activa
        self._tabs.currentChanged.connect(self._update_buttons)
        self._results_list.itemSelectionChanged.connect(self._update_buttons)
        self._saved_list.itemSelectionChanged.connect(self._update_buttons)
        self._favs_list.itemSelectionChanged.connect(self._update_buttons)

        self._update_buttons()

    # ------------------------------------------------------------------
    # Handlers internos
    # ------------------------------------------------------------------

    def _on_search_clicked(self) -> None:
        query   = self._search_input.text().strip()
        country = self._country_input.text().strip()
        genre   = self._genre_input.text().strip()
        self.search_requested.emit(query, country, genre)

    def _on_play_clicked(self, _item=None) -> None:
        station = self._selected_station()
        if station is not None:
            self.play_requested.emit(station)

    def _on_save_clicked(self) -> None:
        # Solo tiene sentido guardar desde la pestaña de resultados
        station = self._selected_from_results()
        if station is not None:
            self.save_requested.emit(station)

    def _on_delete_clicked(self) -> None:
        station = self._selected_saved_station()
        if station is not None and station.id is not None:
            self.delete_requested.emit(station.id)

    def _on_fav_clicked(self) -> None:
        station = self._selected_saved_station()
        if station is not None and station.id is not None:
            self.favorite_toggled.emit(station.id)

    def _update_buttons(self) -> None:
        """Habilita/deshabilita botones según la pestaña y selección activa."""
        tab_idx  = self._tabs.currentIndex()
        has_result  = self._selected_from_results() is not None
        has_saved   = self._selected_saved_station() is not None
        has_any     = self._selected_station() is not None

        self._btn_play.setEnabled(has_any)
        self._btn_save.setEnabled(tab_idx == 0 and has_result)
        self._btn_delete.setEnabled(tab_idx in (1, 2) and has_saved)
        self._btn_fav.setEnabled(tab_idx in (1, 2) and has_saved)

    # ------------------------------------------------------------------
    # Helpers de selección
    # ------------------------------------------------------------------

    def _selected_station(self) -> RadioStation | None:
        """Retorna la emisora seleccionada en la pestaña activa."""
        tab_idx = self._tabs.currentIndex()
        if tab_idx == 0:
            return self._station_from_table(self._results_list)
        if tab_idx == 1:
            return self._station_from_list(self._saved_list)
        return self._station_from_list(self._favs_list)

    def _selected_from_results(self) -> RadioStation | None:
        return self._station_from_table(self._results_list)

    def _selected_saved_station(self) -> RadioStation | None:
        tab_idx = self._tabs.currentIndex()
        if tab_idx == 1:
            return self._station_from_list(self._saved_list)
        if tab_idx == 2:
            return self._station_from_list(self._favs_list)
        return None

    @staticmethod
    def _station_from_table(table: QTableWidget) -> RadioStation | None:
        rows = table.selectedItems()
        if not rows:
            return None
        return table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    @staticmethod
    def _station_from_list(lst: QListWidget) -> RadioStation | None:
        items = lst.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # API pública (llamada por el controller)
    # ------------------------------------------------------------------

    def set_search_results(self, stations: list[RadioStation]) -> None:
        """Muestra los resultados de búsqueda en la tabla correspondiente."""
        self._results_list.setRowCount(0)
        self._results_list.setRowCount(len(stations))
        for row, station in enumerate(stations):
            name_item = QTableWidgetItem(station.name)
            name_item.setData(Qt.ItemDataRole.UserRole, station)
            name_item.setToolTip(station.stream_url)
            if station.is_favorite:
                name_item.setText(f"♥  {station.name}")

            country_item = QTableWidgetItem(station.country or "")
            country_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            genre_item = QTableWidgetItem(station.genre or "")
            genre_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            bitrate_text = f"{station.bitrate_kbps} kbps" if station.bitrate_kbps else ""
            bitrate_item = QTableWidgetItem(bitrate_text)
            bitrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            self._results_list.setItem(row, 0, name_item)
            self._results_list.setItem(row, 1, country_item)
            self._results_list.setItem(row, 2, genre_item)
            self._results_list.setItem(row, 3, bitrate_item)

        self._results_list.resizeRowsToContents()
        self._update_buttons()

    def set_saved_stations(self, stations: list[RadioStation]) -> None:
        """Actualiza la lista de emisoras guardadas."""
        self._saved_list.clear()
        for station in stations:
            item = QListWidgetItem(self._station_label(station))
            item.setData(Qt.ItemDataRole.UserRole, station)
            item.setToolTip(station.stream_url)
            self._saved_list.addItem(item)
        self._update_buttons()

    def set_favorite_stations(self, stations: list[RadioStation]) -> None:
        """Actualiza la lista de emisoras favoritas."""
        self._favs_list.clear()
        for station in stations:
            item = QListWidgetItem(self._station_label(station))
            item.setData(Qt.ItemDataRole.UserRole, station)
            item.setToolTip(station.stream_url)
            self._favs_list.addItem(item)
        self._update_buttons()

    def set_now_playing(self, station: RadioStation | None) -> None:
        """Actualiza la etiqueta de reproducción actual y el botón Detener."""
        if station is None:
            self._now_playing_label.setText("Sin emisora en reproducción")
            self._btn_stop.setEnabled(False)
        else:
            bitrate = f" · {station.bitrate_kbps} kbps" if station.bitrate_kbps else ""
            self._now_playing_label.setText(f"▶  {station.name}{bitrate}")
            self._btn_stop.setEnabled(True)

    def set_searching(self, active: bool) -> None:
        """Muestra/oculta el estado de búsqueda en curso."""
        self._btn_search.setEnabled(not active)
        self._btn_search.setText("Buscando…" if active else "Buscar")

