"""
LibraryController — Bisagra entre LibraryPanel y LibraryService.

Responsabilidades:
    - Conectar las señales de LibraryPanel con LibraryService.
    - Escuchar app_events para refrescar la UI cuando cambia la biblioteca.
    - Cargar el árbol y la tabla de pistas según la selección del usuario.
    - Arrancar la reproducción al hacer doble clic en una pista.

No contiene lógica de negocio.
"""
from __future__ import annotations

import logging

from audiorep.core.events import app_events
from audiorep.domain.track import Track
from audiorep.services.library_service import LibraryService
from audiorep.services.player_service import PlayerService
from audiorep.ui.widgets.library_panel import LibraryPanel

logger = logging.getLogger(__name__)


class LibraryController:
    """
    Controller de la biblioteca musical.

    Args:
        library_service: Servicio de biblioteca.
        player_service:  Servicio de reproducción (para play al doble clic).
        library_panel:   Widget del panel de biblioteca.
    """

    def __init__(
        self,
        library_service: LibraryService,
        player_service: PlayerService,
        library_panel: LibraryPanel,
    ) -> None:
        self._library = library_service
        self._player  = player_service
        self._panel   = library_panel

        self._connect_panel()
        self._connect_app_events()

        # Cargar estado inicial
        self._refresh_tree()
        self._load_all_music()

        logger.debug("LibraryController iniciado.")

    # ------------------------------------------------------------------
    # Conexiones: LibraryPanel → LibraryService / PlayerService
    # ------------------------------------------------------------------

    def _connect_panel(self) -> None:
        panel = self._panel
        panel.import_requested.connect(self._on_import_requested)
        panel.track_double_clicked.connect(self._on_track_double_clicked)
        panel.artist_selected.connect(self._on_artist_selected)
        panel.album_selected.connect(self._on_album_selected)
        panel.all_music_selected.connect(self._load_all_music)

    # ------------------------------------------------------------------
    # Conexiones: app_events → UI
    # ------------------------------------------------------------------

    def _connect_app_events(self) -> None:
        app_events.library_updated.connect(self._on_library_updated)
        app_events.scan_progress.connect(self._on_scan_progress)

    # ------------------------------------------------------------------
    # Handlers: panel
    # ------------------------------------------------------------------

    def _on_import_requested(self, directory: str) -> None:
        """Inicia la importación y conecta el progreso al panel."""
        importer = self._library.import_directory(directory)

        # Conectar señales del importer al panel para actualización en vivo
        importer.track_imported.connect(self._on_track_imported_live)
        importer.finished_import.connect(self._on_import_finished)

        app_events.status_message.emit(f"Importando: {directory} …")
        logger.info("Importación iniciada: %s", directory)

    def _on_track_double_clicked(self, track: Track) -> None:
        """
        El usuario hizo doble clic en una pista.
        Carga la vista actual como cola y arranca desde esa pista.
        """
        visible_tracks = self._panel.get_selected_tracks()
        if not visible_tracks:
            # Si nada seleccionado, usar solo la pista clickeada
            visible_tracks = [track]

        # Si hay más de una seleccionada, reproducir las seleccionadas
        # Si no, cargar toda la vista como cola y arrancar en la pista clickeada
        if len(visible_tracks) == 1:
            # Cargar toda la vista como cola
            all_visible = self._get_all_visible_tracks()
            try:
                start = all_visible.index(track)
            except ValueError:
                start = 0
            self._player.set_queue(all_visible, start_index=start)
        else:
            self._player.set_queue(visible_tracks, start_index=0)

    def _on_artist_selected(self, artist_id: int) -> None:
        tracks = self._library.get_tracks_by_artist(artist_id)
        # Buscar el nombre del artista para el label
        artists = self._library.get_all_artists()
        artist = next((a for a in artists if a.id == artist_id), None)
        label = f"🎤  {artist.name}" if artist else "Artista"
        self._panel.set_tracks(tracks, context_label=label)

    def _on_album_selected(self, album_id: int) -> None:
        tracks = self._library.get_tracks_by_album(album_id)
        albums = self._library.get_all_albums()
        album = next((a for a in albums if a.id == album_id), None)
        label = f"💿  {album.display_title()}" if album else "Álbum"
        self._panel.set_tracks(tracks, context_label=label)

    # ------------------------------------------------------------------
    # Handlers: app_events
    # ------------------------------------------------------------------

    def _on_library_updated(self) -> None:
        """La biblioteca cambió: refrescar el árbol."""
        self._refresh_tree()

    def _on_scan_progress(self, current: int, total: int) -> None:
        self._panel.show_import_progress(current, total)

    def _on_track_imported_live(self, track: Track) -> None:
        """Durante la importación, agrega pistas a la tabla en tiempo real."""
        self._panel.append_track(track)

    def _on_import_finished(self, imported: int, skipped: int) -> None:
        app_events.status_message.emit(
            f"Importación completa: {imported} pistas importadas, {skipped} omitidas."
        )
        self._refresh_tree()
        logger.info("Importación finalizada: %d importadas, %d omitidas.", imported, skipped)

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _refresh_tree(self) -> None:
        """Recarga el árbol de artistas y álbumes desde la BD."""
        artists = self._library.get_all_artists()
        albums_by_artist: dict[int, list] = {}
        for artist in artists:
            if artist.id is not None:
                albums_by_artist[artist.id] = self._library.get_albums_by_artist(artist.id)
        self._panel.populate_tree(artists, albums_by_artist)

    def _load_all_music(self) -> None:
        """Carga todas las pistas en la tabla."""
        tracks = self._library.get_all_tracks()
        self._panel.set_tracks(tracks, context_label="🎵  Toda la música")

    def _get_all_visible_tracks(self) -> list[Track]:
        """
        Obtiene todas las pistas actualmente visibles en la tabla
        (respetando el filtro de búsqueda activo).
        """
        # Acceder al proxy model a través del panel
        proxy = self._panel._proxy_model
        source = self._panel._track_model
        tracks = []
        for row in range(proxy.rowCount()):
            source_row = proxy.mapToSource(proxy.index(row, 0)).row()
            track = source.track_at(source_row)
            if track:
                tracks.append(track)
        return tracks
