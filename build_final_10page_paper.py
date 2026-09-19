# build_final_10page_paper.py
import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pypdf import PdfReader

import manuscript_content as mc

# ==============================================================================
# 1. REPORTLAB NUMBERED CANVAS (PAGE X OF Y & RUNNING HEADERS)
# ==============================================================================
class AcademicNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(AcademicNumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(AcademicNumberedCanvas, self).showPage()
        super(AcademicNumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Times-Roman", 9)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (Pages >= 2)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "Traxion AI: Real-Time Road Accident & Fall Kinematics Intelligence")
            self.drawRightString(8.5 * 72 - 54, 11 * 72 - 36, "Research Manuscript")
            self.setStrokeColor(colors.HexColor("#94a3b8"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 40, 8.5 * 72 - 54, 11 * 72 - 40)

        # Footer (All pages)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 36, footer_text)
        self.drawString(54, 36, "Traxion AI Framework — Comprehensive Research Manuscript")
        self.setStrokeColor(colors.HexColor("#94a3b8"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)
        self.restoreState()


# ==============================================================================
# 2. BUILD REPORTLAB PDF MANUSCRIPT
# ==============================================================================
def build_pdf(pdf_path):
    print(f"Generating PDF: {pdf_path}")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,  # 0.75 in
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Academic Styles in Times-Roman
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=20,
        leading=24,
        alignment=1,  # Center
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        alignment=1,  # Center
        textColor=colors.HexColor("#334155"),
        spaceAfter=14
    )

    abs_heading = ParagraphStyle(
        'AbsHeading',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=11,
        leading=15,
        alignment=0,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=4
    )

    abs_body = ParagraphStyle(
        'AbsBody',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=9.5,
        leading=14,
        alignment=4,  # Justify
        firstLineIndent=16,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=8
    )

    sec_h1 = ParagraphStyle(
        'SecH1',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=13,
        leading=17,
        alignment=0,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    sec_h2 = ParagraphStyle(
        'SecH2',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=11,
        leading=15,
        alignment=0,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'AcademicBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14.5,
        alignment=4,  # JUSTIFY
        firstLineIndent=18,  # First line indent
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )

    formula_style = ParagraphStyle(
        'FormulaStyle',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=13,
        alignment=1,  # Center
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=4,
        spaceAfter=6
    )

    caption_style = ParagraphStyle(
        'FigCaption',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=9,
        leading=13,
        alignment=1,  # Center
        textColor=colors.HexColor("#334155"),
        spaceBefore=5,
        spaceAfter=12
    )

    tbl_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=0,
        textColor=colors.HexColor("#0f172a")
    )

    tbl_header_style = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=8.5,
        leading=12,
        alignment=0,
        textColor=colors.white
    )

    story = []

    # Title & Metadata
    story.append(Paragraph(mc.TITLE, title_style))
    story.append(Paragraph(f"<b>{mc.AUTHORS}</b><br/>{mc.AFFILIATIONS}", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    # Abstract & Keywords
    story.append(Paragraph("<b>ABSTRACT</b>", abs_heading))
    for p in mc.ABSTRACT.split("\n\n"):
        story.append(Paragraph(p, abs_body))
    story.append(Paragraph(f"<b>Keywords:</b> <i>{mc.KEYWORDS}</i>", abs_body))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=8, spaceAfter=14))

    # Helper function for inserting tables
    def make_rl_table(headers, data, col_widths=None):
        table_data = []
        hdr_row = [Paragraph(h, tbl_header_style) for h in headers]
        table_data.append(hdr_row)
        for row in data:
            r = [Paragraph(str(cell), tbl_cell_style) for cell in row]
            table_data.append(r)
        
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        return t

    # Helper function for inserting images
    def make_rl_img(img_path, width_in=6.6, height_in=2.5):
        if os.path.exists(img_path):
            img = RLImage(img_path, width=width_in * inch, height=height_in * inch)
            return img
        return None

    # SECTION 1: INTRODUCTION
    story.append(Paragraph("1. INTRODUCTION", sec_h1))
    for p in mc.SEC_1_INTRO:
        story.append(Paragraph(p, body_style))

    # Figure 1: Pipeline Architecture
    f1_img = make_rl_img(os.path.join("paper_assets", "fig1_pipeline_large.png"), 6.6, 2.4)
    if f1_img:
        story.append(Spacer(1, 6))
        story.append(f1_img)
        story.append(Paragraph("<b>Figure 1.</b> End-to-end Traxion AI operational pipeline showing dual-stream video ingestion, single-stage 17-keypoint deep pose estimation, scale-invariant angular kinematic feature extraction, explainable 3D digital twin synchronization, and automated emergency triage gateway.", caption_style))

    # SECTION 2: LITERATURE REVIEW
    story.append(Paragraph("2. LITERATURE REVIEW AND TAXONOMY", sec_h1))
    for p in mc.SEC_2_LIT_REVIEW:
        story.append(Paragraph(p, body_style))

    # Table 1: Comparative Taxonomy
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 1.</b> Comparative architectural taxonomy of vision-based and wearable fall detection methodologies.", caption_style))
    story.append(make_rl_table(mc.TABLE_1_HEADERS, mc.TABLE_1_DATA, col_widths=[90, 80, 80, 80, 85, 85]))
    story.append(Spacer(1, 10))

    # SECTION 3: THEORETICAL FOUNDATIONS & KINEMATICS
    story.append(Paragraph("3. THEORETICAL FOUNDATIONS AND MATHEMATICAL KINEMATICS", sec_h1))
    for p in mc.SEC_3_METHODOLOGY:
        lines = p.strip().split("\n")
        if len(lines) > 1 and ("=" in lines[1] or "arctan2" in lines[1] or "Delta" in lines[1] or "S_mid" in lines[1]):
            story.append(Paragraph(lines[0], sec_h2 if lines[0].startswith("3.") else body_style))
            for fline in lines[1:]:
                if any(sym in fline for sym in ["=", "Delta", "arctan2", "max(", "min(", "arccos"]):
                    story.append(Paragraph(f"<i>{fline}</i>", formula_style))
                else:
                    story.append(Paragraph(fline, body_style))
        else:
            if p.startswith("3."):
                story.append(Paragraph(p, sec_h2))
            else:
                story.append(Paragraph(p, body_style))

    # Table 2: Mathematical Formulations
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 2.</b> Biomechanical kinematic formulations, normal physiological ranges, critical accident thresholds, and clinical rationale.", caption_style))
    story.append(make_rl_table(mc.TABLE_2_HEADERS, mc.TABLE_2_DATA, col_widths=[105, 120, 85, 85, 105]))
    story.append(Spacer(1, 10))

    # Figure 2: 3D Skeletal Twin
    f2_img = make_rl_img(os.path.join("paper_assets", "fig2_3d_skeletal_twin.png"), 6.6, 2.3)
    if f2_img:
        story.append(Spacer(1, 6))
        story.append(f2_img)
        story.append(Paragraph("<b>Figure 2.</b> Real-time explainable 3D biomechanical digital twin rendered across three clinical posture regimes: (A) Nominal Upright Locomotion (θ = 85.4°, AR = 0.42), (B) Unstable Posture / Stumble Hazard (θ = 48.2°, AR = 0.81), and (C) Catastrophic Road Collapse (θ = 14.8°, AR = 1.44) with illuminated cranial and spinal trauma zones.", caption_style))

    # SECTION 4: ROADSENTRY AI ARCHITECTURE AND UI
    story.append(Paragraph("4. ROADSENTRY AI ARCHITECTURE AND OPERATIONAL UI", sec_h1))
    for p in mc.SEC_4_ARCHITECTURE_AND_UI:
        if p.startswith("4."):
            story.append(Paragraph(p, sec_h2))
        else:
            story.append(Paragraph(p, body_style))

    # Figure 3: UI Architecture
    f3_img = make_rl_img(os.path.join("paper_assets", "fig3_ui_architecture.png"), 6.6, 3.0)
    if f3_img:
        story.append(Spacer(1, 6))
        story.append(f3_img)
        story.append(Paragraph("<b>Figure 3.</b> Traxion AI full operational interface architecture: Top telemetry navigation bar, interactive 3D WebGL skeletal mannequin, 3-state traffic signal telemetry console (Green / Amber / Red), live HUD camera feed with 17-keypoint overlays, H.264 video analysis timeline with collision jump markers, and automated 108 Emergency Ambulance dispatch hub.", caption_style))

    # SECTION 5: MULTI-ZONE TRAUMA TRIAGE
    story.append(Paragraph("5. MULTI-ZONE ANATOMICAL TRAUMA TRIAGE LOGIC", sec_h1))
    for p in mc.SEC_5_TRAUMA_TRIAGE:
        if "FSI =" in p:
            parts = p.split("\n")
            for part in parts:
                if "FSI =" in part:
                    story.append(Paragraph(f"<i>{part}</i>", formula_style))
                else:
                    story.append(Paragraph(part, body_style))
        else:
            story.append(Paragraph(p, body_style))

    # Figure 4: Trauma Logic Flowchart
    f4_img = make_rl_img(os.path.join("paper_assets", "fig4_trauma_logic_large.png"), 6.6, 2.7)
    if f4_img:
        story.append(Spacer(1, 6))
        story.append(f4_img)
        story.append(Paragraph("<b>Figure 4.</b> Multi-zone anatomical trauma triage decision logic: Continuous ingestion of 17 keypoints into parallel cranial, spinal, lower-extremity, and upper-extremity clinical scoring filters, computing the composite Fall Severity Index (FSI) to drive deterministic 3-tier emergency escalations.", caption_style))

    # SECTION 6: EXPERIMENTAL BENCHMARK DATASET
    story.append(Paragraph("6. HIGHWAY ACCIDENT EVALUATION BENCHMARK", sec_h1))
    for p in mc.SEC_6_EXPERIMENTS:
        story.append(Paragraph(p, body_style))

    # Table 3: Dataset Characteristics
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 3.</b> Distribution and kinematic characteristics of the 1,240 evaluation video sequences across highway monitoring categories.", caption_style))
    story.append(make_rl_table(mc.TABLE_3_HEADERS, mc.TABLE_3_DATA, col_widths=[110, 75, 75, 125, 115]))
    story.append(Spacer(1, 10))

    # SECTION 7: QUANTITATIVE RESULTS & BENCHMARKS
    story.append(Paragraph("7. RESULTS AND QUANTITATIVE EVALUATION", sec_h1))
    for p in mc.SEC_7_RESULTS:
        if p.startswith("7."):
            story.append(Paragraph(p, sec_h2))
        else:
            story.append(Paragraph(p, body_style))

    # Table 4: Benchmark Comparison
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 4.</b> Comparative performance evaluation of Traxion AI against baseline fall and accident detection architectures.", caption_style))
    story.append(make_rl_table(mc.TABLE_4_HEADERS, mc.TABLE_4_DATA, col_widths=[125, 60, 60, 65, 65, 65, 60]))
    story.append(Spacer(1, 10))

    # Figure 5: Benchmarks & Confusion Matrix
    f5_img = make_rl_img(os.path.join("paper_assets", "fig5_benchmarks_confusion_large.png"), 6.6, 2.7)
    if f5_img:
        story.append(Spacer(1, 6))
        story.append(f5_img)
        story.append(Paragraph("<b>Figure 5.</b> Quantitative evaluation results: (A) Multi-class confusion matrix over 1,240 labeled highway sequences, demonstrating 99.4% recall on severe accidents, and (B) Baseline benchmark comparisons highlighting the superior balance of precision, recall, and CPU inference throughput achieved by Traxion AI.", caption_style))

    # SECTION 8: QUALITATIVE CASE STUDIES
    story.append(Paragraph("8. QUALITATIVE CASE STUDIES AND EDGE-CASE ROBUSTNESS", sec_h1))
    for p in mc.SEC_8_CASE_STUDIES:
        if p.startswith("8."):
            story.append(Paragraph(p, sec_h2))
        else:
            story.append(Paragraph(p, body_style))

    # Table 5: Case Study Kinematic Trace
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 5.</b> Detailed frame-by-frame kinematic vector trace across positive collisions and difficult negative control edge cases.", caption_style))
    story.append(make_rl_table(mc.TABLE_5_HEADERS, mc.TABLE_5_DATA, col_widths=[130, 55, 60, 75, 65, 55, 60]))
    story.append(Spacer(1, 10))

    # SECTION 9: ABLATION STUDY
    story.append(Paragraph("9. SYSTEMATIC ABLATION STUDY", sec_h1))
    for p in mc.SEC_9_ABLATION:
        story.append(Paragraph(p, body_style))

    # Table 6: Ablation Study
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Table 6.</b> Systematic ablation analysis demonstrating the empirical necessity of individual kinematic vector components.", caption_style))
    story.append(make_rl_table(mc.TABLE_6_HEADERS, mc.TABLE_6_DATA, col_widths=[140, 110, 60, 60, 65, 65]))
    story.append(Spacer(1, 10))

    # SECTION 10: OPERATIONAL DEPLOYMENT & 108 INTEGRATION
    story.append(Paragraph("10. OPERATIONAL DEPLOYMENT AND EMERGENCY GATEWAY", sec_h1))
    for p in mc.SEC_10_DEPLOYMENT:
        if p.startswith("10."):
            story.append(Paragraph(p, sec_h2))
        else:
            story.append(Paragraph(p, body_style))

    # SECTION 11: LIMITATIONS & PRIVACY
    story.append(Paragraph("11. LIMITATIONS, EDGE CONDITIONS, AND ETHICAL PRIVACY", sec_h1))
    for p in mc.SEC_11_ETHICAL_LIMITATIONS:
        if p.startswith("11."):
            story.append(Paragraph(p, sec_h2))
        else:
            story.append(Paragraph(p, body_style))

    # SECTION 12: CONCLUSION & FUTURE SCOPE
    story.append(Paragraph("12. CONCLUSION AND FUTURE SCOPE", sec_h1))
    for p in mc.SEC_12_CONCLUSION:
        story.append(Paragraph(p, body_style))

    # ACKNOWLEDGEMENT
    story.append(Paragraph("ACKNOWLEDGMENT", sec_h1))
    story.append(Paragraph(mc.ACKNOWLEDGEMENT_TEXT, body_style))

    # REFERENCES
    story.append(Paragraph("REFERENCES", sec_h1))
    ref_style = ParagraphStyle(
        'RefStyle',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11.5,
        alignment=4,  # Justify
        firstLineIndent=-14,
        leftIndent=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2.5
    )
    for ref in mc.REFERENCES_LIST:
        story.append(Paragraph(ref, ref_style))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=AcademicNumberedCanvas)
    print("PDF build finished.")


# ==============================================================================
# 3. BUILD DOCX MANUSCRIPT
# ==============================================================================
def build_docx(docx_path):
    print(f"Generating DOCX: {docx_path}")
    doc = docx.Document()

    # Page Margins: 0.75 in (54 pt)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        
        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Traxion AI: Real-Time Road Accident & Fall Kinematics Intelligence | Research Manuscript")
        hrun.font.name = "Times New Roman"
        hrun.font.size = Pt(8.5)
        hrun.font.italic = True
        hrun.font.color.rgb = RGBColor(100, 116, 139)

        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Traxion AI Framework — Comprehensive Research Manuscript")
        frun.font.name = "Times New Roman"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(100, 116, 139)

    # Base styling helper
    def add_p(text, style_type="body", bold=False, italic=False, size_pt=10, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_indent=0.25, space_before=0, space_after=4):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.first_line_indent = Inches(first_indent) if first_indent > 0 else 0
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = RGBColor(15, 23, 42)
        return p

    def add_heading1(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = 0
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(15, 23, 42)
        return p

    def add_heading2(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = 0
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = 0
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(10)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = RGBColor(71, 85, 105)
        return p

    def add_docx_table(headers, data):
        table = doc.add_table(rows=len(data) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        
        # Format Header Row
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            cell = hdr_cells[i]
            cell.text = header_text
            shading = parse_xml(r'<w:shd {} w:fill="1E293B"/>'.format(nsdecls('w')))
            cell._tc.get_or_add_tcPr().append(shading)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(8.5)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(255, 255, 255)

        # Format Data Rows
        for row_idx, row_data in enumerate(data):
            row_cells = table.rows[row_idx + 1].cells
            bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
            for col_idx, cell_value in enumerate(row_data):
                cell = row_cells[col_idx]
                cell.text = str(cell_value)
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), bg_color))
                cell._tc.get_or_add_tcPr().append(shading)
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for r in p.runs:
                        r.font.name = "Times New Roman"
                        r.font.size = Pt(8.5)
                        r.font.color.rgb = RGBColor(15, 23, 42)

        # Set subtle borders
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            r'<w:tblBorders {} '
            r'w:top="single" w:top-sz="4" w:top-space="0" w:top-color="CBD5E1" '
            r'w:bottom="single" w:bottom-sz="4" w:bottom-space="0" w:bottom-color="CBD5E1" '
            r'w:left="none" w:right="none" '
            r'w:insideH="single" w:insideH-sz="4" w:insideH-space="0" w:insideH-color="E2E8F0" '
            r'w:insideV="none"/>'.format(nsdecls('w'))
        )
        tblPr.append(borders)
        add_p("", first_indent=0, space_after=4)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run(mc.TITLE)
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(18)
    r_title.font.bold = True

    # Authors & Affiliations
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(14)
    r_author = p_meta.add_run(f"{mc.AUTHORS}\n")
    r_author.font.name = "Times New Roman"
    r_author.font.size = Pt(10)
    r_author.font.bold = True
    r_affil = p_meta.add_run(mc.AFFILIATIONS)
    r_affil.font.name = "Times New Roman"
    r_affil.font.size = Pt(9.5)
    r_affil.font.color.rgb = RGBColor(71, 85, 105)

    # Abstract & Keywords
    add_heading1("ABSTRACT")
    for p in mc.ABSTRACT.split("\n\n"):
        add_p(p, italic=True, size_pt=9.5, first_indent=0.25, space_after=6)
    p_kw = add_p(f"Keywords: {mc.KEYWORDS}", bold=False, italic=True, size_pt=9.5, first_indent=0.25, space_after=12)

    # SECTION 1
    add_heading1("1. INTRODUCTION")
    for p in mc.SEC_1_INTRO:
        add_p(p)

    # Figure 1
    f1_path = os.path.join("paper_assets", "fig1_pipeline_large.png")
    if os.path.exists(f1_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(f1_path, width=Inches(6.8))
        add_caption("Figure 1. End-to-end Traxion AI operational pipeline showing dual-stream video ingestion, single-stage 17-keypoint deep pose estimation, scale-invariant angular kinematic feature extraction, explainable 3D digital twin synchronization, and automated emergency triage gateway.")

    # SECTION 2
    add_heading1("2. LITERATURE REVIEW AND TAXONOMY")
    for p in mc.SEC_2_LIT_REVIEW:
        add_p(p)

    add_caption("Table 1. Comparative architectural taxonomy of vision-based and wearable fall detection methodologies.")
    add_docx_table(mc.TABLE_1_HEADERS, mc.TABLE_1_DATA)

    # SECTION 3
    add_heading1("3. THEORETICAL FOUNDATIONS AND MATHEMATICAL KINEMATICS")
    for p in mc.SEC_3_METHODOLOGY:
        lines = p.strip().split("\n")
        if p.startswith("3."):
            add_heading2(lines[0])
            for l in lines[1:]:
                if any(sym in l for sym in ["=", "Delta", "arctan2", "max(", "min(", "arccos"]):
                    p_f = doc.add_paragraph()
                    p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_f.paragraph_format.first_line_indent = 0
                    p_f.paragraph_format.space_before = Pt(2)
                    p_f.paragraph_format.space_after = Pt(4)
                    r = p_f.add_run(l)
                    r.font.name = "Courier New"
                    r.font.size = Pt(9)
                    r.font.bold = True
                else:
                    add_p(l)
        else:
            add_p(p)

    add_caption("Table 2. Biomechanical kinematic formulations, normal physiological ranges, critical accident thresholds, and clinical rationale.")
    add_docx_table(mc.TABLE_2_HEADERS, mc.TABLE_2_DATA)

    # Figure 2: 3D Twin
    f2_path = os.path.join("paper_assets", "fig2_3d_skeletal_twin.png")
    if os.path.exists(f2_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(f2_path, width=Inches(6.8))
        add_caption("Figure 2. Real-time explainable 3D biomechanical digital twin rendered across three clinical posture regimes: (A) Nominal Upright Locomotion (θ = 85.4°, AR = 0.42), (B) Unstable Posture / Stumble Hazard (θ = 48.2°, AR = 0.81), and (C) Catastrophic Road Collapse (θ = 14.8°, AR = 1.44) with illuminated cranial and spinal trauma zones.")

    # SECTION 4
    add_heading1("4. ROADSENTRY AI ARCHITECTURE AND OPERATIONAL UI")
    for p in mc.SEC_4_ARCHITECTURE_AND_UI:
        if p.startswith("4."):
            add_heading2(p)
        else:
            add_p(p)

    # Figure 3: UI Architecture
    f3_path = os.path.join("paper_assets", "fig3_ui_architecture.png")
    if os.path.exists(f3_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(f3_path, width=Inches(6.8))
        add_caption("Figure 3. Traxion AI full operational interface architecture: Top telemetry navigation bar, interactive 3D WebGL skeletal mannequin, 3-state traffic signal telemetry console (Green / Amber / Red), live HUD camera feed with 17-keypoint overlays, H.264 video analysis timeline with collision jump markers, and automated 108 Emergency Ambulance dispatch hub.")

    # SECTION 5
    add_heading1("5. MULTI-ZONE ANATOMICAL TRAUMA TRIAGE LOGIC")
    for p in mc.SEC_5_TRAUMA_TRIAGE:
        if "FSI =" in p:
            parts = p.split("\n")
            for part in parts:
                if "FSI =" in part:
                    p_f = doc.add_paragraph()
                    p_f.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_f.paragraph_format.first_line_indent = 0
                    r = p_f.add_run(part)
                    r.font.name = "Courier New"
                    r.font.size = Pt(9)
                    r.font.bold = True
                else:
                    add_p(part)
        else:
            add_p(p)

    # Figure 4: Trauma Flowchart
    f4_path = os.path.join("paper_assets", "fig4_trauma_logic_large.png")
    if os.path.exists(f4_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(f4_path, width=Inches(6.8))
        add_caption("Figure 4. Multi-zone anatomical trauma triage decision logic: Continuous ingestion of 17 keypoints into parallel cranial, spinal, lower-extremity, and upper-extremity clinical scoring filters, computing the composite Fall Severity Index (FSI) to drive deterministic 3-tier emergency escalations.")

    # SECTION 6
    add_heading1("6. HIGHWAY ACCIDENT EVALUATION BENCHMARK")
    for p in mc.SEC_6_EXPERIMENTS:
        add_p(p)

    add_caption("Table 3. Distribution and kinematic characteristics of the 1,240 evaluation video sequences across highway monitoring categories.")
    add_docx_table(mc.TABLE_3_HEADERS, mc.TABLE_3_DATA)

    # SECTION 7
    add_heading1("7. RESULTS AND QUANTITATIVE EVALUATION")
    for p in mc.SEC_7_RESULTS:
        if p.startswith("7."):
            add_heading2(p)
        else:
            add_p(p)

    add_caption("Table 4. Comparative performance evaluation of Traxion AI against baseline fall and accident detection architectures.")
    add_docx_table(mc.TABLE_4_HEADERS, mc.TABLE_4_DATA)

    # Figure 5: Benchmarks
    f5_path = os.path.join("paper_assets", "fig5_benchmarks_confusion_large.png")
    if os.path.exists(f5_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(f5_path, width=Inches(6.8))
        add_caption("Figure 5. Quantitative evaluation results: (A) Multi-class confusion matrix over 1,240 labeled highway sequences, demonstrating 99.4% recall on severe accidents, and (B) Baseline benchmark comparisons highlighting the superior balance of precision, recall, and CPU inference throughput achieved by Traxion AI.")

    # SECTION 8
    add_heading1("8. QUALITATIVE CASE STUDIES AND EDGE-CASE ROBUSTNESS")
    for p in mc.SEC_8_CASE_STUDIES:
        if p.startswith("8."):
            add_heading2(p)
        else:
            add_p(p)

    add_caption("Table 5. Detailed frame-by-frame kinematic vector trace across positive collisions and difficult negative control edge cases.")
    add_docx_table(mc.TABLE_5_HEADERS, mc.TABLE_5_DATA)

    # SECTION 9
    add_heading1("9. SYSTEMATIC ABLATION STUDY")
    for p in mc.SEC_9_ABLATION:
        add_p(p)

    add_caption("Table 6. Systematic ablation analysis demonstrating the empirical necessity of individual kinematic vector components.")
    add_docx_table(mc.TABLE_6_HEADERS, mc.TABLE_6_DATA)

    # SECTION 10
    add_heading1("10. OPERATIONAL DEPLOYMENT AND EMERGENCY GATEWAY")
    for p in mc.SEC_10_DEPLOYMENT:
        if p.startswith("10."):
            add_heading2(p)
        else:
            add_p(p)

    # SECTION 11
    add_heading1("11. LIMITATIONS, EDGE CONDITIONS, AND ETHICAL PRIVACY")
    for p in mc.SEC_11_ETHICAL_LIMITATIONS:
        if p.startswith("11."):
            add_heading2(p)
        else:
            add_p(p)

    # SECTION 12
    add_heading1("12. CONCLUSION AND FUTURE SCOPE")
    for p in mc.SEC_12_CONCLUSION:
        add_p(p)

    # ACKNOWLEDGEMENT
    add_heading1("ACKNOWLEDGMENT")
    add_p(mc.ACKNOWLEDGEMENT_TEXT)

    # REFERENCES
    add_heading1("REFERENCES")
    for ref in mc.REFERENCES_LIST:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.first_line_indent = Inches(-0.25)
        p_ref.paragraph_format.left_indent = Inches(0.25)
        p_ref.paragraph_format.space_before = Pt(0)
        p_ref.paragraph_format.space_after = Pt(3)
        r = p_ref.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(30, 41, 59)

    doc.save(docx_path)
    print("DOCX build finished.")


if __name__ == "__main__":
    pdf_out = "Traxion_AI_Research_Paper.pdf"
    docx_out = "Traxion_AI_Research_Paper.docx"
    
    build_pdf(pdf_out)
    build_docx(docx_out)

    # Check PDF page count
    reader = PdfReader(pdf_out)
    page_count = len(reader.pages)
    print(f"==================================================")
    print(f"FINAL GENERATED PDF PAGE COUNT: {page_count} PAGES")
    print(f"==================================================")
