"""
NowPlaying — Panel izquierdo con portada y datos de la pista actual.

objectNames alineados con dark.qss:
    coverLabel, trackTitle, trackArtist, trackAlbum, trackRating
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from audiorep.domain.track import Track


class NowPlaying(QWidget):
    """Widget de información de la pista actual."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nowPlayingPanel")
        self._current_cover: bytes | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)

        self._cover = QLabel()
        self._cover.setObjectName("coverLabel")
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setFixedHeight(190)
        self._cover.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._show_placeholder()
        layout.addWidget(self._cover)

        self._title = QLabel("—")
        self._title.setObjectName("trackTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._artist = QLabel("—")
        self._artist.setObjectName("trackArtist")
        self._artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._artist.setWordWrap(True)
        layout.addWidget(self._artist)

        self._album = QLabel("—")
        self._album.setObjectName("trackAlbum")
        self._album.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._album.setWordWrap(True)
        layout.addWidget(self._album)

        self._rating = QLabel("")
        self._rating.setObjectName("trackRating")
        self._rating.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._rating)

        layout.addStretch()

    def _show_placeholder(self) -> None:
        self._cover.setPixmap(QPixmap())
        self._cover.setText("♪")

    @staticmethod
    def _rating_stars(rating: int) -> str:
        stars = min(max(rating, 0), 5)
        return "★" * stars + "☆" * (5 - stars) if stars > 0 else ""

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def update_track(self, track: Track) -> None:
        self._title.setText(track.title or "—")
        self._artist.setText(track.artist_name or "—")
        self._album.setText(track.album_title or "—")
        self._rating.setText(self._rating_stars(track.rating))
        # Re-aplicar portada almacenada; si no hay, mostrar placeholder
        if self._current_cover:
            self._apply_cover(self._current_cover)
        else:
            self._show_placeholder()

    def update_cover(self, image_data: bytes) -> None:
        self._current_cover = image_data
        self._apply_cover(image_data)

    def clear_cover(self) -> None:
        """Limpia sólo la portada (ej. al eyectar el CD), sin tocar título/artista."""
        self._current_cover = None
        self._show_placeholder()

    def clear(self) -> None:
        self._current_cover = None
        self._title.setText("—")
        self._artist.setText("—")
        self._album.setText("—")
        self._rating.setText("")
        self._show_placeholder()

    def _apply_cover(self, image_data: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            scaled = pixmap.scaled(
                190, 190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cover.setPixmap(scaled)
            self._cover.setText("")
        else:
            self._show_placeholder()
