"""
ExportService — Exportación de la biblioteca de pistas.

Formatos soportados:
    XLSX — dos hojas: "Biblioteca" + "Estadísticas" (requiere openpyxl).
    PDF  — dos secciones con el mismo contenido (requiere fpdf2).
    CSV  — solo la biblioteca; sin estadísticas (stdlib csv).

Uso:
    svc = ExportService()
    svc.export_xlsx(tracks, stats, "/ruta/biblioteca.xlsx")
    svc.export_pdf(tracks, stats, "/ruta/biblioteca.pdf")
    svc.export_csv(tracks, "/ruta/biblioteca.csv")
"""
from __future__ import annotations

import csv
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audiorep.domain.track import Track
    from audiorep.services.stats_service import LibraryStats


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _ms_to_str(ms: int) -> str:
    if not ms:
        return "0:00"
    total_s = ms // 1000
    m, s = divmod(total_s, 60)
    return f"{m}:{s:02d}"


def _stars(rating: int) -> str:
    """Versión Unicode para XLSX (soporta ★☆)."""
    if rating <= 0:
        return "Sin rating"
    return "★" * rating + "☆" * (5 - rating)


def _stars_text(rating: int) -> str:
    """Versión ASCII para PDF (Helvetica no soporta ★☆)."""
    if rating <= 0:
        return "Sin rating"
    return f"{rating}/5"


# ---------------------------------------------------------------------------
# ExportService
# ---------------------------------------------------------------------------

class ExportService:
    """Exporta pistas y estadísticas a diferentes formatos de archivo."""

    # ------------------------------------------------------------------
    # XLSX
    # ------------------------------------------------------------------

    def export_xlsx(
        self,
        tracks: list[Track],
        stats:  LibraryStats,
        filepath: str,
    ) -> None:
        """Exporta a Excel con dos hojas: Biblioteca y Estadísticas."""
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = openpyxl.Workbook()

        # ── Hoja 1: Biblioteca ─────────────────────────────────────── #
        ws1 = wb.active
        ws1.title = "Biblioteca"

        # Tema profesional legible: cabecera gris oscuro, filas claras
        hdr_font  = Font(bold=True, color="FFFFFF", size=9)
        hdr_fill  = PatternFill("solid", fgColor="2D2D2D")
        alt_fill  = PatternFill("solid", fgColor="F2F2F2")
        data_font = Font(color="1A1A1A", size=9)
        center    = Alignment(horizontal="center")
        left      = Alignment(horizontal="left")

        headers    = ["#", "Título", "Artista", "Álbum", "Año", "Género", "Duración", "Formato"]
        col_widths = [5,    40,       25,         30,      6,     20,       10,          8]

        for col, (h, w) in enumerate(zip(headers, col_widths), 1):
            cell = ws1.cell(row=1, column=col, value=h)
            cell.font      = hdr_font
            cell.fill      = hdr_fill
            cell.alignment = center
            ws1.column_dimensions[cell.column_letter].width = w
        ws1.row_dimensions[1].height = 16

        for row_idx, t in enumerate(tracks, 2):
            is_alt = row_idx % 2 == 0
            vals = [
                row_idx - 1,
                t.title       or "",
                t.artist_name or "",
                t.album_title or "",
                t.year        or "",
                t.genre       or "",
                _ms_to_str(t.duration_ms),
                t.format.value if t.format else "",
            ]
            for col, val in enumerate(vals, 1):
                cell = ws1.cell(row=row_idx, column=col, value=val)
                cell.font      = data_font
                cell.alignment = center if col in (1, 5, 7, 8) else left
                if is_alt:
                    cell.fill = alt_fill

        ws1.freeze_panes = "A2"

        # ── Hoja 2: Estadísticas ───────────────────────────────────── #
        ws2 = wb.create_sheet("Estadísticas")
        ws2.column_dimensions["A"].width = 32
        ws2.column_dimensions["B"].width = 20
        ws2.column_dimensions["C"].width = 20

        section_font = Font(bold=True, size=12, color="1A1A1A")
        label_font   = Font(bold=True, color="FFFFFF", size=9)
        value_font   = Font(color="1A1A1A", size=9)
        hdr2_fill    = PatternFill("solid", fgColor="2D2D2D")
        alt2_fill    = PatternFill("solid", fgColor="F2F2F2")

        row = 1

        def section(title: str) -> None:
            nonlocal row
            ws2.cell(row=row, column=1, value=title).font = section_font
            row += 1

        def table_header(*cols: str) -> None:
            nonlocal row
            for col_idx, col in enumerate(cols, 1):
                cell = ws2.cell(row=row, column=col_idx, value=col)
                cell.font = label_font
                cell.fill = hdr2_fill
            row += 1

        def table_row(*vals: object) -> None:
            nonlocal row
            is_alt = row % 2 == 0
            for col_idx, val in enumerate(vals, 1):
                cell = ws2.cell(row=row, column=col_idx, value=val)
                cell.font = value_font
                if is_alt:
                    cell.fill = alt2_fill
            row += 1

        # Resumen
        section("Resumen general")
        hours = stats.total_duration_ms / 3_600_000
        table_header("Indicador", "Valor")
        table_row("Total pistas", stats.total_tracks)
        table_row("Total artistas", stats.total_artists)
        table_row("Total álbumes", stats.total_albums)
        table_row("Horas de música", f"{hours:.1f} h")
        table_row("Nacionalidades de artistas", stats.total_countries)
        row += 1

        # Géneros
        section("Géneros")
        table_header("Género", "Pistas")
        for g, c in sorted(stats.genre_counts.items(), key=lambda x: x[1], reverse=True):
            table_row(g, c)
        row += 1

        # Décadas
        section("Décadas")
        table_header("Década", "Pistas")
        for d, c in sorted(stats.decade_counts.items()):
            table_row(d, c)
        row += 1

        # Formatos
        section("Formatos")
        table_header("Formato", "Pistas")
        for f, c in sorted(stats.format_counts.items(), key=lambda x: x[1], reverse=True):
            table_row(f, c)
        row += 1

        # Top artistas
        section("Top 10 artistas por cantidad de pistas")
        table_header("Artista", "Pistas")
        for artist, count in stats.top_artists:
            table_row(artist, count)
        row += 1

        # Tipo de álbum
        if stats.album_type_counts:
            section("Tipo de álbum")
            table_header("Tipo", "Álbumes")
            for t, c in sorted(stats.album_type_counts.items(), key=lambda x: x[1], reverse=True):
                table_row(t, c)
            row += 1

        # País de origen de artistas
        if stats.artist_country_counts:
            section("País de origen de artistas")
            table_header("País", "Artistas")
            for country, count in sorted(stats.artist_country_counts.items(), key=lambda x: x[1], reverse=True):
                table_row(country, count)
            row += 1

        # País de origen de sellos
        if stats.label_country_counts:
            section("País de origen de sellos")
            table_header("País", "Sellos")
            for country, count in sorted(stats.label_country_counts.items(), key=lambda x: x[1], reverse=True):
                table_row(country, count)

        wb.save(filepath)

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def export_pdf(
        self,
        tracks: list[Track],
        stats:  LibraryStats,
        filepath: str,
    ) -> None:
        """Exporta a PDF con dos secciones: Biblioteca y Estadísticas."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(10, 10, 10)

        # ── Sección 1: Biblioteca ──────────────────────────────────── #
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "AudioRep - Biblioteca de pistas", ln=True)
        pdf.set_font("Helvetica", size=7)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 5, f"{stats.total_tracks} pistas  |  {stats.total_artists} artistas  |  {stats.total_albums} albums  |  {stats.total_duration_ms / 3_600_000:.1f} horas", ln=True)
        pdf.ln(3)

        col_w = [8, 52, 32, 36, 10, 20, 14, 12]
        headers = ["#", "Titulo", "Artista", "Album", "Ano", "Genero", "Dur.", "Fmt"]

        # Cabecera: gris claro con texto negro
        pdf.set_fill_color(210, 210, 210)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 7)
        for w, h in zip(col_w, headers):
            pdf.cell(w, 5, h, border=1, fill=True)
        pdf.ln()

        for i, t in enumerate(tracks, 1):
            is_alt = i % 2 == 0
            if is_alt:
                pdf.set_fill_color(242, 242, 242)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", size=7)

            row_vals = [
                str(i),
                (t.title or "")[:38],
                (t.artist_name or "")[:22],
                (t.album_title or "")[:24],
                str(t.year or ""),
                (t.genre or "")[:14],
                _ms_to_str(t.duration_ms),
                (t.format.value if t.format else "")[:6],
            ]
            for w, val in zip(col_w, row_vals):
                pdf.cell(w, 4, val, border="B", fill=True)
            pdf.ln()

        # ── Sección 2: Estadísticas ────────────────────────────────── #
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "AudioRep - Estadisticas de la biblioteca", ln=True)
        pdf.ln(2)

        def _pdf_section(title: str) -> None:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, title, ln=True)

        def _pdf_table(headers_row: list[str], rows: list[tuple], col_widths: list[int]) -> None:
            pdf.set_fill_color(210, 210, 210)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "B", 8)
            for h, w in zip(headers_row, col_widths):
                pdf.cell(w, 5, h, border=1, fill=True)
            pdf.ln()

            for i, row_data in enumerate(rows):
                is_alt = i % 2 == 0
                if is_alt:
                    pdf.set_fill_color(242, 242, 242)
                else:
                    pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", size=8)
                for val, w in zip(row_data, col_widths):
                    pdf.cell(w, 4, str(val)[:24], border="B", fill=True)
                pdf.ln()
            pdf.ln(3)

        # Resumen
        _pdf_section("Resumen general")
        hours = stats.total_duration_ms / 3_600_000
        _pdf_table(
            ["Indicador", "Valor"],
            [
                ("Total pistas",                stats.total_tracks),
                ("Total artistas",              stats.total_artists),
                ("Total albums",                stats.total_albums),
                ("Horas de musica",             f"{hours:.1f} h"),
                ("Nacionalidades de artistas",  stats.total_countries),
            ],
            [80, 50],
        )

        # Géneros
        _pdf_section("Generos")
        genre_rows = sorted(stats.genre_counts.items(), key=lambda x: x[1], reverse=True)
        _pdf_table(["Genero", "Pistas"], [(g, c) for g, c in genre_rows], [80, 30])

        # Décadas
        _pdf_section("Decadas")
        decade_rows = sorted(stats.decade_counts.items())
        _pdf_table(["Decada", "Pistas"], [(d, c) for d, c in decade_rows], [40, 30])

        # Formatos
        _pdf_section("Formatos")
        fmt_rows = sorted(stats.format_counts.items(), key=lambda x: x[1], reverse=True)
        _pdf_table(["Formato", "Pistas"], [(f, c) for f, c in fmt_rows], [40, 30])

        # Top artistas
        _pdf_section("Top 10 artistas por pistas")
        _pdf_table(["Artista", "Pistas"], stats.top_artists, [90, 30])

        # Tipo de album
        if stats.album_type_counts:
            _pdf_section("Tipo de album")
            rows_type = sorted(stats.album_type_counts.items(), key=lambda x: x[1], reverse=True)
            _pdf_table(["Tipo", "Albumes"], rows_type, [60, 30])

        # Pais de origen de artistas
        if stats.artist_country_counts:
            _pdf_section("Pais de origen de artistas")
            rows_ac = sorted(stats.artist_country_counts.items(), key=lambda x: x[1], reverse=True)
            _pdf_table(["Pais", "Artistas"], rows_ac, [80, 30])

        # Pais de origen de sellos
        if stats.label_country_counts:
            _pdf_section("Pais de origen de sellos")
            rows_lc = sorted(stats.label_country_counts.items(), key=lambda x: x[1], reverse=True)
            _pdf_table(["Pais", "Sellos"], rows_lc, [80, 30])

        pdf.output(filepath)

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def export_csv(self, tracks: list[Track], filepath: str) -> None:
        """Exporta solo la biblioteca a CSV (UTF-8 con BOM para Excel)."""
        fieldnames = ["#", "Título", "Artista", "Álbum", "Año", "Género", "Duración", "Formato"]
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for i, t in enumerate(tracks, 1):
                writer.writerow({
                    "#":         i,
                    "Título":    t.title       or "",
                    "Artista":   t.artist_name or "",
                    "Álbum":     t.album_title or "",
                    "Año":       t.year        or "",
                    "Género":    t.genre       or "",
                    "Duración":  _ms_to_str(t.duration_ms),
                    "Formato":   t.format.value if t.format else "",
                })
