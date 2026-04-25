"""
StatsService — Cálculo de estadísticas de la biblioteca musical.

Expone:
    LibraryStats  — dataclass con todos los indicadores calculados.
    compute_stats — función pura que procesa una lista de Track.
    StatsService  — QObject que delega el cómputo a un QThread worker.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from audiorep.domain.track import Track


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class LibraryStats:
    total_tracks:     int                        = 0
    total_artists:    int                        = 0
    total_albums:     int                        = 0
    total_duration_ms: int                       = 0
    genre_counts:     dict[str, int]             = field(default_factory=dict)
    decade_counts:    dict[str, int]             = field(default_factory=dict)
    format_counts:    dict[str, int]             = field(default_factory=dict)
    rating_counts:    dict[int, int]             = field(default_factory=dict)
    top_artists:      list[tuple[str, int]]      = field(default_factory=list)
    top_tracks:       list[tuple[str, str, int]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Función pura de cómputo (sin UI, sin threading)
# ---------------------------------------------------------------------------

def compute_stats(tracks: list[Track]) -> LibraryStats:
    """Calcula LibraryStats a partir de una lista de pistas."""
    if not tracks:
        return LibraryStats()

    genres:  dict[str, int] = defaultdict(int)
    decades: dict[str, int] = defaultdict(int)
    formats: dict[str, int] = defaultdict(int)
    ratings: dict[int, int] = defaultdict(int)
    artists: dict[str, int] = defaultdict(int)
    total_dur = 0

    artist_set: set[str] = set()
    album_set:  set[tuple[str, str]] = set()

    for t in tracks:
        total_dur += t.duration_ms or 0

        genre = (t.genre or "").strip() or "Sin género"
        genres[genre] += 1

        if t.year:
            decade = f"{(t.year // 10) * 10}s"
        else:
            decade = "Sin año"
        decades[decade] += 1

        fmt = t.format.value if t.format else "Desconocido"
        formats[fmt] += 1

        rating = t.rating if t.rating is not None else 0
        ratings[rating] += 1

        artist = t.artist_name or "Artista desconocido"
        artists[artist] += 1
        artist_set.add(artist)

        if t.album_title:
            album_set.add((artist, t.album_title))

    # Top 10 artistas por cantidad de pistas
    top_artists = sorted(artists.items(), key=lambda x: x[1], reverse=True)[:10]

    # Top 10 pistas más reproducidas (solo si alguna tiene play_count > 0)
    sorted_by_plays = sorted(tracks, key=lambda t: t.play_count or 0, reverse=True)[:10]
    top_tracks = [
        (t.title or "Sin título", t.artist_name or "", t.play_count or 0)
        for t in sorted_by_plays
    ]

    # Géneros: top 8, el resto agrupado como "Otros"
    sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
    top_genres: dict[str, int] = dict(sorted_genres[:8])
    others = sum(v for k, v in sorted_genres[8:])
    if others > 0:
        top_genres["Otros"] = others

    return LibraryStats(
        total_tracks=len(tracks),
        total_artists=len(artist_set),
        total_albums=len(album_set),
        total_duration_ms=total_dur,
        genre_counts=top_genres,
        decade_counts=dict(sorted(decades.items())),
        format_counts=dict(formats),
        rating_counts={i: ratings.get(i, 0) for i in range(6)},
        top_artists=top_artists,
        top_tracks=top_tracks,
    )


# ---------------------------------------------------------------------------
# Worker (QThread)
# ---------------------------------------------------------------------------

class _StatsWorker(QThread):
    stats_ready = pyqtSignal(object)  # LibraryStats

    def __init__(self, tracks: list[Track]) -> None:
        super().__init__()
        self._tracks = tracks

    def run(self) -> None:
        stats = compute_stats(self._tracks)
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

    def compute(self, tracks: list[Track]) -> None:
        """Inicia el cómputo asíncrono. Emite stats_ready al terminar."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

        self._worker = _StatsWorker(tracks)
        self._worker.stats_ready.connect(self.stats_ready)
        self._worker.start()
