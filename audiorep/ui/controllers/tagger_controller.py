"""
TaggerController — Bisagra entre LibraryPanel y TaggerService.

Responsabilidades:
    - Abrir TagEditorDialog cuando el usuario lo solicita desde LibraryPanel.
    - Lanzar identificación por huella cromática.
    - Aplicar los metadatos seleccionados por el usuario.
"""
from __future__ import annotations

import logging

from audiorep.domain.track import Track
from audiorep.services.tagger_service import TaggerService
from audiorep.ui.widgets.library_panel import LibraryPanel

logger = logging.getLogger(__name__)


class TaggerController:
    """
    Controller de edición de tags.

    Args:
        tagger_service: Servicio de tagger.
        library_panel:  Panel de biblioteca (fuente de la selección de pista).
    """

    def __init__(
        self,
        tagger_service: TaggerService,
        library_panel:  LibraryPanel,
    ) -> None:
        self._service = tagger_service
        self._panel   = library_panel

        self._connect_panel()
        self._connect_service()

        logger.debug("TaggerController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        self._panel.edit_tags_requested.connect(self._on_edit_tags)
        self._panel.identify_requested.connect(self._on_identify)

    def _connect_service(self) -> None:
        self._service.fingerprint_result.connect(self._on_fingerprint_result)
        self._service.fingerprint_error.connect(self._on_fingerprint_error)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_edit_tags(self, track: Track) -> None:
        from audiorep.ui.dialogs.tag_editor_dialog import TagEditorDialog
        dialog = TagEditorDialog(track=track, parent=self._panel)
        dialog.tags_saved.connect(
            lambda tags: self._service.apply_metadata(track, tags)
        )
        dialog.exec()

    def _on_identify(self, track: Track) -> None:
        from audiorep.core.events import app_events
        app_events.status_message.emit(f"Identificando: {track.title} …")
        self._service.identify_track(track)

    def _on_fingerprint_result(self, track: Track, candidates: list) -> None:
        if not candidates:
            from audiorep.core.events import app_events
            app_events.status_message.emit("No se encontraron candidatos.")
            return
        from audiorep.ui.dialogs.tag_editor_dialog import TagEditorDialog
        dialog = TagEditorDialog(track=track, candidates=candidates, parent=self._panel)
        dialog.tags_saved.connect(
            lambda tags: self._service.apply_metadata(track, tags)
        )
        dialog.exec()

    def _on_fingerprint_error(self, track: Track, message: str) -> None:
        from audiorep.core.events import app_events
        app_events.error_occurred.emit("Error de identificación", message)
