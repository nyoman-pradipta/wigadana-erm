"""Generator PDF rekam medis & resep (ReportLab Platypus, ukuran A5).

Font unicode: cari TTF yang tersedia di sistem (DejaVu di Linux/Docker,
Arial Unicode di macOS). Kalau tidak ketemu, fallback Helvetica (Latin-1).
"""
import os
from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import settings

# ===== Font unicode =====
_FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def _find_font(kind: str) -> str | None:
    for path in _FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return path
    return None


FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
_reg = _find_font("regular")
if _reg:
    pdfmetrics.registerFont(TTFont("ClinicFont", _reg))
    FONT = "ClinicFont"
    _bold = _find_font("bold")
    if _bold:
        pdfmetrics.registerFont(TTFont("ClinicFont-Bold", _bold))
        FONT_BOLD = "ClinicFont-Bold"
    else:
        FONT_BOLD = "ClinicFont"


# ===== Styles =====
def _styles() -> dict:
    return {
        "clinic": ParagraphStyle("clinic", fontName=FONT_BOLD, fontSize=15, leading=18),
        "clinic_info": ParagraphStyle("clinic_info", fontName=FONT, fontSize=8.5, leading=11, textColor=colors.HexColor("#444444")),
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=11, leading=14, alignment=1, spaceBefore=6),
        "label": ParagraphStyle("label", fontName=FONT_BOLD, fontSize=9, leading=12),
        "body": ParagraphStyle("body", fontName=FONT, fontSize=9, leading=13),
        "small": ParagraphStyle("small", fontName=FONT, fontSize=8, leading=11, textColor=colors.HexColor("#555555")),
    }


def _klinik_header(elements, styles: dict) -> None:
    elements.append(Paragraph(settings.CLINIC_NAME or "Klinik", styles["clinic"]))
    info = ", ".join(x for x in [settings.CLINIC_ADDRESS, settings.CLINIC_PHONE] if x)
    if info:
        elements.append(Paragraph(info, styles["clinic_info"]))
    elements.append(Spacer(1, 2))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#0f766e")))
    elements.append(Spacer(1, 6))


def _field_table(rows: list[tuple[str, str]]) -> Table:
    def fmt(v: str) -> str:
        # escape HTML + pertahankan baris baru (Paragraph render <br/>)
        return escape(str(v or "—")).replace("\n", "<br/>")

    data = []
    for label, value in rows:
        data.append([Paragraph(label, _styles()["label"]), Paragraph(fmt(value), _styles()["body"])])
    t = Table(data, colWidths=[32 * mm, 92 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _tanda_vital_table(visit) -> Table:
    cells = [
        ("TB", f"{visit.tb or '-'} cm"),
        ("BB", f"{visit.bb or '-'} kg"),
        ("TD", visit.td or "-"),
        ("Suhu", f"{visit.suhu or '-'} °C"),
        ("HR", f"{visit.hr or '-'} x/mnt"),
        ("RR", f"{visit.rr or '-'} x/mnt"),
    ]
    data = []
    row = []
    for i, (label, value) in enumerate(cells):
        row.append(f"<b>{label}:</b> {value}")
        if i % 3 == 2:
            data.append(row)
            row = []
    if row:
        data.append(row)
    t = Table([[Paragraph(c, _styles()["body"]) for c in r] for r in data])
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _make_doc(title: str) -> tuple[SimpleDocTemplate, BytesIO]:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A5, title=title,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
    )
    return doc, buf


def build_rekam_medis_pdf(visit) -> bytes:
    s = _styles()
    doc, buf = _make_doc(f"Rekam Medis {visit.patient.no_rm}")
    elements = []
    _klinik_header(elements, s)
    elements.append(Paragraph("REKAM MEDIS", s["title"]))
    elements.append(Spacer(1, 6))

    p = visit.patient

    # ⚠ Blok alergi obat — WAJIB menonjol, sebelum data lain/anamnesa
    if p.riwayat_alergi_obat.strip():
        alergi_style = ParagraphStyle(
            "alergi_obat", fontName=FONT_BOLD, fontSize=10.5,
            textColor=colors.HexColor("#b91c1c"), spaceAfter=4,
        )
        elements.append(Paragraph(f"⚠ ALERGI OBAT: {escape(p.riwayat_alergi_obat)}", alergi_style))
    else:
        elements.append(Paragraph("⚠ Alergi Obat: Tidak ada tercatat", s["small"]))
    elements.append(Spacer(1, 6))

    elements.append(_field_table([
        ("Nama", p.nama),
        ("No. RM", p.no_rm),
        ("Identitas", f"{p.jenis_identitas} {p.no_identitas or '-'}".strip()),
        ("No. HP", p.no_hp),
        ("Alamat", p.alamat),
        ("Alergi Lain", p.riwayat_alergi or "Tidak ada"),
    ]))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("Pemeriksaan", s["label"]))
    elements.append(Spacer(1, 3))
    elements.append(_field_table([
        ("Tanggal", str(visit.tgl_pemeriksaan or "-")),
        ("Anamnesa", visit.anamnesa),
    ]))
    elements.append(Spacer(1, 5))
    elements.append(_tanda_vital_table(visit))
    elements.append(Spacer(1, 5))
    elements.append(_field_table([
        ("Pemeriksaan Fisik", visit.pemeriksaan_fisik),
        ("Diagnosa", visit.diagnosa),
        ("Terapi", visit.terapi),
    ]))
    elements.append(Spacer(1, 12))

    dokter = visit.doctor.nama if visit.doctor else "-"
    elements.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cccccc")))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(
        f"Ditangani: <b>{dokter}</b> &nbsp;|&nbsp; Dicetak: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        s["small"],
    ))

    doc.build(elements)
    return buf.getvalue()


def build_resep_pdf(visit) -> bytes:
    s = _styles()
    doc, buf = _make_doc(f"Resep {visit.patient.no_rm}")
    elements = []
    _klinik_header(elements, s)

    # Blok dokter (kanan)
    dokter = visit.doctor
    nama_dokter = dokter.nama if dokter else "-"
    sip = f"SIP: {dokter.no_sip}" if dokter and dokter.no_sip else "SIP: -"
    t_dokter = Table(
        [[Paragraph(f"<b>{nama_dokter}</b>", s["body"]), Paragraph(sip, s["body"])]],
        colWidths=[62 * mm, 62 * mm],
    )
    t_dokter.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    elements.append(t_dokter)
    elements.append(Spacer(1, 4))

    p = visit.patient
    elements.append(_field_table([
        ("Nama", p.nama),
        ("No. RM", p.no_rm),
        ("Tanggal", str(visit.tgl_pemeriksaan or datetime.now().date())),
    ]))
    elements.append(Spacer(1, 8))

    # Isi resep: setiap baris terapi = satu item obat
    elements.append(Paragraph("R/", ParagraphStyle("rx", fontName=FONT_BOLD, fontSize=13, leading=16)))
    elements.append(Spacer(1, 2))
    items = [escape(ln.strip()) for ln in (visit.terapi or "").split("\n") if ln.strip()]
    if not items:
        items = ["—"]
    t_resep = Table([[Paragraph(ln, s["body"])] for ln in items], colWidths=[100 * mm])
    t_resep.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#eeeeee")),
    ]))
    elements.append(t_resep)
    elements.append(Spacer(1, 24))

    # Area tanda tangan
    t_ttd = Table(
        [["", ""], ["", f"({nama_dokter})"]],
        colWidths=[62 * mm, 62 * mm],
    )
    t_ttd.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (1, 0), (1, 0), 18),
        ("LINEABOVE", (1, 0), (1, 0), 0.6, colors.black),
    ]))
    elements.append(t_ttd)
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Dicetak: {datetime.now().strftime('%d-%m-%Y %H:%M')}", s["small"]))

    doc.build(elements)
    return buf.getvalue()


def build_surat_sakit_pdf(visit) -> bytes:
    """Surat Keterangan Sakit — dicetak kalau pasien minta setelah pemeriksaan.
    Butuh surat_sakit_tgl_mulai & surat_sakit_tgl_selesai terisi di visit."""
    s = _styles()
    p = visit.patient
    doc, buf = _make_doc(f"Surat Sakit {p.no_rm}")
    elements = []
    _klinik_header(elements, s)
    elements.append(Paragraph("SURAT KETERANGAN SAKIT", s["title"]))
    elements.append(Spacer(1, 10))

    usia = f"{p.usia} tahun" if p.usia is not None else "-"
    elements.append(_field_table([
        ("Nama", p.nama),
        ("Usia", usia),
        ("Alamat", p.alamat or "-"),
        ("Pekerjaan", p.pekerjaan or "-"),
    ]))
    elements.append(Spacer(1, 10))

    tgl_mulai = visit.surat_sakit_tgl_mulai.strftime("%d-%m-%Y") if visit.surat_sakit_tgl_mulai else "-"
    tgl_selesai = visit.surat_sakit_tgl_selesai.strftime("%d-%m-%Y") if visit.surat_sakit_tgl_selesai else "-"
    diagnosa = escape(visit.diagnosa or "-")
    nama_pasien = escape(p.nama)
    body_text = (
        f"Yang bertanda tangan di bawah ini menerangkan bahwa benar pasien atas nama "
        f"<b>{nama_pasien}</b> telah diperiksa dan berobat, dengan diagnosa "
        f"<b>{diagnosa}</b>, dan perlu istirahat pada tanggal "
        f"<b>{escape(tgl_mulai)}</b> sampai dengan <b>{escape(tgl_selesai)}</b>."
    )
    elements.append(Paragraph(body_text, ParagraphStyle(
        "surat_body", fontName=FONT, fontSize=10, leading=16, alignment=4,  # justify
    )))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Demikian surat keterangan ini dibuat dengan sebenarnya untuk dipergunakan sebagaimana mestinya.",
        ParagraphStyle("surat_penutup", fontName=FONT, fontSize=10, leading=14),
    ))
    elements.append(Spacer(1, 26))

    dokter = visit.doctor
    nama_dokter = dokter.nama if dokter else "-"
    tgl_cetak = datetime.now().strftime("%d-%m-%Y")
    t_ttd = Table(
        [[f"{tgl_cetak}"], [""], [""], [f"({nama_dokter})"]],
        colWidths=[62 * mm],
    )
    t_ttd.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (0, -1), 62 * mm),
        ("TOPPADDING", (0, 3), (0, 3), 4),
        ("LINEABOVE", (0, 3), (0, 3), 0.6, colors.black),
    ]))
    elements.append(t_ttd)

    doc.build(elements)
    return buf.getvalue()
