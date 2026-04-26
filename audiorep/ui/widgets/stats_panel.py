"""
StatsPanel — Panel de estadísticas de la biblioteca musical.

Muestra gráficos y tarjetas de resumen calculados por StatsService,
organizados en 6 tabs: Generales, Pistas, Álbumes, Artistas, Géneros, Sellos.

objectNames alineados con dark.qss:
    statsPanel, statsScrollContent, statsSummaryCard,
    statsCardValue, statsCardLabel, statsSectionLabel, statsChartView, statsTabs
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from audiorep.services.stats_service import LibraryStats

try:
    from PyQt6.QtCharts import (
        QBarCategoryAxis,
        QBarSeries,
        QBarSet,
        QChart,
        QChartView,
        QHorizontalBarSeries,
        QPieSeries,
        QValueAxis,
    )
    _CHARTS_AVAILABLE = True
except ImportError:
    _CHARTS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------

_BG_DEEP    = QColor("#12121e")
_BG_SURFACE = QColor("#1e1e2e")
_BG_RAISED  = QColor("#2a2a3e")
_ACCENT     = QColor("#7c5cbf")
_ACCENT_DIM = QColor("#5a3d9a")
_TEXT_MAIN  = QColor("#e2e2f0")
_TEXT_MID   = QColor("#c0c0e0")
_TEXT_DIM   = QColor("#8888aa")
_BORDER     = QColor("#33334a")

_PIE_COLORS = [
    "#7c5cbf", "#5a3d9a", "#9b7dd4", "#4a3480",
    "#b090ff", "#a082d8", "#3a2470", "#8a6cbf",
    "#6d4aa8", "#c0a8ff",
]

_FONT_LABEL = QFont("Segoe UI", 9)
_FONT_TITLE = QFont("Segoe UI", 10, QFont.Weight.Bold)


# ---------------------------------------------------------------------------
# Fábrica de gráficos
# ---------------------------------------------------------------------------

def _base_chart(title: str = "") -> QChart:
    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(_BG_DEEP)
    chart.setTitleFont(_FONT_TITLE)
    chart.setTitleBrush(_TEXT_MAIN)
    chart.setMargins(chart.margins().__class__(8, 8, 8, 8))
    chart.legend().setVisible(False)
    return chart


def _chart_view(chart: QChart, min_height: int = 260) -> QChartView:
    view = QChartView(chart)
    view.setObjectName("statsChartView")
    view.setRenderHint(view.renderHints().__class__.Antialiasing)
    view.setMinimumHeight(min_height)
    view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    view.setStyleSheet(
        "background-color: #1e1e2e; border: 1px solid #33334a; border-radius: 6px;"
    )
    return view


def _styled_axis_x(axis: QBarCategoryAxis) -> None:
    axis.setLabelsColor(_TEXT_MID)
    axis.setLabelsFont(_FONT_LABEL)
    pen = QPen(_BORDER)
    axis.setLinePen(pen)
    axis.setGridLinePen(QPen(QColor("#2a2a3e")))
    axis.setLinePenColor(_BORDER)


def _styled_axis_y(axis: QValueAxis) -> None:
    axis.setLabelsColor(_TEXT_MID)
    axis.setLabelsFont(_FONT_LABEL)
    axis.setLinePen(QPen(_BORDER))
    axis.setGridLinePen(QPen(QColor("#2a2a3e")))
    axis.setLabelFormat("%d")
    axis.setTickCount(5)


def make_pie_chart(title: str, data: dict[str, int]) -> QChartView:
    chart = _base_chart(title)
    chart.legend().setVisible(True)
    chart.legend().setLabelColor(_TEXT_MID)
    chart.legend().setFont(_FONT_LABEL)
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

    series = QPieSeries()
    series.setHoleSize(0.3)
    total = sum(data.values()) or 1

    for i, (label, count) in enumerate(data.items()):
        pct = count / total * 100
        slc = series.append(f"{label} ({pct:.0f}%)", count)
        slc.setColor(QColor(_PIE_COLORS[i % len(_PIE_COLORS)]))
        slc.setBorderColor(_BG_SURFACE)
        if pct >= 8:
            slc.setLabelVisible(True)
            slc.setLabelColor(_TEXT_MID)
            slc.setLabelFont(_FONT_LABEL)

    chart.addSeries(series)
    return _chart_view(chart, 280)


def make_bar_chart(title: str, categories: list[str], values: list[int]) -> QChartView:
    bar_set = QBarSet("")
    bar_set.setColor(_ACCENT)
    bar_set.setBorderColor(_ACCENT_DIM)
    bar_set.setLabelColor(_TEXT_MAIN)
    for v in values:
        bar_set.append(v)

    series = QBarSeries()
    series.append(bar_set)
    series.setLabelsVisible(True)
    series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsOutsideEnd)
    series.setLabelsFormat("@value")

    chart = _base_chart(title)
    chart.addSeries(series)

    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    _styled_axis_x(axis_x)

    axis_y = QValueAxis()
    _styled_axis_y(axis_y)
    if values:
        axis_y.setRange(0, max(values) * 1.25 or 1)

    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)

    return _chart_view(chart, 260)


def make_hbar_chart(
    title: str,
    labels: list[str],
    values: list[int],
    min_height: int = 320,
    left_margin: int = 140,
) -> QChartView:
    bar_set = QBarSet("")
    bar_set.setColor(_ACCENT)
    bar_set.setBorderColor(_ACCENT_DIM)
    bar_set.setLabelColor(_TEXT_MAIN)
    for v in values:
        bar_set.append(v)

    series = QHorizontalBarSeries()
    series.append(bar_set)
    series.setLabelsVisible(True)
    series.setLabelsPosition(QHorizontalBarSeries.LabelsPosition.LabelsOutsideEnd)
    series.setLabelsFormat("@value")

    chart = _base_chart(title)
    # Margen izquierdo amplio para que se lean los nombres completos
    chart.setMargins(chart.margins().__class__(left_margin, 8, 24, 8))
    chart.addSeries(series)

    # Truncar labels en Python antes de pasarlos al eje: si un label supera el
    # ancho del margen, Qt Charts trunca TODOS con "..." aunque el resto quepan.
    # Estimación: ~7px por carácter con Segoe UI 9pt; 20px de padding interno.
    max_chars = max(8, (left_margin - 20) // 7)
    safe_labels = [
        (lbl[:max_chars] + "…") if len(lbl) > max_chars else lbl
        for lbl in labels
    ]

    axis_y = QBarCategoryAxis()
    axis_y.append(safe_labels)
    axis_y.setTruncateLabels(False)
    _styled_axis_x(axis_y)

    axis_x = QValueAxis()
    _styled_axis_y(axis_x)
    if values:
        axis_x.setRange(0, max(values) * 1.25 or 1)

    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_y)
    series.attachAxis(axis_x)

    return _chart_view(chart, min_height)


# ---------------------------------------------------------------------------
# Helpers de layout
# ---------------------------------------------------------------------------

def _scroll_tab() -> tuple[QScrollArea, QVBoxLayout]:
    """Retorna (scroll_area, layout_del_contenedor_interno)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    container = QWidget()
    container.setObjectName("statsScrollContent")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(16)
    scroll.setWidget(container)
    return scroll, layout


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("statsSectionLabel")
    return lbl


def _chart_row(*views: QChartView) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    for v in views:
        row.addWidget(v)
    return row


def _make_card(value: str, label: str) -> QWidget:
    card = QFrame()
    card.setObjectName("statsSummaryCard")
    v = QVBoxLayout(card)
    v.setContentsMargins(12, 14, 12, 14)
    v.setSpacing(4)

    val_lbl = QLabel(value)
    val_lbl.setObjectName("statsCardValue")
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl_lbl = QLabel(label)
    lbl_lbl.setObjectName("statsCardLabel")
    lbl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    v.addWidget(val_lbl)
    v.addWidget(lbl_lbl)
    return card


# ---------------------------------------------------------------------------
# Construcción de cada tab
# ---------------------------------------------------------------------------

def _build_tab_general(stats: LibraryStats) -> QWidget:
    scroll, layout = _scroll_tab()

    hours = stats.total_duration_ms / 3_600_000
    cards = [
        (str(stats.total_tracks),    "pistas"),
        (str(stats.total_artists),   "artistas"),
        (str(stats.total_albums),    "álbumes"),
        (f"{hours:.1f}",             "horas"),
        (str(stats.total_genres),    "géneros"),
        (str(stats.total_formats),   "formatos"),
        (str(stats.total_labels),    "sellos"),
        (str(stats.total_countries), "nacionalidades"),
    ]

    # Primera fila: 4 tarjetas principales
    row1 = QWidget()
    h1 = QHBoxLayout(row1)
    h1.setContentsMargins(0, 0, 0, 0)
    h1.setSpacing(12)
    for value, label in cards[:4]:
        h1.addWidget(_make_card(value, label), stretch=1)
    layout.addWidget(row1)

    # Segunda fila: 4 tarjetas adicionales
    row2 = QWidget()
    h2 = QHBoxLayout(row2)
    h2.setContentsMargins(0, 0, 0, 0)
    h2.setSpacing(12)
    for value, label in cards[4:]:
        h2.addWidget(_make_card(value, label), stretch=1)
    layout.addWidget(row2)

    layout.addStretch(1)
    return scroll


def _build_tab_tracks(stats: LibraryStats, charts: bool) -> QWidget:
    scroll, layout = _scroll_tab()

    if not charts:
        layout.addWidget(_no_charts_note())
        layout.addStretch(1)
        return scroll

    # Duración de pistas
    if any(stats.track_duration_dist.values()):
        cats = list(stats.track_duration_dist.keys())
        vals = list(stats.track_duration_dist.values())
        layout.addWidget(make_bar_chart("Duración de pistas", cats, vals))

    # Formatos de pistas
    if stats.track_format_dist:
        cats = list(stats.track_format_dist.keys())
        vals = list(stats.track_format_dist.values())
        layout.addWidget(make_bar_chart("Formatos de pistas", cats, vals))

    # BitRate de pistas
    if any(stats.track_bitrate_dist.values()):
        cats = list(stats.track_bitrate_dist.keys())
        vals = list(stats.track_bitrate_dist.values())
        layout.addWidget(make_bar_chart("BitRate de pistas", cats, vals))

    # Top 10 pistas más reproducidas
    max_plays = max((t[2] for t in stats.top_tracks), default=0)
    if stats.top_tracks and max_plays > 0:
        tracks_rev = list(reversed(stats.top_tracks))
        t_labels = [f"{t[0][:20]} — {t[1][:14]}" for t in tracks_rev]
        t_vals   = [t[2] for t in tracks_rev]
        layout.addWidget(_section_label("Top 10 pistas más reproducidas"))
        layout.addWidget(make_hbar_chart("", t_labels, t_vals))

    layout.addStretch(1)
    return scroll


def _build_tab_albums(stats: LibraryStats, charts: bool) -> QWidget:
    scroll, layout = _scroll_tab()

    if not charts:
        layout.addWidget(_no_charts_note())
        layout.addStretch(1)
        return scroll

    # Cantidad de pistas por álbum
    if any(stats.album_track_count_dist.values()):
        cats = list(stats.album_track_count_dist.keys())
        vals = list(stats.album_track_count_dist.values())
        layout.addWidget(make_bar_chart("Pistas por álbum", cats, vals))

    # Duración de álbumes
    if any(stats.album_duration_dist.values()):
        cats = list(stats.album_duration_dist.keys())
        vals = list(stats.album_duration_dist.values())
        layout.addWidget(make_bar_chart("Duración de álbumes", cats, vals))

    # Décadas de álbumes
    if stats.album_decade_counts:
        decades_clean = {k: v for k, v in stats.album_decade_counts.items() if k != "Sin año"}
        if decades_clean:
            keys = sorted(decades_clean.keys())
            layout.addWidget(
                make_bar_chart("Décadas", keys, [decades_clean[k] for k in keys])
            )

    # Tipo de álbum (release_type) — solo si hay datos
    if stats.album_type_counts:
        types = list(stats.album_type_counts.keys())
        vals  = list(stats.album_type_counts.values())
        layout.addWidget(_section_label("Tipo de álbum"))
        layout.addWidget(make_bar_chart("Tipo de álbum", types, vals))
    else:
        layout.addWidget(_no_data_note(
            "Tipo de álbum: sin datos.\n"
            "Se completa al identificar discos CD con MusicBrainz."
        ))

    layout.addStretch(1)
    return scroll


def _build_tab_artists(stats: LibraryStats, charts: bool) -> QWidget:
    scroll, layout = _scroll_tab()

    if not charts:
        layout.addWidget(_no_charts_note())
        layout.addStretch(1)
        return scroll

    # Top 10 artistas por cantidad de pistas
    if stats.top_artists:
        artists_rev = list(reversed(stats.top_artists))
        a_labels = [a[0] for a in artists_rev]  # nombre completo (sin truncar)
        a_vals   = [a[1] for a in artists_rev]
        layout.addWidget(_section_label("Top 10 artistas por cantidad de pistas"))
        layout.addWidget(make_hbar_chart("", a_labels, a_vals, min_height=360, left_margin=160))

    # Top países de artistas — solo si hay datos
    if stats.artist_country_counts:
        countries     = list(reversed(list(stats.artist_country_counts.keys())))
        country_vals  = list(reversed(list(stats.artist_country_counts.values())))
        layout.addWidget(_section_label("País de origen de artistas"))
        layout.addWidget(
            make_hbar_chart("", countries, country_vals, min_height=320, left_margin=160)
        )
    else:
        layout.addWidget(_no_data_note(
            "País de origen: sin datos.\n"
            "Se completa al identificar discos CD con MusicBrainz."
        ))

    layout.addStretch(1)
    return scroll


def _build_tab_genres(stats: LibraryStats, charts: bool) -> QWidget:
    scroll, layout = _scroll_tab()

    if not charts:
        layout.addWidget(_no_charts_note())
        layout.addStretch(1)
        return scroll

    # Torta de géneros (top 8 + Otros)
    if stats.genre_counts:
        layout.addWidget(make_pie_chart("Distribución de géneros", stats.genre_counts))

    # Top 10 géneros (barras)
    if stats.top_genres_bar:
        genres_rev = list(reversed(stats.top_genres_bar))
        g_labels = [g[0] for g in genres_rev]
        g_vals   = [g[1] for g in genres_rev]
        layout.addWidget(_section_label("Top 10 géneros por cantidad de pistas"))
        layout.addWidget(make_hbar_chart("", g_labels, g_vals, min_height=320, left_margin=160))

    layout.addStretch(1)
    return scroll


def _build_tab_labels(stats: LibraryStats, charts: bool) -> QWidget:
    scroll, layout = _scroll_tab()

    if not charts:
        layout.addWidget(_no_charts_note())
        layout.addStretch(1)
        return scroll

    if stats.top_labels:
        labels_rev = list(reversed(stats.top_labels))
        l_labels = [l[0] for l in labels_rev]
        l_vals   = [l[1] for l in labels_rev]
        layout.addWidget(_section_label("Top 10 sellos discográficos por cantidad de pistas"))
        layout.addWidget(make_hbar_chart("", l_labels, l_vals, min_height=320, left_margin=160))
    else:
        layout.addWidget(_no_data_note(
            "No hay información de sellos disponible.\n"
            "Los sellos se toman de los tags de los álbumes importados."
        ))

    # País de origen de sellos — solo si hay datos
    if stats.label_country_counts:
        countries    = list(reversed(list(stats.label_country_counts.keys())))
        country_vals = list(reversed(list(stats.label_country_counts.values())))
        layout.addWidget(_section_label("País de origen de sellos"))
        layout.addWidget(
            make_hbar_chart("", countries, country_vals, min_height=280, left_margin=160)
        )
    else:
        layout.addWidget(_no_data_note(
            "País de sellos: sin datos.\n"
            "Se completa al identificar discos CD con MusicBrainz."
        ))

    layout.addStretch(1)
    return scroll


def _no_charts_note() -> QLabel:
    note = QLabel(
        "PyQt6-Charts no está instalado. Instale 'PyQt6-Charts' para ver gráficos."
    )
    note.setObjectName("statsSectionLabel")
    note.setAlignment(Qt.AlignmentFlag.AlignCenter)
    note.setWordWrap(True)
    return note


def _no_data_note(text: str) -> QLabel:
    note = QLabel(text)
    note.setObjectName("statsSectionLabel")
    note.setAlignment(Qt.AlignmentFlag.AlignCenter)
    note.setWordWrap(True)
    return note


# ---------------------------------------------------------------------------
# StatsPanel
# ---------------------------------------------------------------------------

class StatsPanel(QWidget):
    """Panel de estadísticas con 6 tabs: Generales, Pistas, Álbumes, Artistas, Géneros, Sellos."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statsPanel")
        self._build_ui()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        # Página 0: cargando
        self._stack.addWidget(self._make_loading_page())

        # Página 1: contenido (se construye al recibir datos)
        self._content_page: QWidget = QWidget()
        self._stack.addWidget(self._content_page)

    def _make_loading_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("Calculando estadísticas…")
        lbl.setObjectName("statsSectionLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        return page

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def show_loading(self) -> None:
        self._stack.setCurrentIndex(0)

    def load(self, stats: LibraryStats) -> None:
        """Puebla el panel con los datos de stats y lo muestra."""
        old = self._content_page
        self._stack.removeWidget(old)
        old.deleteLater()

        self._content_page = self._build_content(stats)
        self._stack.addWidget(self._content_page)
        self._stack.setCurrentWidget(self._content_page)

    # ------------------------------------------------------------------
    # Construcción del contenido
    # ------------------------------------------------------------------

    def _build_content(self, stats: LibraryStats) -> QWidget:
        tabs = QTabWidget()
        tabs.setObjectName("statsTabs")

        charts = _CHARTS_AVAILABLE

        tabs.addTab(_build_tab_general(stats),            "Generales")
        tabs.addTab(_build_tab_tracks(stats, charts),     "Pistas")
        tabs.addTab(_build_tab_albums(stats, charts),     "Álbumes")
        tabs.addTab(_build_tab_artists(stats, charts),    "Artistas")
        tabs.addTab(_build_tab_genres(stats, charts),     "Géneros")
        tabs.addTab(_build_tab_labels(stats, charts),     "Sellos")

        return tabs
