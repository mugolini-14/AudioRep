"""
StatsService — Cálculo de estadísticas de la biblioteca musical.

Expone:
    LibraryStats  — dataclass con todos los indicadores calculados.
    compute_stats — función pura que procesa listas de Track y Album.
    StatsService  — QObject que delega el cómputo a un QThread worker.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.domain.album import Album
from audiorep.domain.artist import Artist
from audiorep.domain.track import Track


# ---------------------------------------------------------------------------
# Helpers de bucketing
# ---------------------------------------------------------------------------

def _duration_bucket(ms: int) -> str:
    if ms < 120_000:
        return "0–2 min"
    if ms < 180_000:
        return "2–3 min"
    if ms < 240_000:
        return "3–4 min"
    if ms < 300_000:
        return "4–5 min"
    if ms < 600_000:
        return "5–10 min"
    return "+10 min"


_DURATION_BUCKETS = ["0–2 min", "2–3 min", "3–4 min", "4–5 min", "5–10 min", "+10 min"]


def _bitrate_bucket(kbps: int) -> str:
    if kbps < 96:
        return "0–96 kbps"
    if kbps < 128:
        return "96–128 kbps"
    if kbps < 256:
        return "128–256 kbps"
    if kbps < 320:
        return "256–320 kbps"
    return "≥320 kbps"


_BITRATE_BUCKETS = ["0–96 kbps", "96–128 kbps", "128–256 kbps", "256–320 kbps", "≥320 kbps"]


def _album_track_bucket(n: int) -> str:
    if n < 5:
        return "0–5 pistas"
    if n < 10:
        return "5–10 pistas"
    if n < 15:
        return "10–15 pistas"
    return "+15 pistas"


_ALBUM_TRACK_BUCKETS = ["0–5 pistas", "5–10 pistas", "10–15 pistas", "+15 pistas"]


def _album_dur_bucket(ms: int) -> str:
    if ms < 900_000:
        return "0–15 min"
    if ms < 1_800_000:
        return "15–30 min"
    if ms < 2_700_000:
        return "30–45 min"
    if ms < 3_600_000:
        return "45–60 min"
    return "+1 hora"


_ALBUM_DUR_BUCKETS = ["0–15 min", "15–30 min", "30–45 min", "45–60 min", "+1 hora"]


def _decade_label(year: int) -> str:
    # Normaliza años de dos dígitos (ej. 90 → 1990)
    if 0 < year < 100:
        year += 1900
    return f"{(year // 10) * 10}s"


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class LibraryStats:
    # ── Generales ──────────────────────────────────────────────────────── #
    total_tracks:      int                        = 0
    total_artists:     int                        = 0
    total_albums:      int                        = 0
    total_duration_ms: int                        = 0
    total_genres:      int                        = 0
    total_formats:     int                        = 0
    total_labels:      int                        = 0
    total_countries:   int                        = 0

    # ── Pistas ─────────────────────────────────────────────────────────── #
    track_duration_dist: dict[str, int]           = field(default_factory=dict)
    track_format_dist:   dict[str, int]           = field(default_factory=dict)
    track_bitrate_dist:  dict[str, int]           = field(default_factory=dict)
    top_tracks:          list[tuple[str, str, int]] = field(default_factory=list)

    # ── Álbumes ────────────────────────────────────────────────────────── #
    album_track_count_dist: dict[str, int]        = field(default_factory=dict)
    album_duration_dist:    dict[str, int]        = field(default_factory=dict)
    album_decade_counts:    dict[str, int]        = field(default_factory=dict)
    album_type_counts:      dict[str, int]        = field(default_factory=dict)  # tipo → cant.

    # ── Artistas ───────────────────────────────────────────────────────── #
    top_artists:          list[tuple[str, int]]   = field(default_factory=list)
    artist_country_counts: dict[str, int]         = field(default_factory=dict)  # país → cant.

    # ── Géneros ────────────────────────────────────────────────────────── #
    genre_counts:    dict[str, int]               = field(default_factory=dict)  # top8+Otros (pie)
    top_genres_bar:  list[tuple[str, int]]        = field(default_factory=list)  # top10 (barras)

    # ── Sellos ─────────────────────────────────────────────────────────── #
    top_labels:           list[tuple[str, int]]   = field(default_factory=list)
    label_country_counts: dict[str, int]          = field(default_factory=dict)  # país → cant.

    # ── Compatibilidad con exportación (no mostrar en UI) ──────────────── #
    decade_counts:  dict[str, int]                = field(default_factory=dict)
    format_counts:  dict[str, int]                = field(default_factory=dict)
    rating_counts:  dict[int, int]                = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Función pura de cómputo (sin UI, sin threading)
# ---------------------------------------------------------------------------

def compute_stats(
    tracks: list[Track],
    albums: list[Album] | None = None,
    artists: list[Artist] | None = None,
    label_country_map: dict[str, str] | None = None,
) -> LibraryStats:
    """Calcula LibraryStats a partir de listas de pistas, álbumes y artistas."""
    if not tracks:
        return LibraryStats()

    albums = albums or []
    artists = artists or []
    label_country_map = label_country_map or {}

    # ── Acumuladores de pistas ──────────────────────────────────────────── #
    genres:        dict[str, int]          = defaultdict(int)
    formats:       dict[str, int]          = defaultdict(int)
    ratings:       dict[int, int]          = defaultdict(int)
    artist_counts: dict[str, int]          = defaultdict(int)   # nombre → cant. pistas
    dur_dist:      dict[str, int]          = defaultdict(int)
    bitrate_dist:  dict[str, int]          = defaultdict(int)
    decades:       dict[str, int]          = defaultdict(int)   # para export compat

    artist_set: set[str]               = set()
    album_set:  set[tuple[str, str]]   = set()

    # duration y track count por álbum (clave: artista+título)
    album_dur_acc:   dict[tuple[str, str], int] = defaultdict(int)
    album_track_acc: dict[tuple[str, str], int] = defaultdict(int)

    total_dur = 0

    for t in tracks:
        total_dur += t.duration_ms or 0

        genre = (t.genre or "").strip() or "Sin género"
        genres[genre] += 1

        fmt = t.format.value if t.format else "Desconocido"
        formats[fmt] += 1

        rating = t.rating if t.rating is not None else 0
        ratings[rating] += 1

        artist = (t.artist_name or "").strip() or "Artista desconocido"
        artist_counts[artist] += 1
        artist_set.add(artist)

        dur_dist[_duration_bucket(t.duration_ms or 0)] += 1

        kbps = t.bitrate_kbps or 0
        bitrate_dist[_bitrate_bucket(kbps)] += 1

        if t.year and t.year > 0:
            decades[_decade_label(t.year)] += 1
        else:
            decades["Sin año"] += 1

        key = (artist, (t.album_title or "").strip())
        if t.album_title:
            album_set.add(key)
            album_dur_acc[key]   += t.duration_ms or 0
            album_track_acc[key] += 1

    # ── Top artistas ────────────────────────────────────────────────────── #
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Top pistas más reproducidas ─────────────────────────────────────── #
    sorted_by_plays = sorted(tracks, key=lambda t: t.play_count or 0, reverse=True)[:10]
    top_tracks = [
        (t.title or "Sin título", t.artist_name or "", t.play_count or 0)
        for t in sorted_by_plays
    ]

    # ── Géneros: pie (top 8 + Otros) y barras (top 10) ─────────────────── #
    sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
    top_genres_bar: list[tuple[str, int]] = sorted_genres[:10]
    pie_genres: dict[str, int] = dict(sorted_genres[:8])
    others = sum(v for _, v in sorted_genres[8:])
    if others > 0:
        pie_genres["Otros"] = others

    # ── Distribuciones con orden fijo ───────────────────────────────────── #
    track_dur_dist  = {k: dur_dist.get(k, 0)     for k in _DURATION_BUCKETS}
    track_bit_dist  = {k: bitrate_dist.get(k, 0) for k in _BITRATE_BUCKETS}

    # ── Stats de álbumes ─────────────────────────────────────────────────── #
    # Décadas desde la lista de Album (más precisa que desde pistas)
    album_decade: dict[str, int] = defaultdict(int)
    label_track_count: dict[str, int] = defaultdict(int)
    label_set: set[str] = set()
    album_type_raw: dict[str, int] = defaultdict(int)

    # Mapa (artist_name, album_title) → (label, release_type) para cruzar con pistas
    album_label_map: dict[tuple[str, str], str] = {}
    for a in albums:
        lbl = (a.label or "").strip()
        artist_key = (a.artist_name or "").strip()
        title_key  = (a.title or "").strip()
        album_label_map[(artist_key, title_key)] = lbl

        if a.year and a.year > 0:
            album_decade[_decade_label(a.year)] += 1

        if lbl:
            label_set.add(lbl)

        # Tipo de álbum (release_type)
        rtype = (a.release_type or "").strip()
        if rtype:
            album_type_raw[rtype] += 1

    # Acumular tracks por sello usando el mapa
    for (artist, album_title), count in album_track_acc.items():
        lbl = album_label_map.get((artist, album_title), "")
        if lbl:
            label_track_count[lbl] += count

    top_labels = sorted(label_track_count.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Países de artistas ───────────────────────────────────────────────── #
    artist_country_raw: dict[str, int] = defaultdict(int)
    for ar in artists:
        c = (ar.country or "").strip()
        if c:
            artist_country_raw[c] += 1
    total_countries = len(artist_country_raw)
    artist_country_counts = dict(
        sorted(artist_country_raw.items(), key=lambda x: x[1], reverse=True)[:15]
    )

    # ── Países de sellos ─────────────────────────────────────────────────── #
    label_country_raw: dict[str, int] = defaultdict(int)
    for lbl_name, lbl_country in label_country_map.items():
        if lbl_country and lbl_name in {lbl for lbl in label_set if lbl}:
            label_country_raw[lbl_country] += 1
    label_country_counts = dict(
        sorted(label_country_raw.items(), key=lambda x: x[1], reverse=True)[:15]
    )

    # Distribución de álbumes por cantidad de pistas
    atc_dist = {k: 0 for k in _ALBUM_TRACK_BUCKETS}
    for count in album_track_acc.values():
        atc_dist[_album_track_bucket(count)] += 1

    # Distribución de álbumes por duración total
    adur_dist = {k: 0 for k in _ALBUM_DUR_BUCKETS}
    for ms in album_dur_acc.values():
        adur_dist[_album_dur_bucket(ms)] += 1

    return LibraryStats(
        # Generales
        total_tracks=len(tracks),
        total_artists=len(artist_set),
        total_albums=len(album_set),
        total_duration_ms=total_dur,
        total_genres=len(genres),
        total_formats=len(formats),
        total_labels=len(label_set),
        total_countries=total_countries,
        # Pistas
        track_duration_dist=track_dur_dist,
        track_format_dist=dict(formats),
        track_bitrate_dist=track_bit_dist,
        top_tracks=top_tracks,
        # Álbumes
        album_track_count_dist=atc_dist,
        album_duration_dist=adur_dist,
        album_decade_counts=dict(sorted(album_decade.items())),
        album_type_counts=dict(sorted(album_type_raw.items(), key=lambda x: x[1], reverse=True)),
        # Artistas
        top_artists=top_artists,
        artist_country_counts=artist_country_counts,
        # Géneros
        genre_counts=pie_genres,
        top_genres_bar=top_genres_bar,
        # Sellos
        top_labels=top_labels,
        label_country_counts=label_country_counts,
        # Compat. exportación
        decade_counts=dict(sorted(decades.items())),
        format_counts=dict(formats),
        rating_counts={i: ratings.get(i, 0) for i in range(6)},
    )


# ---------------------------------------------------------------------------
# Worker (QThread)
# ---------------------------------------------------------------------------

class _StatsWorker(QThread):
    stats_ready = pyqtSignal(object)  # LibraryStats

    def __init__(
        self,
        tracks: list[Track],
        albums: list[Album],
        artists: list[Artist] | None = None,
        label_country_map: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._tracks            = tracks
        self._albums            = albums
        self._artists           = artists or []
        self._label_country_map = label_country_map or {}

    def run(self) -> None:
        stats = compute_stats(
            self._tracks,
            self._albums,
            self._artists,
            self._label_country_map,
        )
        self.stats_ready.emit(stats)


# ---------------------------------------------------------------------------
# Service público
# ---------------------------------------------------------------------------

class StatsService(QObject):
    """
    Calcula estadísticas de la biblioteca en un hilo de fondo.

    Señales:
        stats_ready(LibraryStats): emitida al terminar el cómputo.
    """

    stats_ready = pyqtSignal(object)  # LibraryStats

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: _StatsWorker | None = None

    def compute(
        self,
        tracks: list[Track],
        albums: list[Album] | None = None,
        artists: list[Artist] | None = None,
        label_country_map: dict[str, str] | None = None,
    ) -> None:
        """Inicia el cómputo asíncrono. Emite stats_ready al terminar."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

        self._worker = _StatsWorker(
            tracks,
            albums or [],
            artists or [],
            label_country_map or {},
        )
        self._worker.stats_ready.connect(self.stats_ready)
        self._worker.start()
