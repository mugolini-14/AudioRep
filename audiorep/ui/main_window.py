"""
MainWindow — Ventana principal de AudioRep.

Layout general:
    ┌──────────────────────────────────────────────┐
    │  NowPlaying  │  [Biblioteca] [CD]  ← tabs   │
    │  (portada +  │  LibraryPanel / CDPanel       │
    │   info)      │                               │
    ├──────────────────────────────────────────────┤
    │  Barra de estado                             │
    ├──────────────────────────────────────────────┤
    │  PlayerBar (controles + progreso + volumen)  │
    └──────────────────────────────────────────────┘

Responsabilidades:
    - Instanciar y disponer todos los widgets.
    - Instanciar los controllers inyectando services y widgets.
    - Cargar el tema visual (QSS).
    - Gestionar el ciclo de vida de la ventana (closeEvent).

NO contiene lógica de negocio.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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
from audiorep.services.cd_service import CDService
from audiorep.services.library_service import LibraryService
from audiorep.services.player_service import PlayerService
from audiorep.ui.controllers.cd_controller import CDController
from audiorep.ui.controllers.library_controller import LibraryController
from audiorep.ui.controllers.player_controller import PlayerController
from audiorep.ui.widgets.cd_panel import CDPanel
from audiorep.ui.widgets.library_panel import LibraryPanel
from audiorep.ui.widgets.now_playing import NowPlaying
from audiorep.ui.widgets.player_bar import PlayerBar

logger = logging.getLogger(__name__)

_STYLE_DIR = Path(__file__).parent / "style"


class MainWindow(QMainWindow):
    """
    Ventana principal de AudioRep.

    Args:
        player_service: Servicio de reproducción (obligatorio).
        Resto de services se agregarán en pasos sucesivos.
    """

    def __init__(
        self,
        player_service: PlayerService,
        library_service: LibraryService,
        cd_service: CDService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._player_service  = player_service
        self._library_service = library_service
        self._cd_service      = cd_service

        self._setup_window()
        self._build_ui()
        self._setup_controllers()
        self._load_stylesheet()
        self._connect_events()

        logger.debug("MainWindow construida.")

    # ------------------------------------------------------------------
    # Configuración de la ventana
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("AudioRep")
        self.setMinimumSize(800, 500)
        self.resize(1100, 680)

    # ------------------------------------------------------------------
    # Construcción del layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Widget raíz
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Área principal (NowPlaying + panel central) ────────────────
        root_layout.addWidget(self._build_main_area(), stretch=1)

        # ── Separador ─────────────────────────────────────────────────
        root_layout.addWidget(self._make_separator())

        # ── PlayerBar ─────────────────────────────────────────────────
        self._player_bar = PlayerBar()
        self._player_bar.setObjectName("playerBar")
        root_layout.addWidget(self._player_bar)

        # ── Barra de estado ───────────────────────────────────────────
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusBar")
        self._status_bar.showMessage("AudioRep listo.")
        self.setStatusBar(self._status_bar)

    def _build_main_area(self) -> QSplitter:
        """
        Splitter horizontal:
            izquierda → NowPlaying (ancho fijo ~260 px)
            derecha   → Panel central (biblioteca, placeholder por ahora)
        """
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(1)

        # NowPlaying
        self._now_playing = NowPlaying()
        self._now_playing.setObjectName("nowPlayingPanel")
        self._now_playing.setMinimumWidth(220)
        self._now_playing.setMaximumWidth(320)
        self._now_playing.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

        # Tabs: Biblioteca / CD
        self._tabs = QTabWidget()
        self._tabs.setObjectName("mainTabs")
        self._tabs.setDocumentMode(True)

        self._library_panel = LibraryPanel()
        self._library_panel.setObjectName("libraryPanel")
        self._tabs.addTab(self._library_panel, "🎵  Biblioteca")

        self._cd_panel = CDPanel()
        self._cd_panel.setObjectName("cdPanel")
        self._tabs.addTab(self._cd_panel, "💿  CD")

        splitter.addWidget(self._now_playing)
        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        return sep

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
            now_playing=self._now_playing,
        )
        # Pasos futuros: TaggerController, etc.

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------

    def _load_stylesheet(self) -> None:
        qss_path = _STYLE_DIR / "dark.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))
            logger.debug("Tema cargado: %s", qss_path)
        else:
            logger.warning("Archivo de tema no encontrado: %s", qss_path)

    # ------------------------------------------------------------------
    # Eventos globales → barra de estado
    # ------------------------------------------------------------------

    def _connect_events(self) -> None:
        app_events.status_message.connect(self._status_bar.showMessage)
        app_events.error_occurred.connect(self._on_error)
        app_events.track_changed.connect(self._on_track_changed)
        # Cambiar al tab de CD automáticamente cuando se inserta un disco
        app_events.cd_inserted.connect(self._on_cd_inserted)

    def _on_error(self, title: str, detail: str) -> None:
        self._status_bar.showMessage(f"⚠ {title}: {detail}", 5000)
        logger.error("%s — %s", title, detail)

    def _on_track_changed(self, track) -> None:  # type: ignore[override]
        artist = track.artist_name or "Desconocido"
        self.setWindowTitle(f"{track.title} — {artist}  ·  AudioRep")
        self._status_bar.showMessage(f"▶  {track.title}  —  {artist}")

    def _on_cd_inserted(self, _disc_id: str) -> None:
        """Cambia automáticamente al tab de CD cuando se inserta un disco."""
        self._tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Detiene la reproducción limpiamente antes de cerrar."""
        self._player_service.stop()
        logger.info("Aplicación cerrada.")
        super().closeEvent(event)
