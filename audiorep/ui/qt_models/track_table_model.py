"""
TrackTableModel — QAbstractTableModel para mostrar pistas en una tabla.

Columnas: #, Título, Artista, Álbum, Año, Género, Duración, Formato
"""
from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from audiorep.domain.track import Track

_COLUMNS = ["#", "Título", "Artista", "Álbum", "Año", "Género", "Duración", "Formato"]

_COL_INDEX    = 0
_COL_TITLE    = 1
_COL_ARTIST   = 2
_COL_ALBUM    = 3
_COL_YEAR     = 4
_COL_GENRE    = 5
_COL_DURATION = 6
_COL_FORMAT   = 7


def _sort_key(track: Track, column: int):
    if column == _COL_INDEX:
        return track.track_number or 0
    if column == _COL_TITLE:
        return (track.title or "").lower()
    if column == _COL_ARTIST:
        return (track.artist_name or "").lower()
    if column == _COL_ALBUM:
        return (track.album_title or "").lower()
    if column == _COL_YEAR:
        return track.year or 0
    if column == _COL_GENRE:
        return (track.genre or "").lower()
    if column == _COL_DURATION:
        return track.duration_ms or 0
    if column == _COL_FORMAT:
        return (track.format.value if track.format else "").lower()
    return ""


class TrackTableModel(QAbstractTableModel):
    """
    Modelo de tabla para pistas de audio.

    Uso:
        model = TrackTableModel()
        model.set_tracks(tracks)
        table_view.setModel(model)
    """

    def __init__(self, tracks: list[Track] | None = None) -> None:
        super().__init__()
        self._tracks: list[Track] = tracks or []
        self._sort_column: int = -1
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_tracks(self, tracks: list[Track]) -> None:
        self.beginResetModel()
        self._tracks = list(tracks)
        if self._sort_column >= 0:
            reverse = self._sort_order == Qt.SortOrder.DescendingOrder
            self._tracks.sort(key=lambda t: _sort_key(t, self._sort_column), reverse=reverse)
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        self.layoutAboutToBeChanged.emit()
        self._sort_column = column
        self._sort_order = order
        reverse = order == Qt.SortOrder.DescendingOrder
        self._tracks.sort(key=lambda t: _sort_key(t, column), reverse=reverse)
        self.layoutChanged.emit()

    def track_at(self, row: int) -> Track | None:
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def all_tracks(self) -> list[Track]:
        return list(self._tracks)

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._tracks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(_COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(_COLUMNS):
                    return _COLUMNS[section]
            else:
                return section + 1
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._tracks):
            return None
        track = self._tracks[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == _COL_INDEX:
                return row + 1
            if col == _COL_TITLE:
                return track.title
            if col == _COL_ARTIST:
                return track.artist_name
            if col == _COL_ALBUM:
                return track.album_title
            if col == _COL_YEAR:
                return str(track.year) if track.year else ""
            if col == _COL_GENRE:
                return track.genre
            if col == _COL_DURATION:
                return track.duration_str
            if col == _COL_FORMAT:
                return track.format.value if track.format else ""

        if role == Qt.ItemDataRole.UserRole:
            return track

        return None
