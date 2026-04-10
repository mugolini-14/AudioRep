"""
AudioRep — Punto de entrada de la aplicación.

Responsabilidad: composición raíz (dependency injection manual).
Instancia todas las capas y las conecta antes de arrancar la UI.

Estado de implementación:
    ✅ Paso 1 — domain/ + core/
    ✅ Paso 2 — infrastructure/database/
    ✅ Paso 3 — VLCPlayer + PlayerService
    ✅ Paso 4 — UI mínima
    ✅ Paso 5 — LibraryService + filesystem
    ✅ Paso 6 — CDService + MusicBrainz
    ⬜ Paso 7 — RipperService
"""
import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from audiorep.core.events import app_events  # noqa: F401  (inicializa el bus)

# Directorio de datos de la aplicación (junto al ejecutable / raíz del proyecto)
DATA_DIR = Path(__file__).parent / "data"
DB_PATH  = str(DATA_DIR / "audiorep.db")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AudioRep")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("AudioRep")

    # ------------------------------------------------------------------ #
    # Paso 2 — Infrastructure: base de datos                             #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Paso 3 — Infrastructure: audio                                      #
    # ------------------------------------------------------------------ #
    from audiorep.infrastructure.audio.vlc_player import VLCPlayer

    vlc_player = VLCPlayer()

    # ------------------------------------------------------------------ #
    # Paso 3 — Services                                                   #
    # ------------------------------------------------------------------ #
    from audiorep.services.player_service import PlayerService

    player_service = PlayerService(player=vlc_player, track_repo=track_repo)

    logger.info("PlayerService listo.")

    # ------------------------------------------------------------------ #
    # Paso 5 — Infrastructure: filesystem                                  #
    # ------------------------------------------------------------------ #
    from audiorep.infrastructure.filesystem.scanner import FileScanner
    from audiorep.infrastructure.filesystem.tagger import FileTagger

    scanner = FileScanner()
    tagger  = FileTagger()

    # ------------------------------------------------------------------ #
    # Paso 5 — Services: biblioteca                                        #
    # ------------------------------------------------------------------ #
    from audiorep.services.library_service import LibraryService

    library_service = LibraryService(
        track_repo=track_repo,
        artist_repo=artist_repo,
        album_repo=album_repo,
        scanner=scanner,
        tagger=tagger,
    )

    logger.info("LibraryService listo.")

    # ------------------------------------------------------------------ #
    # Paso 6 — Infrastructure: CD                                         #
    # ------------------------------------------------------------------ #
    from audiorep.infrastructure.audio.cd_reader import CDReader
    from audiorep.infrastructure.api.musicbrainz_client import MusicBrainzClient
    from audiorep.infrastructure.api.coverart_client import CoverArtClient

    cd_reader    = CDReader()
    mb_client    = MusicBrainzClient(app_name="AudioRep", app_version="0.1.0")
    cover_client = CoverArtClient(cache_dir=str(DATA_DIR / "covers"))

    # ------------------------------------------------------------------ #
    # Paso 6 — Services: CD                                               #
    # ------------------------------------------------------------------ #
    from audiorep.services.cd_service import CDService

    cd_service = CDService(
        reader=cd_reader,
        metadata_provider=mb_client,
        cover_client=cover_client,
    )

    logger.info("CDService listo.")

    # ------------------------------------------------------------------ #
    # Paso 4 + 5 + 6 — UI                                                 #
    # ------------------------------------------------------------------ #
    from audiorep.ui.main_window import MainWindow

    window = MainWindow(
        player_service=player_service,
        library_service=library_service,
        cd_service=cd_service,
    )
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
