"""
MainWindow — Ventana principal de AudioRep.

Layout general:
    ┌──────────────────────────────────────────────────────┐
    │  [Biblioteca][CD][Playlists][Radio]  │  NowPlaying  │
    │  LibraryPanel / CDPanel /           │  (portada +  │
    │  PlaylistPanel / RadioPanel         │   info)      │
    │                                     ├──────────────┤
    │                                     │  VU Meter    │
    ├─────────────────────────────────────────────────────┤
    │  Barra de estado                                    │
    ├─────────────────────────────────────────────────────┤
    │  PlayerBar (controles + progreso + volumen)         │
    └─────────────────────────────────────────────────────┘

Responsabilidades:
    - Instanciar y disponer todos los widgets.
    - Instanciar los controllers inyectando services y widgets.
    - Cargar el tema visual (QSS).
    - Gestionar el menú de aplicación.
    - Gestionar el ciclo de vida de la ventana (closeEvent).

NO contiene lógica de negocio.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from audiorep.core.events import app_events
from audiorep.core.settings import AppSettings
from audiorep.services.cd_service import CDService
from audiorep.services.library_service import LibraryService
from audiorep.services.player_service import PlayerService
from audiorep.services.playlist_service import PlaylistService
from audiorep.services.radio_service import RadioService
from audiorep.services.ripper_service import RipperService
from audiorep.services.search_service import SearchService
from audiorep.services.tagger_service import TaggerService
from audiorep.ui.controllers.cd_controller import CDController
from audiorep.ui.controllers.library_controller import LibraryController
from audiorep.ui.controllers.player_controller import PlayerController
from audiorep.ui.controllers.playlist_controller import PlaylistController
from audiorep.ui.controllers.radio_controller import RadioController
from audiorep.ui.controllers.tagger_controller import TaggerController
from audiorep.ui.widgets.cd_metadata_panel import CDMetadataPanel
from audiorep.ui.widgets.cd_panel import CDPanel
from audiorep.ui.widgets.library_panel import LibraryPanel
from audiorep.ui.widgets.now_playing import NowPlaying
from audiorep.ui.widgets.player_bar import PlayerBar
from audiorep.ui.widgets.playlist_panel import PlaylistPanel
from audiorep.ui.widgets.radio_panel import RadioPanel
from audiorep.ui.widgets.vu_meter import VUMeterWidget

logger = logging.getLogger(__name__)

_STYLE_DIR = Path(__file__).parent / "style"


class MainWindow(QMainWindow):
    """
    Ventana principal de AudioRep.

    Args:
        player_service:   Servicio de reproducción (obligatorio).
        library_service:  Servicio de biblioteca.
        cd_service:       Servicio de CD.
        playlist_service: Servicio de playlists.
        search_service:   Servicio de búsqueda.
        ripper_service:   Servicio de ripeo de CD.
        tagger_service:   Servicio de tags y metadatos.
        radio_service:    Servicio de radio por internet.
        settings:         Configuración persistente de la aplicación.
    """

    def __init__(
        self,
        player_service:     PlayerService,
        library_service:    LibraryService,
        cd_service:         CDService,
        playlist_service:   PlaylistService,
        search_service:     SearchService,
        ripper_service:     RipperService,
        tagger_service:     TaggerService,
        radio_service:      RadioService | None = None,
        settings:           AppSettings | None = None,
        cd_lookup_providers: list | None = None,
        parent:             QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player_service      = player_service
        self._library_service     = library_service
        self._cd_service          = cd_service
        self._playlist_service    = playlist_service
        self._search_service      = search_service
        self._ripper_service      = ripper_service
        self._tagger_service      = tagger_service
        self._radio_service       = radio_service
        self._settings            = settings
        self._cd_lookup_providers = cd_lookup_providers or []

        self._setup_window()
        self._build_ui()
        self._setup_menu()
        self._setup_controllers()
        self._load_stylesheet()
        self._connect_events()

        logger.debug("MainWindow construida.")

    # ------------------------------------------------------------------
    # Configuración de la ventana
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("AudioRep 0.60")
        self.setMinimumSize(860, 520)
        self.resize(1200, 700)

    # ------------------------------------------------------------------
    # Construcción del layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_main_area(), stretch=1)
        root_layout.addWidget(self._make_separator())

        self._player_bar = PlayerBar()
        self._player_bar.setObjectName("playerBar")
        root_layout.addWidget(self._player_bar)

        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusBar")
        self._status_bar.showMessage("AudioRep listo.")
        self.setStatusBar(self._status_bar)

    def _build_main_area(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(1)

        # ── Pestañas (ocupa la mayor parte) ─────────────────────── #
        self._tabs = QTabWidget()
        self._tabs.setObjectName("mainTabs")
        self._tabs.setDocumentMode(True)

        self._library_panel = LibraryPanel()
        self._library_panel.setObjectName("libraryPanel")
        self._tabs.addTab(self._library_panel, "🎵  Biblioteca")

        self._cd_panel = CDPanel()
        self._cd_panel.setObjectName("cdPanel")
        self._cd_metadata_panel = CDMetadataPanel()
        cd_tab_widget = self._build_cd_tab()
        self._tabs.addTab(cd_tab_widget, "💿  CD")

        self._playlist_panel = PlaylistPanel()
        self._playlist_panel.setObjectName("playlistPanel")
        self._tabs.addTab(self._playlist_panel, "♫  Playlists")

        self._radio_panel = RadioPanel()
        self._radio_panel.setObjectName("radioPanel")
        self._tabs.addTab(self._radio_panel, "📻  Radio")

        # ── Panel derecho: NowPlaying + VU meter ─────────────────── #
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel.setMinimumWidth(210)
        right_panel.setMaximumWidth(320)
        right_panel.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._now_playing = NowPlaying()
        self._now_playing.setObjectName("nowPlayingPanel")
        right_layout.addWidget(self._now_playing, stretch=1)

        right_layout.addWidget(self._make_separator())

        self._vu_meter = VUMeterWidget()
        self._vu_meter.setObjectName("vuMeter")
        self._vu_meter.setFixedHeight(110)
        right_layout.addWidget(self._vu_meter)

        splitter.addWidget(self._tabs)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        return splitter

    def _build_cd_tab(self) -> QWidget:
        """
        Construye el contenido del tab CD: CDPanel (izq.) + CDMetadataPanel (der.).
        Usa un QSplitter horizontal para que el usuario pueda redimensionar.
        """
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("cdTabSplitter")
        splitter.setHandleWidth(1)
        splitter.addWidget(self._cd_panel)
        splitter.addWidget(self._cd_metadata_panel)
        splitter.setStretchFactor(0, 1)   # CDPanel expande
        splitter.setStretchFactor(1, 0)   # CDMetadataPanel ancho fijo preferido
        splitter.setSizes([700, 280])
        return splitter

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        return sep

    # ------------------------------------------------------------------
    # Menú
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()

        archivo = menu_bar.addMenu("Archivo")

        act_settings = QAction("⚙  Configuración…", self)
        act_settings.setShortcut("Ctrl+,")
        act_settings.triggered.connect(self._open_settings)
        archivo.addAction(act_settings)

        archivo.addSeparator()

        act_quit = QAction("Salir", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(QApplication.instance().quit)
        archivo.addAction(act_quit)

    def _open_settings(self) -> None:
        if self._settings is None:
            return
        from audiorep.ui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(settings=self._settings, parent=self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_settings_saved(self) -> None:
        tagger_controller = getattr(self, "_tagger_controller", None)
        if tagger_controller is not None:
            client = getattr(tagger_controller._service, "_fingerprinter", None)
            if client is not None and hasattr(client, "_api_key"):
                client._api_key = self._settings.acoustid_api_key  # type: ignore[union-attr]
        app_events.status_message.emit("Configuración guardada.")

    # ------------------------------------------------------------------
    # Controllers
    # ------------------------------------------------------------------

    def _setup_controllers(self) -> None:
        """Instancia los controllers inyectando services y widgets."""
        self._player_controller = PlayerController(
            service=self._player_service,
            player_bar=self._player_bar,
            now_playing=self._now_playing,
        )
        self._library_controller = LibraryController(
            library_service=self._library_service,
            player_service=self._player_service,
            library_panel=self._library_panel,
        )
        self._cd_controller = CDController(
            cd_service=self._cd_service,
            player_service=self._player_service,
            cd_panel=self._cd_panel,
            cd_metadata_panel=self._cd_metadata_panel,
            now_playing=self._now_playing,
            ripper_service=self._ripper_service,
            settings=self._settings,
            cd_lookup_providers=self._cd_lookup_providers,
        )
        self._playlist_controller = PlaylistController(
            playlist_service=self._playlist_service,
            player_service=self._player_service,
            playlist_panel=self._playlist_panel,
            library_panel=self._library_panel,
        )
        self._tagger_controller = TaggerController(
            tagger_service=self._tagger_service,
            library_panel=self._library_panel,
        )
        if self._radio_service is not None:
            self._radio_controller = RadioController(
                radio_service=self._radio_service,
                radio_panel=self._radio_panel,
            )

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _load_stylesheet(self) -> None:
        qss_path = _STYLE_DIR / "dark.qss"
        if qss_path.exists():
            qss = qss_path.read_text(encoding="utf-8")
            # Expand relative SVG URLs to absolute paths so they work
            # both from source and from a frozen PyInstaller bundle.
            qss = qss.replace("url(./", f"url({_STYLE_DIR.as_posix()}/")
            self.setStyleSheet(qss)
            logger.debug("Tema cargado: %s", qss_path)
        else:
            logger.warning("Archivo de tema no encontrado: %s", qss_path)

    # ------------------------------------------------------------------
    # Eventos globales
    # ------------------------------------------------------------------

    def _connect_events(self) -> None:
        app_events.status_message.connect(self._status_bar.showMessage)
        app_events.error_occurred.connect(self._on_error)
        app_events.track_changed.connect(self._on_track_changed)
        app_events.cd_inserted.connect(self._on_cd_inserted)

    def _on_error(self, title: str, detail: str) -> None:
        self._status_bar.showMessage(f"⚠ {title}: {detail}", 5000)
        logger.error("%s — %s", title, detail)

    def _on_track_changed(self, track) -> None:  # type: ignore[override]
        artist = track.artist_name or "Desconocido"
        self._status_bar.showMessage(f"▶  {track.title}  —  {artist}")

    def _on_cd_inserted(self, _disc_id: str) -> None:
        self._tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._player_service.stop()
        logger.info("Aplicación cerrada.")
        super().closeEvent(event)
