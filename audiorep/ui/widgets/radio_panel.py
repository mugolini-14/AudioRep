"""
AudioRep — Panel de radio por internet.

Presenta tres pestañas:
  1. Buscar    — formulario de búsqueda + tabla de resultados (llamada a API)
  2. Guardadas — emisoras persistidas localmente con barra de filtro
  3. Favoritas — subconjunto marcado como favorito con barra de filtro

El widget solo emite señales; no llama a ningún service directamente.
El `RadioController` conecta estas señales con `RadioService`.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.radio_station import RadioStation


class _BitrateItem(QTableWidgetItem):
    """QTableWidgetItem que ordena el bitrate numéricamente."""

    def __lt__(self, other: "QTableWidgetItem") -> bool:
        return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)


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
        export_saved_requested():
            El usuario quiere exportar todas las emisoras guardadas a M3U.
        export_radio_list_requested():
            El usuario quiere exportar la lista de radios a XLSX/PDF/CSV.
    """

    search_requested        = pyqtSignal(str, str, str)   # (query, country, genre)
    play_requested          = pyqtSignal(object)           # RadioStation
    stop_requested          = pyqtSignal()
    save_requested          = pyqtSignal(object)           # RadioStation
    delete_requested        = pyqtSignal(int)              # station_id
    favorite_toggled        = pyqtSignal(int)              # station_id
    export_saved_requested       = pyqtSignal()   # exportar emisoras guardadas a M3U
    export_radio_list_requested  = pyqtSignal()   # exportar lista de radios a XLSX/PDF/CSV

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadioPanel")
        self._all_saved_stations: list[RadioStation] = []
        self._all_fav_stations: list[RadioStation] = []
        self._build_ui()
        self._connect_internal()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("RadioTabs")
        self._tabs.addTab(self._build_search_tab(),  "Buscar")
        self._tabs.addTab(self._build_saved_tab(),   "Guardadas")
        self._tabs.addTab(self._build_favs_tab(),    "Favoritas")
        root.addWidget(self._tabs)

        self._now_playing_label = QLabel("Sin emisora en reproducción")
        self._now_playing_label.setObjectName("RadioNowPlaying")
        self._now_playing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._now_playing_label)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

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
            btn_row.addWidget(btn, stretch=1)

        root.addLayout(btn_row)

    def _build_search_tab(self) -> QWidget:
        """Pestaña de búsqueda: campos + tabla de resultados."""
        tab = QWidget()
        tab.setObjectName("RadioSearchTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(6)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setObjectName("RadioSearchInput")
        self._search_input.setPlaceholderText("Nombre de la emisora…")

        self._country_input = QLineEdit()
        self._country_input.setObjectName("RadioCountryInput")
        self._country_input.setPlaceholderText("País (ej: AR)")
        self._country_input.setMaximumWidth(160)

        self._genre_input = QLineEdit()
        self._genre_input.setObjectName("RadioGenreInput")
        self._genre_input.setPlaceholderText("Género (ej: rock)")
        self._genre_input.setMaximumWidth(160)

        self._btn_search = QPushButton("Buscar")
        self._btn_search.setObjectName("RadioBtnSearch")
        self._btn_search.setDefault(True)
        self._btn_search.setMinimumWidth(100)

        search_row.addWidget(self._search_input)
        search_row.addWidget(self._country_input)
        search_row.addWidget(self._genre_input)
        search_row.addWidget(self._btn_search)
        layout.addLayout(search_row)

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
        self._results_list.setSortingEnabled(True)
        layout.addWidget(self._results_list)

        return tab

    def _build_saved_tab(self) -> QWidget:
        """Pestaña de emisoras guardadas con barra de filtro local."""
        tab = QWidget()
        tab.setObjectName("RadioSavedTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(6)

        filter_row = QHBoxLayout()
        self._saved_filter_input = QLineEdit()
        self._saved_filter_input.setObjectName("RadioSearchInput")
        self._saved_filter_input.setPlaceholderText("Nombre de la emisora…")

        self._saved_country_filter = QLineEdit()
        self._saved_country_filter.setObjectName("RadioCountryInput")
        self._saved_country_filter.setPlaceholderText("País (ej: AR)")
        self._saved_country_filter.setMaximumWidth(160)

        self._saved_genre_filter = QLineEdit()
        self._saved_genre_filter.setObjectName("RadioGenreInput")
        self._saved_genre_filter.setPlaceholderText("Género (ej: rock)")
        self._saved_genre_filter.setMaximumWidth(160)

        self._btn_saved_filter = QPushButton("Buscar")
        self._btn_saved_filter.setObjectName("RadioBtnSearch")
        self._btn_saved_filter.setMinimumWidth(80)

        self._btn_export_saved = QPushButton("Exportar Radio")
        self._btn_export_saved.setObjectName("RadioBtnExport")
        self._btn_export_list = QPushButton("Exportar Lista de Radios")
        self._btn_export_list.setObjectName("RadioBtnExportList")

        filter_row.addWidget(self._saved_filter_input)
        filter_row.addWidget(self._saved_country_filter)
        filter_row.addWidget(self._saved_genre_filter)
        filter_row.addWidget(self._btn_saved_filter)
        filter_row.addWidget(self._btn_export_saved)
        filter_row.addWidget(self._btn_export_list)
        layout.addLayout(filter_row)

        self._saved_table = QTableWidget()
        self._saved_table.setObjectName("RadioSavedTable")
        self._saved_table.setColumnCount(4)
        self._saved_table.setHorizontalHeaderLabels(["Nombre", "País", "Género", "Bitrate"])
        self._saved_table.setAlternatingRowColors(True)
        self._saved_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._saved_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._saved_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._saved_table.verticalHeader().setVisible(False)
        self._saved_table.setShowGrid(False)
        self._saved_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        header = self._saved_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._saved_table.setColumnWidth(1, 60)
        self._saved_table.setColumnWidth(2, 110)
        self._saved_table.setColumnWidth(3, 75)
        self._saved_table.setSortingEnabled(True)
        layout.addWidget(self._saved_table)

        return tab

    def _build_favs_tab(self) -> QWidget:
        """Pestaña de emisoras favoritas con barra de filtro local."""
        tab = QWidget()
        tab.setObjectName("RadioFavsTab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(6)

        filter_row = QHBoxLayout()
        self._favs_filter_input = QLineEdit()
        self._favs_filter_input.setObjectName("RadioSearchInput")
        self._favs_filter_input.setPlaceholderText("Nombre de la emisora…")

        self._favs_country_filter = QLineEdit()
        self._favs_country_filter.setObjectName("RadioCountryInput")
        self._favs_country_filter.setPlaceholderText("País (ej: AR)")
        self._favs_country_filter.setMaximumWidth(160)

        self._favs_genre_filter = QLineEdit()
        self._favs_genre_filter.setObjectName("RadioGenreInput")
        self._favs_genre_filter.setPlaceholderText("Género (ej: rock)")
        self._favs_genre_filter.setMaximumWidth(160)

        self._btn_favs_filter = QPushButton("Buscar")
        self._btn_favs_filter.setObjectName("RadioBtnSearch")
        self._btn_favs_filter.setMinimumWidth(100)

        filter_row.addWidget(self._favs_filter_input)
        filter_row.addWidget(self._favs_country_filter)
        filter_row.addWidget(self._favs_genre_filter)
        filter_row.addWidget(self._btn_favs_filter)
        layout.addLayout(filter_row)

        self._favs_table = QTableWidget()
        self._favs_table.setObjectName("RadioFavsTable")
        self._favs_table.setColumnCount(4)
        self._favs_table.setHorizontalHeaderLabels(["Nombre", "País", "Género", "Bitrate"])
        self._favs_table.setAlternatingRowColors(True)
        self._favs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._favs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._favs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._favs_table.verticalHeader().setVisible(False)
        self._favs_table.setShowGrid(False)
        self._favs_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        header = self._favs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._favs_table.setColumnWidth(1, 60)
        self._favs_table.setColumnWidth(2, 110)
        self._favs_table.setColumnWidth(3, 75)
        self._favs_table.setSortingEnabled(True)
        layout.addWidget(self._favs_table)

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
        self._btn_export_saved.clicked.connect(self.export_saved_requested)
        self._btn_export_list.clicked.connect(self.export_radio_list_requested)

        # Filtros locales — Guardadas
        self._btn_saved_filter.clicked.connect(self._apply_saved_filter)
        self._saved_filter_input.returnPressed.connect(self._apply_saved_filter)
        self._saved_filter_input.textChanged.connect(self._apply_saved_filter)
        self._saved_country_filter.textChanged.connect(self._apply_saved_filter)
        self._saved_genre_filter.textChanged.connect(self._apply_saved_filter)

        # Filtros locales — Favoritas
        self._btn_favs_filter.clicked.connect(self._apply_favs_filter)
        self._favs_filter_input.returnPressed.connect(self._apply_favs_filter)
        self._favs_filter_input.textChanged.connect(self._apply_favs_filter)
        self._favs_country_filter.textChanged.connect(self._apply_favs_filter)
        self._favs_genre_filter.textChanged.connect(self._apply_favs_filter)

        # Doble clic en cualquier tabla → reproducir
        self._results_list.doubleClicked.connect(self._on_play_clicked)
        self._saved_table.doubleClicked.connect(self._on_play_clicked)
        self._favs_table.doubleClicked.connect(self._on_play_clicked)

        # Actualizar botones según selección activa
        self._tabs.currentChanged.connect(self._update_buttons)
        self._results_list.itemSelectionChanged.connect(self._update_buttons)
        self._saved_table.itemSelectionChanged.connect(self._update_buttons)
        self._favs_table.itemSelectionChanged.connect(self._update_buttons)

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
        tab_idx    = self._tabs.currentIndex()
        has_result = self._selected_from_results() is not None
        has_saved  = self._selected_saved_station() is not None
        has_any    = self._selected_station() is not None

        self._btn_play.setEnabled(has_any)
        self._btn_save.setEnabled(tab_idx == 0 and has_result)
        self._btn_delete.setEnabled(tab_idx in (1, 2) and has_saved)
        self._btn_fav.setEnabled(tab_idx in (1, 2) and has_saved)

    # ------------------------------------------------------------------
    # Filtros locales
    # ------------------------------------------------------------------

    def _apply_saved_filter(self) -> None:
        name    = self._saved_filter_input.text().strip().lower()
        country = self._saved_country_filter.text().strip().lower()
        genre   = self._saved_genre_filter.text().strip().lower()
        filtered = [
            s for s in self._all_saved_stations
            if (not name    or name    in s.name.lower())
            and (not country or country in (s.country or "").lower())
            and (not genre   or genre   in (s.genre   or "").lower())
        ]
        self._populate_table(self._saved_table, filtered)

    def _apply_favs_filter(self) -> None:
        name    = self._favs_filter_input.text().strip().lower()
        country = self._favs_country_filter.text().strip().lower()
        genre   = self._favs_genre_filter.text().strip().lower()
        filtered = [
            s for s in self._all_fav_stations
            if (not name    or name    in s.name.lower())
            and (not country or country in (s.country or "").lower())
            and (not genre   or genre   in (s.genre   or "").lower())
        ]
        self._populate_table(self._favs_table, filtered)

    # ------------------------------------------------------------------
    # Helpers de selección
    # ------------------------------------------------------------------

    def _selected_station(self) -> RadioStation | None:
        tab_idx = self._tabs.currentIndex()
        if tab_idx == 0:
            return self._station_from_table(self._results_list)
        if tab_idx == 1:
            return self._station_from_table(self._saved_table)
        return self._station_from_table(self._favs_table)

    def _selected_from_results(self) -> RadioStation | None:
        return self._station_from_table(self._results_list)

    def _selected_saved_station(self) -> RadioStation | None:
        tab_idx = self._tabs.currentIndex()
        if tab_idx == 1:
            return self._station_from_table(self._saved_table)
        if tab_idx == 2:
            return self._station_from_table(self._favs_table)
        return None

    @staticmethod
    def _station_from_table(table: QTableWidget) -> RadioStation | None:
        rows = table.selectedItems()
        if not rows:
            return None
        return table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # API pública (llamada por el controller)
    # ------------------------------------------------------------------

    def set_search_results(self, stations: list[RadioStation]) -> None:
        """Muestra los resultados de búsqueda en la tabla de la pestaña Buscar."""
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
            bitrate_item = _BitrateItem(bitrate_text)
            bitrate_item.setData(Qt.ItemDataRole.UserRole, station.bitrate_kbps or 0)
            bitrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            self._results_list.setItem(row, 0, name_item)
            self._results_list.setItem(row, 1, country_item)
            self._results_list.setItem(row, 2, genre_item)
            self._results_list.setItem(row, 3, bitrate_item)

        self._results_list.resizeRowsToContents()
        self._update_buttons()

    def set_saved_stations(self, stations: list[RadioStation]) -> None:
        """Almacena y muestra las emisoras guardadas aplicando el filtro activo."""
        self._all_saved_stations = stations
        self._apply_saved_filter()

    def set_favorite_stations(self, stations: list[RadioStation]) -> None:
        """Almacena y muestra las emisoras favoritas aplicando el filtro activo."""
        self._all_fav_stations = stations
        self._apply_favs_filter()

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

    # ------------------------------------------------------------------
    # Helpers de poblado de tabla (compartido por Guardadas y Favoritas)
    # ------------------------------------------------------------------

    @staticmethod
    def _populate_table(table: QTableWidget, stations: list[RadioStation]) -> None:
        table.setRowCount(0)
        table.setRowCount(len(stations))
        for row, station in enumerate(stations):
            name_text = f"♥  {station.name}" if station.is_favorite else station.name
            name_item = QTableWidgetItem(name_text)
            name_item.setData(Qt.ItemDataRole.UserRole, station)
            name_item.setToolTip(station.stream_url)

            country_item = QTableWidgetItem(station.country or "")
            country_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            genre_item = QTableWidgetItem(station.genre or "")
            genre_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            bitrate_text = f"{station.bitrate_kbps} kbps" if station.bitrate_kbps else ""
            bitrate_item = _BitrateItem(bitrate_text)
            bitrate_item.setData(Qt.ItemDataRole.UserRole, station.bitrate_kbps or 0)
            bitrate_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            table.setItem(row, 0, name_item)
            table.setItem(row, 1, country_item)
            table.setItem(row, 2, genre_item)
            table.setItem(row, 3, bitrate_item)

        table.resizeRowsToContents()
