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
    ✅ Paso 11 — Radio por internet (radio-browser.info), v0.20
    ✅ Paso 12 — UI 0.25: pestañas, controles, CD multi-lectora, playlist, VU meter, NowPlaying derecha
    ✅ Paso 13 — CD fix: CDDA URIs, identificación MB normalizada, GnuDB, panel metadatos manual, v0.30
    ✅ Paso 14 — VU metro real (PCM via sounddevice), tabla CD con cabeceras, fix portada NowPlaying, v0.35
    ✅ Paso 15 — Radio tabla resultados, CD sin portada inline, PlayerBar barra tiempo + volumen, v0.40
    ✅ Paso 16 — Fix crash radio (_station_label), fix tema QSS en listas cdMeta, v0.40
    ✅ Paso 17 — RadioSavedTable (tabla), fix volumen inicial en PlayerController, v0.42
    ✅ Paso 18 — Filtros en las 3 sub-tabs de Radio, RadioFavsTable, fix volumen PCM callback, v0.44
    ✅ Paso 19 — Fix hover menú Archivo (QMenuBar/QMenu QSS), mute toggle en ícono de volumen, v0.46
    ✅ Paso 20 — Números de tiempo de reproducción más grandes (font-size 11px → 16px), v0.47
    ✅ Paso 21 — Rediseño pestaña CD: fila única lectora+estado+info, tabla más alta, botones a ancho completo con estilo unificado, v0.48
    ✅ Paso 22 — Estandarización de todos los botones de acción, fix alineación botón play, v0.49
    ✅ Paso 23 — Estandarización de dropdowns, refactor performance reproductor (poll 200ms, VU stop, DB async), v0.50
    ✅ Paso 24 — Hilo RMS dedicado (_RMSAnalyzer), backpressure con log de underruns en _SDAudioBridge, v0.51
    ✅ Paso 25 — Columnas ordenables en Biblioteca (TrackTableModel.sort() + setSortingEnabled), v0.52
    ✅ Paso 26 — Columnas ordenables en Playlists; fix doble-clic siempre reproducía desde pista 1, v0.53
    ✅ Paso 27 — Columnas ordenables en Radio (3 tabs); _BitrateItem para orden numérico correcto, v0.54
    ✅ Paso 28 — trackLabel 16px en PlayerBar; botones de transporte sin highlight de foco (NoFocus), v0.57
    ✅ Paso 29 — NowPlaying: campo año, campos opcionales con setVisible, portada limpia al cambiar pista, v0.57
    ✅ Paso 30 — Estándar de diálogos modales: QLineEdit global, QDialogButtonBox, confirmaciones en español, v0.58
    ✅ Paso 31 — Título de ventana estático; Play tras Stop reproduce última pista (replay_current()), v0.59
    ✅ Paso 32 — Sello discográfico en NowPlaying y CDMetadataPanel; orden estándar NowPlaying, v0.60
    ✅ Paso 33 — StatsService + StatsPanel (6 tabs, PyQt6-Charts) + ExportService (XLSX/PDF/CSV), v0.65
    ✅ Paso 34 — Label entity + LabelRepository; Artist.country + Album.release_type; gráficos país/tipo, v0.67
    ✅ Paso 35 — EnrichmentService + LastFmClient; auto-enriquecimiento al importar y al arrancar, v0.69
    ✅ Paso 36 — XLSX/PDF tema profesional legible; tarjeta nacionalidades; total_countries en stats, v0.70
    ✅ Paso 37 — Gráfico de formatos convertido a torta; layout 2-por-fila en tabs Pistas y Álbumes, v0.71
    ✅ Paso 38 — Exportaciones separadas: "Exportar Biblioteca" y "Exportar Estadísticas" independientes, v0.72
    ✅ Paso 39 — Alturas fijas en gráficos (_H_HALF/FULL), sin scroll interno, leyenda torta a la izquierda, v0.73
    ✅ Paso 40 — Exportaciones: fuente 11 en XLSX, fuente 9 PDF, biblioteca PDF en horizontal (landscape), v0.74–v0.75
    ✅ Paso 41 — Fix stats: recálculo tras enriquecimiento; PDF stats ancho completo; fix NowPlaying trackLabel → playerTrackLabel, v0.76
    ✅ Paso 42 — Enriquecimiento por álbum (1 API call/álbum); códigos ISO → nombres completos; dedup importación; flecha dropdown visible, v0.77
    ✅ Paso 43 — Fix stats top_artists: album_id → album.artist_name canónico para evitar fragmentación por featuring, v0.78
    ✅ Paso 44 — Fix stats: _strip_featuring, _normalize_label, dedup países artistas, label country via get_label_by_id + caché; layout Álbumes: Décadas + Tipo de álbum emparejados, v0.79
    ✅ Paso 45 — Exportación de emisoras guardadas a M3U8 (ExportService.export_radio_m3u, RadioPanel botón Exportar, RadioController), v0.80
    ✅ Paso 46 — Exportación de lista de radios a XLSX/PDF/CSV (export_radio_xlsx/pdf/csv); botón "Exportar Radio" + "Exportar Lista de Radios" en pestaña Guardadas, v0.81
    ✅ Paso 47 — Ecualizador gráfico de 10 bandas: EqualizerService, EqualizerWidget (sliders -20/+20dB), botón EQ en PlayerBar, 18 presets VLC built-in + presets de usuario en SQLite, v0.82
"""
import os
import sys
import logging
from datetime import date, timedelta
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


def _maybe_auto_enrich(settings: "AppSettings", enrichment_service: object) -> None:
    """Inicia el enriquecimiento automático si está habilitado y el intervalo se cumplió."""
    if not settings.enrichment_enabled:
        return
    last_run_str = settings.enrichment_last_run
    if last_run_str:
        try:
            last_run = date.fromisoformat(last_run_str)
            days_since = (date.today() - last_run).days
            if days_since < settings.enrichment_interval_days:
                logger.debug(
                    "Auto-enriquecimiento: %d días desde la última ejecución, "
                    "intervalo=%d días. Omitido.",
                    days_since, settings.enrichment_interval_days,
                )
                return
        except ValueError:
            pass  # fecha inválida → ejecutar igual
    logger.info("Auto-enriquecimiento al startup: iniciando.")
    enrichment_service.start()  # type: ignore[attr-defined]
    settings.enrichment_last_run = date.today().isoformat()
    settings.sync()


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AudioRep")
    app.setApplicationVersion("0.82.0")
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
    from audiorep.infrastructure.database.repositories.radio_station_repository import RadioStationRepository
    from audiorep.infrastructure.database.repositories.label_repository import LabelRepository
    from audiorep.infrastructure.database.repositories.eq_preset_repository import EqPresetRepository

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = DatabaseConnection(DB_PATH)
    db.connect()

    artist_repo        = ArtistRepository(db)
    album_repo         = AlbumRepository(db)
    track_repo         = TrackRepository(db)
    playlist_repo      = PlaylistRepository(db)
    radio_station_repo = RadioStationRepository(db)
    label_repo         = LabelRepository(db)
    eq_preset_repo     = EqPresetRepository(db)

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
    from audiorep.infrastructure.api.radio_browser_client import RadioBrowserClient
    from audiorep.infrastructure.api.gnudb_client import GnuDBClient

    cd_reader       = CDReader()
    cd_ripper       = CDRipper()
    mb_client       = MusicBrainzClient(app_name="AudioRep", app_version="0.30.0")
    radio_client    = RadioBrowserClient()
    gnudb_client    = GnuDBClient()
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
    from audiorep.services.radio_service import RadioService
    from audiorep.services.stats_service import StatsService
    from audiorep.services.export_service import ExportService
    from audiorep.services.equalizer_service import EqualizerService

    player_service = PlayerService(player=vlc_player, track_repo=track_repo)
    logger.info("PlayerService listo.")

    library_service = LibraryService(
        track_repo=track_repo,
        artist_repo=artist_repo,
        album_repo=album_repo,
        scanner=scanner,
        tagger=tagger,
        label_repo=label_repo,
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

    radio_service = RadioService(
        player=vlc_player,
        station_repo=radio_station_repo,
        search_provider=radio_client,
    )
    logger.info("RadioService listo.")

    stats_service  = StatsService()
    export_service = ExportService()
    equalizer_service = EqualizerService(
        vlc_player=vlc_player,
        preset_repo=eq_preset_repo,
        settings=settings,
    )
    logger.info("StatsService, ExportService y EqualizerService listos.")

    from audiorep.infrastructure.api.lastfm_client import LastFmClient
    from audiorep.services.enrichment_service import EnrichmentService

    lastfm_client = LastFmClient(api_key=settings.lastfm_api_key) if settings.lastfm_api_key else None

    enrichment_service = EnrichmentService(
        db_path=db.path,
        tagger=tagger,
        mb_client=mb_client,
        lastfm_client=lastfm_client,
    )
    logger.info("EnrichmentService listo.")

    # ── UI ────────────────────────────────────────────────────────────── #
    from audiorep.ui.main_window import MainWindow

    # Providers de metadatos para el panel manual de CD.
    # Orden = orden en el desplegable "Servicio".
    cd_lookup_providers = [mb_client, gnudb_client]

    window = MainWindow(
        player_service=player_service,
        library_service=library_service,
        cd_service=cd_service,
        playlist_service=playlist_service,
        search_service=search_service,
        ripper_service=ripper_service,
        tagger_service=tagger_service,
        stats_service=stats_service,
        export_service=export_service,
        radio_service=radio_service,
        settings=settings,
        cd_lookup_providers=cd_lookup_providers,
        enrichment_service=enrichment_service,
        equalizer_service=equalizer_service,
    )
    window.show()

    # Auto-enriquecimiento al startup si el intervalo se cumplió
    _maybe_auto_enrich(settings, enrichment_service)

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
