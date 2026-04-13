"""
TagEditorDialog — Editor de tags / metadatos de una pista.

Permite editar manualmente los campos de una pista, o seleccionar
un candidato de identificación por huella cromática.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from audiorep.domain.track import Track

logger = logging.getLogger(__name__)


class TagEditorDialog(QDialog):
    """
    Diálogo de edición de tags.

    Args:
        track:      Pista a editar.
        candidates: Lista de candidatos de identificación (opcional).
        parent:     Widget padre.

    Signals:
        tags_saved: Emitido con el dict de tags cuando el usuario acepta.
    """

    tags_saved = pyqtSignal(dict)

    def __init__(
        self,
        track: Track,
        candidates: list[dict] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._track = track
        self._candidates = candidates or []

        self.setWindowTitle("Editor de tags")
        self.setMinimumWidth(480)
        self.setObjectName("TagEditorDialog")

        layout = QVBoxLayout(self)

        # ── Candidatos (si los hay) ────────────────────────────────── #
        if self._candidates:
            candidates_box = QGroupBox("Candidatos encontrados")
            candidates_box.setObjectName("TagEditorCandidatesBox")
            cand_layout = QVBoxLayout(candidates_box)
            self._candidates_list = QListWidget()
            self._candidates_list.setObjectName("TagEditorCandidatesList")
            for c in self._candidates:
                title  = c.get("title", "?")
                artist = c.get("artist", "?")
                score  = c.get("score", 0.0)
                item = QListWidgetItem(
                    f"{artist} — {title}  (score: {score:.2f})"
                )
                item.setData(256, c)  # Qt.UserRole = 256
                self._candidates_list.addItem(item)
            self._candidates_list.currentItemChanged.connect(self._on_candidate_selected)
            cand_layout.addWidget(self._candidates_list)
            layout.addWidget(candidates_box)

        # ── Formulario de tags ─────────────────────────────────────── #
        form_box = QGroupBox("Tags")
        form_box.setObjectName("TagEditorFormBox")
        form = QFormLayout(form_box)

        self._title_edit  = QLineEdit(track.title or "")
        self._artist_edit = QLineEdit(track.artist_name or "")
        self._album_edit  = QLineEdit(track.album_title or "")
        self._year_edit   = QLineEdit(str(track.year) if track.year else "")
        self._genre_edit  = QLineEdit(track.genre or "")
        self._track_edit  = QLineEdit(str(track.track_number) if track.track_number else "")

        for widget in (
            self._title_edit, self._artist_edit, self._album_edit,
            self._year_edit, self._genre_edit, self._track_edit,
        ):
            widget.setObjectName("TagEditorField")

        form.addRow("Título:",    self._title_edit)
        form.addRow("Artista:",   self._artist_edit)
        form.addRow("Álbum:",     self._album_edit)
        form.addRow("Año:",       self._year_edit)
        form.addRow("Género:",    self._genre_edit)
        form.addRow("N.º pista:", self._track_edit)
        layout.addWidget(form_box)

        # ── Botones ────────────────────────────────────────────────── #
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_candidate_selected(self, current: QListWidgetItem | None, _) -> None:
        if current is None:
            return
        data: dict = current.data(256)
        self._title_edit.setText(data.get("title", ""))
        self._artist_edit.setText(data.get("artist", ""))
        self._album_edit.setText(data.get("album", ""))
        year = data.get("year", "")
        self._year_edit.setText(str(year) if year else "")
        self._genre_edit.setText(data.get("genre", ""))
        tn = data.get("track_number", "")
        self._track_edit.setText(str(tn) if tn else "")

    def _on_save(self) -> None:
        try:
            year = int(self._year_edit.text()) if self._year_edit.text().strip() else None
        except ValueError:
            year = None
        try:
            track_number = int(self._track_edit.text()) if self._track_edit.text().strip() else 0
        except ValueError:
            track_number = 0

        # Include recording_id from selected candidate if available
        recording_id = None
        if self._candidates:
            item = getattr(self, "_candidates_list", None)
            if item:
                current = item.currentItem()
                if current:
                    recording_id = current.data(256).get("recording_id")

        tags = {
            "title":        self._title_edit.text().strip(),
            "artist":       self._artist_edit.text().strip(),
            "album":        self._album_edit.text().strip(),
            "year":         year,
            "genre":        self._genre_edit.text().strip(),
            "track_number": track_number,
        }
        if recording_id:
            tags["recording_id"] = recording_id

        self.tags_saved.emit(tags)
        self.accept()
