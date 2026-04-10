"""
TrackTableModel — QAbstractTableModel para mostrar pistas en un QTableView.

Columnas:
    0  #       (track_number)
    1  Título
    2  Artista
    3  Álbum
    4  Duración
    5  Año
    6  Género
    7  ★       (rating)

Soporta ordenamiento por cualquier columna.
"""
from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QColor

from audiorep.core.utils import format_duration
from audiorep.domain.track import Track

# Índices de columna
COL_NUMBER   = 0
COL_TITLE    = 1
COL_ARTIST   = 2
COL_ALBUM    = 3
COL_DURATION = 4
COL_YEAR     = 5
COL_GENRE    = 6
COL_RATING   = 7

_HEADERS = ["#", "Título", "Artista", "Álbum", "Duración", "Año", "Género", "★"]

# Rol personalizado para obtener el objeto Track completo
TrackRole = Qt.ItemDataRole.UserRole + 1


class TrackTableModel(QAbstractTableModel):
    """
    Modelo de tabla de pistas para QTableView.

    Uso típico:
        model = TrackTableModel()
        model.set_tracks(tracks)
        table_view.setModel(model)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tracks: list[Track] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[Track]) -> None:
        """Reemplaza los datos del modelo."""
        self.beginResetModel()
        self._tracks = list(tracks)
        self.endResetModel()

    def append_track(self, track: Track) -> None:
        """Agrega una pista al final sin resetear todo el modelo."""
        row = len(self._tracks)
        self.beginInsertRows(QModelIndex(), row, row)
        self._tracks.append(track)
        self.endInsertRows()

    def track_at(self, row: int) -> Track | None:
        """Retorna el Track en la fila indicada, o None."""
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def clear(self) -> None:
        self.set_tracks([])

    # ------------------------------------------------------------------
    # QAbstractTableModel — interfaz obligatoria
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole and orientation == Qt.Orientation.Horizontal:
            if section in (COL_NUMBER, COL_DURATION, COL_YEAR, COL_RATING):
                return Qt.AlignmentFlag.AlignCenter
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return None

        track = self._tracks[index.row()]
        col   = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_data(track, col)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (COL_NUMBER, COL_DURATION, COL_YEAR, COL_RATING):
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role == Qt.ItemDataRole.ForegroundRole:
            if col == COL_RATING and track.rating > 0:
                return QColor("#7c5cbf")
            if col == COL_DURATION:
                return QColor("#7070a0")
            if col in (COL_YEAR, COL_GENRE):
                return QColor("#8888aa")

        if role == TrackRole:
            return track

        return None

    @staticmethod
    def _display_data(track: Track, col: int):
        if col == COL_NUMBER:
            return str(track.track_number) if track.track_number else ""
        if col == COL_TITLE:
            return track.title
        if col == COL_ARTIST:
            return track.artist_name
        if col == COL_ALBUM:
            return track.album_title
        if col == COL_DURATION:
            return format_duration(track.duration_ms) if track.duration_ms else ""
        if col == COL_YEAR:
            return str(track.year) if track.year else ""
        if col == COL_GENRE:
            return track.genre
        if col == COL_RATING:
            return "★" * track.rating if track.rating else ""
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Ordena el modelo en memoria."""
        reverse = order == Qt.SortOrder.DescendingOrder

        key_funcs = {
            COL_NUMBER:   lambda t: t.track_number,
            COL_TITLE:    lambda t: t.title.lower(),
            COL_ARTIST:   lambda t: t.artist_name.lower(),
            COL_ALBUM:    lambda t: t.album_title.lower(),
            COL_DURATION: lambda t: t.duration_ms,
            COL_YEAR:     lambda t: t.year or 0,
            COL_GENRE:    lambda t: t.genre.lower(),
            COL_RATING:   lambda t: t.rating,
        }
        key = key_funcs.get(column, lambda t: t.title.lower())

        self.beginResetModel()
        self._tracks.sort(key=key, reverse=reverse)
        self.endResetModel()


def make_track_proxy_model(source: TrackTableModel) -> QSortFilterProxyModel:
    """
    Crea un proxy de filtrado/ordenamiento para un TrackTableModel.

    El filtro busca en Título, Artista y Álbum (columnas 1, 2, 3).
    """
    proxy = QSortFilterProxyModel()
    proxy.setSourceModel(source)
    proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    proxy.setFilterKeyColumn(-1)   # -1 = busca en todas las columnas
    proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    return proxy
