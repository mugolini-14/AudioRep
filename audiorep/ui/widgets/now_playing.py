"""
NowPlaying — Panel izquierdo con portada y datos de la pista actual.

Muestra: portada (o placeholder), título, artista, álbum.
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
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._cover = QLabel()
        self._cover.setObjectName("nowPlayingCover")
        self._cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover.setMinimumSize(160, 160)
        self._cover.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._cover.setFixedHeight(180)
        self._show_placeholder()
        layout.addWidget(self._cover)

        self._title = QLabel("—")
        self._title.setObjectName("nowPlayingTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._artist = QLabel("—")
        self._artist.setObjectName("nowPlayingArtist")
        self._artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._artist.setWordWrap(True)
        layout.addWidget(self._artist)

        self._album = QLabel("—")
        self._album.setObjectName("nowPlayingAlbum")
        self._album.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._album.setWordWrap(True)
        layout.addWidget(self._album)

        layout.addStretch()

    def _show_placeholder(self) -> None:
        self._cover.setText("♪")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def update_track(self, track: Track) -> None:
        self._title.setText(track.title or "—")
        self._artist.setText(track.artist_name or "—")
        self._album.setText(track.album_title or "—")
        self._show_placeholder()

    def update_cover(self, image_data: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            scaled = pixmap.scaled(
                180, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cover.setPixmap(scaled)
        else:
            self._show_placeholder()

    def clear(self) -> None:
        self._title.setText("—")
        self._artist.setText("—")
        self._album.setText("—")
        self._show_placeholder()
