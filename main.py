"""
AudioRep — Punto de entrada de la aplicación.

Responsabilidad: composición raíz (dependency injection manual).
Instancia todas las capas y las conecta antes de arrancar la UI.

Estado de implementación:
    ✅ Paso 1  — domain/ + core/
    ✅ Paso 2  — infrastructure/database/
    ✅ Paso 3  — VLCPlayer + PlayerService
    ✅ Paso 4  — UI mínima
    ✅ Paso 5  — LibraryService + filesystem
    ✅ Paso 6  — CDService + MusicBrainz
    ✅ Paso 7  — RipperService + CDRipper
    ✅ Paso 8  — TaggerService + AcoustIDClient
    ✅ Paso 9  — PlaylistService + PlaylistPanel + PlaylistController
    ✅ Paso 10 — AppSettings, SettingsDialog, menú, tema QSS completo, v0.10
"""
import os
import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from audiorep.core.events import app_events  # noqa: F401  (inicializa el bus)
from audiorep.core.settings import AppSettings

# ── Directorio de datos ────────────────────────────────────────────────────── #
# En bundle PyInstaller: %APPDATA%\AudioRep (Win) / ~/.local/share/AudioRep (Linux)
# En desarrollo:         <raíz del proyecto>/data/
if getattr(sys, "frozen", False):
    if sys.platform == "win32":
        DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "AudioRep"
    else:
        xdg = os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        DATA_DIR = Path(xdg) / "AudioRep"
else:
    DATA_DIR = Path(__file__).parent / "data"

DB_PATH = str(DATA_DIR / "audiorep.db")

# Clave de AcoustID para el primer arranque (se persiste en QSettings).
# Dejar vacío ("") si no se quiere pre-cargar ninguna clave.
_ACOUSTID_KEY_SEED = "kSijHxC4qU"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AudioRep")
    app.setApplicationVersion("0.10.0")
    app.setOrganizationName("AudioRep")

    # ── Settings ──────────────────────────────────────────────────────── #
    settings = AppSettings()
    if _ACOUSTID_KEY_SEED and not settings.acoustid_api_key:
        settings.acoustid_api_key = _ACOUSTID_KEY_SEED
        settings.sync()
        logger.info("AcoustID API key inicializada desde seed.")

    # ── Infrastructure: base de datos ─────────────────────────────────── #
    from audiorep.infrastructure.database.connection import DatabaseConnection
    from audiorep.infrastructure.database.repositories.artist_repository import ArtistRepository
    from audiorep.infrastructure.database.repositories.album_repository import AlbumRepository
    from audiorep.infrastructure.database.repositories.track_repository import TrackRepository
    from audiorep.infrastructure.database.repositories.playlist_repository import PlaylistRepository

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = DatabaseConnection(DB_PATH)
    db.connect()

    artist_repo   = ArtistRepository(db)
    album_repo    = AlbumRepository(db)
    track_repo    = TrackRepository(db)
    playlist_repo = PlaylistRepository(db)

    logger.info("Base de datos lista en: %s", DB_PATH)

    # ── Infrastructure: audio ─────────────────────────────────────────── #
    from audiorep.infrastructure.audio.vlc_player import VLCPlayer

    vlc_player = VLCPlayer()

    # ── Infrastructure: filesystem ────────────────────────────────────── #
    from audiorep.infrastructure.filesystem.scanner import FileScanner
    from audiorep.infrastructure.filesystem.tagger import FileTagger

    scanner = FileScanner()
    tagger  = FileTagger()

    # ── Infrastructure: CD y APIs externas ───────────────────────────── #
    from audiorep.infrastructure.audio.cd_reader import CDReader
    from audiorep.infrastructure.audio.cd_ripper import CDRipper
    from audiorep.infrastructure.api.musicbrainz_client import MusicBrainzClient
    from audiorep.infrastructure.api.coverart_client import CoverArtClient
    from audiorep.infrastructure.api.acoustid_client import AcoustIDClient

    cd_reader       = CDReader()
    cd_ripper       = CDRipper()
    mb_client       = MusicBrainzClient(app_name="AudioRep", app_version="0.10.0")
    cover_client    = CoverArtClient(cache_dir=str(DATA_DIR / "covers"))
    acoustid_client = AcoustIDClient(api_key=settings.acoustid_api_key)

    # ── Services ──────────────────────────────────────────────────────── #
    from audiorep.services.player_service import PlayerService
    from audiorep.services.library_service import LibraryService
    from audiorep.services.cd_service import CDService
    from audiorep.services.playlist_service import PlaylistService
    from audiorep.services.search_service import SearchService
    from audiorep.services.ripper_service import RipperService
    from audiorep.services.tagger_service import TaggerService

    player_service = PlayerService(player=vlc_player, track_repo=track_repo)
    logger.info("PlayerService listo.")

    library_service = LibraryService(
        track_repo=track_repo,
        artist_repo=artist_repo,
        album_repo=album_repo,
        scanner=scanner,
        tagger=tagger,
    )
    logger.info("LibraryService listo.")

    cd_service = CDService(
        reader=cd_reader,
        metadata_provider=mb_client,
        cover_client=cover_client,
    )
    logger.info("CDService listo.")

    playlist_service = PlaylistService(
        playlist_repo=playlist_repo,
        track_repo=track_repo,
    )
    playlist_service.ensure_default_smart_playlists()
    logger.info("PlaylistService listo.")

    search_service = SearchService(library_service=library_service)
    logger.info("SearchService listo.")

    ripper_service = RipperService(
        ripper=cd_ripper,
        tagger=tagger,
        library_service=library_service,
    )
    logger.info("RipperService listo.")

    tagger_service = TaggerService(
        fingerprinter=acoustid_client,
        metadata_provider=mb_client,
        tagger=tagger,
        track_repo=track_repo,
        artist_repo=artist_repo,
        album_repo=album_repo,
    )
    logger.info("TaggerService listo.")

    # ── UI ────────────────────────────────────────────────────────────── #
    from audiorep.ui.main_window import MainWindow

    window = MainWindow(
        player_service=player_service,
        library_service=library_service,
        cd_service=cd_service,
        playlist_service=playlist_service,
        search_service=search_service,
        ripper_service=ripper_service,
        tagger_service=tagger_service,
        settings=settings,
    )
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
