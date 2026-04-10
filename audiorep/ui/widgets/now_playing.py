"""
NowPlaying — Widget que muestra la información de la pista en reproducción.

Muestra:
    - Portada del álbum (cuadrada, escalada con antialiasing)
    - Título de la pista
    - Nombre del artista
    - Título del álbum
    - Puntuación (rating) de 0 a 5 estrellas

Este widget no llama a ningún service; recibe datos a través de su API
pública, que el PlayerController invoca al recibir app_events.track_changed.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.track import Track

# Tamaño de la miniatura de portada en píxeles
_COVER_SIZE = 80

# Ruta a la imagen placeholder (se genera con texto si no existe el archivo)
_PLACEHOLDER_PATH = Path(__file__).parent.parent / "style" / "cover_placeholder.png"


class NowPlaying(QWidget):
    """
    Panel de información de la pista en reproducción.

    Señales:
        rating_changed(int): el usuario cambió la puntuación (0–5).
    """

    rating_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_track: Track | None = None
        self._rating: int = 0
        self._build_ui()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)

        # ── Portada ────────────────────────────────────────────────────
        self._cover_label = QLabel()
        self._cover_label.setFixedSize(_COVER_SIZE, _COVER_SIZE)
        self._cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cover_label.setObjectName("coverLabel")
        self._show_placeholder_cover()

        # ── Info textual ───────────────────────────────────────────────
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self._lbl_title = QLabel("Sin reproducción")
        self._lbl_title.setObjectName("trackTitle")
        self._lbl_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._lbl_title.setWordWrap(False)

        self._lbl_artist = QLabel("—")
        self._lbl_artist.setObjectName("trackArtist")

        self._lbl_album = QLabel("—")
        self._lbl_album.setObjectName("trackAlbum")

        self._lbl_rating = QLabel("☆☆☆☆☆")
        self._lbl_rating.setObjectName("trackRating")
        self._lbl_rating.setToolTip("Puntuación")

        info_layout.addWidget(self._lbl_title)
        info_layout.addWidget(self._lbl_artist)
        info_layout.addWidget(self._lbl_album)
        info_layout.addWidget(self._lbl_rating)
        info_layout.addStretch()

        layout.addWidget(self._cover_label)
        layout.addLayout(info_layout, 1)

    # ------------------------------------------------------------------
    # API pública — actualización desde el Controller
    # ------------------------------------------------------------------

    def update_track(self, track: Track) -> None:
        """Actualiza todos los campos con la información de la pista."""
        self._current_track = track

        # Texto con elipsis si es muy largo
        title  = track.title       or "Sin título"
        artist = track.artist_name or "Artista desconocido"
        album  = track.album_title or "Álbum desconocido"
        if track.year:
            album = f"{album} ({track.year})"

        self._lbl_title.setText(title)
        self._lbl_title.setToolTip(title)
        self._lbl_artist.setText(artist)
        self._lbl_album.setText(album)
        self._set_rating(track.rating)

        # Portada: intentar desde el disco, si no el placeholder
        self._load_cover(track)

    def update_cover(self, image_data: bytes) -> None:
        """Actualiza la portada desde datos binarios (descargada online)."""
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            self._apply_cover_pixmap(pixmap)

    def clear(self) -> None:
        """Vuelve al estado 'sin reproducción'."""
        self._current_track = None
        self._lbl_title.setText("Sin reproducción")
        self._lbl_artist.setText("—")
        self._lbl_album.setText("—")
        self._set_rating(0)
        self._show_placeholder_cover()

    # ------------------------------------------------------------------
    # Portada
    # ------------------------------------------------------------------

    def _load_cover(self, track: Track) -> None:
        """Intenta cargar la portada desde el álbum o un archivo embebido."""
        # 1. Desde la ruta de portada del álbum
        if track.album_id is not None:
            # El Controller puede llamar a update_cover() cuando la tenga
            pass

        # 2. Intentar cargar desde el directorio del archivo de audio
        if track.file_path:
            track_dir = Path(track.file_path).parent
            for name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png", "front.jpg"):
                candidate = track_dir / name
                if candidate.exists():
                    pixmap = QPixmap(str(candidate))
                    if not pixmap.isNull():
                        self._apply_cover_pixmap(pixmap)
                        return

        self._show_placeholder_cover()

    def _apply_cover_pixmap(self, pixmap: QPixmap) -> None:
        """Escala y muestra el pixmap con esquinas redondeadas."""
        scaled = pixmap.scaled(
            _COVER_SIZE, _COVER_SIZE,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # Recortar al cuadrado central
        x = (scaled.width()  - _COVER_SIZE) // 2
        y = (scaled.height() - _COVER_SIZE) // 2
        scaled = scaled.copy(x, y, _COVER_SIZE, _COVER_SIZE)

        # Esquinas redondeadas
        rounded = QPixmap(_COVER_SIZE, _COVER_SIZE)
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, _COVER_SIZE, _COVER_SIZE, 6, 6)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        self._cover_label.setPixmap(rounded)

    def _show_placeholder_cover(self) -> None:
        """Muestra un placeholder gris con nota musical."""
        pixmap = QPixmap(_COVER_SIZE, _COVER_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo redondeado
        path = QPainterPath()
        path.addRoundedRect(0, 0, _COVER_SIZE, _COVER_SIZE, 6, 6)
        from PyQt6.QtGui import QColor
        painter.fillPath(path, QColor("#2a2a3e"))

        # Nota musical centrada
        painter.setPen(QColor("#555577"))
        font = painter.font()
        font.setPointSize(28)
        painter.setFont(font)
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "♪",
        )
        painter.end()
        self._cover_label.setPixmap(pixmap)

    # ------------------------------------------------------------------
    # Rating
    # ------------------------------------------------------------------

    def _set_rating(self, rating: int) -> None:
        self._rating = max(0, min(5, rating))
        stars = "★" * self._rating + "☆" * (5 - self._rating)
        self._lbl_rating.setText(stars)
