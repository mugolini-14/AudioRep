"""
StatsPanel — Panel de estadísticas de la biblioteca musical.

Muestra gráficos y tarjetas de resumen calculados por StatsService.

objectNames alineados con dark.qss:
    statsPanel, statsSummaryRow, statsSummaryCard,
    statsSectionLabel, statsChartView

Modos:
    show_loading()           — muestra indicador de carga.
    load(stats: LibraryStats) — puebla y muestra los gráficos.
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
    chart.setBackgroundBrush(_BG_SURFACE)
    chart.setPlotAreaBackgroundBrush(_BG_DEEP)
    chart.setPlotAreaBackgroundVisible(True)
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
    view.setStyleSheet("background-color: #1e1e2e; border: 1px solid #33334a; border-radius: 6px;")
    return view


def _styled_axis_x(axis: QBarCategoryAxis) -> None:
    axis.setLabelsColor(_TEXT_DIM)
    axis.setLabelsFont(_FONT_LABEL)
    pen = QPen(_BORDER)
    axis.setLinePen(pen)
    axis.setGridLinePen(QPen(QColor("#2a2a3e")))
    axis.setLinePenColor(_BORDER)


def _styled_axis_y(axis: QValueAxis) -> None:
    axis.setLabelsColor(_TEXT_DIM)
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
    return _chart_view(chart, 270)


def make_bar_chart(title: str, categories: list[str], values: list[int]) -> QChartView:
    bar_set = QBarSet("")
    bar_set.setColor(_ACCENT)
    bar_set.setBorderColor(_ACCENT_DIM)
    for v in values:
        bar_set.append(v)

    series = QBarSeries()
    series.append(bar_set)

    chart = _base_chart(title)
    chart.addSeries(series)

    axis_x = QBarCategoryAxis()
    axis_x.append(categories)
    _styled_axis_x(axis_x)

    axis_y = QValueAxis()
    _styled_axis_y(axis_y)
    if values:
        axis_y.setRange(0, max(values) * 1.15 or 1)

    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(axis_x)
    series.attachAxis(axis_y)

    return _chart_view(chart, 260)


def make_hbar_chart(title: str, labels: list[str], values: list[int]) -> QChartView:
    bar_set = QBarSet("")
    bar_set.setColor(_ACCENT)
    bar_set.setBorderColor(_ACCENT_DIM)
    for v in values:
        bar_set.append(v)

    series = QHorizontalBarSeries()
    series.append(bar_set)

    chart = _base_chart(title)
    chart.addSeries(series)

    axis_y = QBarCategoryAxis()
    axis_y.append(labels)
    _styled_axis_x(axis_y)

    axis_x = QValueAxis()
    _styled_axis_y(axis_x)
    if values:
        axis_x.setRange(0, max(values) * 1.15 or 1)

    chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
    chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
    series.attachAxis(axis_y)
    series.attachAxis(axis_x)

    return _chart_view(chart, 300)


# ---------------------------------------------------------------------------
# StatsPanel
# ---------------------------------------------------------------------------

class StatsPanel(QWidget):
    """Panel de estadísticas con tarjetas de resumen y gráficos."""

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
        self._content_page = QWidget()
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
        # Reconstruir la página de contenido
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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("statsScrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ── Tarjetas de resumen ──────────────────────────────────── #
        layout.addWidget(self._make_summary_row(stats))

        if _CHARTS_AVAILABLE:
            self._add_charts(layout, stats)
        else:
            self._add_fallback_tables(layout, stats)

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _make_summary_row(self, stats: LibraryStats) -> QWidget:
        row = QWidget()
        row.setObjectName("statsSummaryRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(12)

        hours = stats.total_duration_ms / 3_600_000
        cards = [
            (str(stats.total_tracks), "pistas"),
            (str(stats.total_artists), "artistas"),
            (str(stats.total_albums), "álbumes"),
            (f"{hours:.1f}", "horas"),
        ]
        for value, label in cards:
            h.addWidget(self._make_card(value, label), stretch=1)
        return row

    def _make_card(self, value: str, label: str) -> QWidget:
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

    def _add_charts(self, layout: QVBoxLayout, stats: LibraryStats) -> None:
        """Agrega todos los gráficos al layout."""

        # Fila 1: géneros (torta) + décadas (barras)
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        if stats.genre_counts:
            row1.addWidget(make_pie_chart("Géneros", stats.genre_counts))

        if stats.decade_counts:
            decades_clean = {k: v for k, v in stats.decade_counts.items() if k != "Sin año"}
            if decades_clean:
                keys = sorted(decades_clean.keys())
                row1.addWidget(make_bar_chart("Décadas", keys, [decades_clean[k] for k in keys]))

        if row1.count():
            layout.addLayout(row1)

        # Fila 2: formatos (torta) + ratings (barras)
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        if stats.format_counts:
            row2.addWidget(make_pie_chart("Formatos", stats.format_counts))

        rating_labels = ["Sin rating", "★", "★★", "★★★", "★★★★", "★★★★★"]
        rating_vals   = [stats.rating_counts.get(i, 0) for i in range(6)]
        if any(rating_vals):
            row2.addWidget(make_bar_chart("Ratings", rating_labels, rating_vals))

        if row2.count():
            layout.addLayout(row2)

        # Fila 3: top artistas (barras horizontales)
        if stats.top_artists:
            artists_rev = list(reversed(stats.top_artists))
            a_labels = [a[0][:22] for a in artists_rev]
            a_vals   = [a[1] for a in artists_rev]
            self._add_section_label(layout, "Top 10 artistas por cantidad de pistas")
            layout.addWidget(make_hbar_chart("", a_labels, a_vals))

        # Fila 4: top pistas (solo si hay alguna reproducida)
        max_plays = max((t[2] for t in stats.top_tracks), default=0)
        if stats.top_tracks and max_plays > 0:
            tracks_rev = list(reversed(stats.top_tracks))
            t_labels = [f"{t[0][:18]} — {t[1][:12]}" for t in tracks_rev]
            t_vals   = [t[2] for t in tracks_rev]
            self._add_section_label(layout, "Top 10 pistas más reproducidas")
            layout.addWidget(make_hbar_chart("", t_labels, t_vals))

    def _add_section_label(self, layout: QVBoxLayout, text: str) -> None:
        lbl = QLabel(text)
        lbl.setObjectName("statsSectionLabel")
        layout.addWidget(lbl)

    def _add_fallback_tables(self, layout: QVBoxLayout, stats: LibraryStats) -> None:
        """Tabla de texto simple cuando PyQt6-Charts no está disponible."""
        note = QLabel(
            "PyQt6-Charts no está instalado. Instale 'PyQt6-Charts' para ver gráficos.\n\n"
            "Estadísticas numéricas disponibles en la exportación XLSX."
        )
        note.setObjectName("statsSectionLabel")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)
