import json
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
    HRFlowable,
)

BASE_DIR = Path(__file__).resolve().parent.parent

VISUAL_DIR = BASE_DIR / "outputs" / "visual"
HEATMAP = BASE_DIR / "outputs" / "vision" / "diff_heatmap.png"
SEMANTIC = BASE_DIR / "outputs" / "semantic_scene_report.json"

IMG_BEFORE = VISUAL_DIR / "annotated_v1.png"
IMG_AFTER = VISUAL_DIR / "annotated_v2.png"

OUTPUT_PDF = BASE_DIR / "outputs" / "meshmerge_report.pdf"

PAGE_W, PAGE_H = A4
MARGIN = 40


# ──────────────────────────────────────
# Styles
# ──────────────────────────────────────
def build_styles():
    ss = getSampleStyleSheet()

    ss.add(ParagraphStyle(
        "Title_Custom",
        parent=ss["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        spaceAfter=4,
        alignment=TA_LEFT,
    ))
    ss.add(ParagraphStyle(
        "Subtitle",
        parent=ss["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=12,
    ))
    ss.add(ParagraphStyle(
        "Section",
        parent=ss["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=18,
        spaceAfter=8,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    ss.add(ParagraphStyle(
        "Body",
        parent=ss["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "BodyIndent",
        parent=ss["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        leftIndent=16,
        spaceAfter=6,
        textColor=colors.HexColor("#333333"),
    ))
    ss.add(ParagraphStyle(
        "Label",
        parent=ss["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        "Caption",
        parent=ss["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceBefore=4,
        spaceAfter=10,
    ))
    return ss


# ──────────────────────────────────────
# Helpers
# ──────────────────────────────────────
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def make_scaled_image(path, max_width, max_height=None):
    """Return a platypus Image flowable scaled to fit within bounds."""
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    aspect = ih / iw

    width = max_width
    height = width * aspect

    if max_height and height > max_height:
        height = max_height
        width = height / aspect

    return Image(str(path), width=width, height=height)


def section_hr():
    """A thin horizontal rule to visually separate sections."""
    return HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#cccccc"),
        spaceBefore=6, spaceAfter=10,
    )


# ──────────────────────────────────────
# Header / Footer
# ──────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()
    # footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        MARGIN, 20,
        f"MeshMerge Report  •  Page {doc.page}"
    )
    canvas.drawRightString(
        PAGE_W - MARGIN, 20,
        datetime.now().strftime("%Y-%m-%d"),
    )
    canvas.restoreState()


# ──────────────────────────────────────
# Build story (content)
# ──────────────────────────────────────
def build_story(data, styles):
    story = []
    usable_width = PAGE_W - 2 * MARGIN

    # ── Title ──
    story.append(Paragraph("MeshMerge Visual Report", styles["Title_Custom"]))
    now = datetime.now().strftime("%Y-%m-%d  %H:%M")
    story.append(Paragraph(f"Generated: {now}", styles["Subtitle"]))
    story.append(section_hr())

    # ── Scene Summary ──
    story.append(Paragraph("Scene Summary", styles["Section"]))

    summary = data["scene_summary"]["description"]
    story.append(Paragraph(summary, styles["Body"]))

    sig = data["scene_summary"]["overall_significance"]
    dominant = data["scene_summary"].get("dominant_change_type", "unknown")
    conf = data["scene_summary"].get("confidence", "unknown")

    meta_data = [
        ["Overall significance:", sig],
        ["Dominant change:", dominant],
        ["Confidence:", conf],
    ]
    meta_table = Table(meta_data, colWidths=[130, usable_width - 140])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    story.append(section_hr())

    # ── Before / After images ──
    story.append(Paragraph("Before / After", styles["Section"]))

    if IMG_BEFORE.exists() and IMG_AFTER.exists():
        img_max_w = (usable_width - 12) / 2
        max_img_h = 220  # prevent images from consuming more than ~1/3 page

        img_before = make_scaled_image(IMG_BEFORE, img_max_w, max_img_h)
        img_after = make_scaled_image(IMG_AFTER, img_max_w, max_img_h)

        img_table = Table(
            [[img_before, img_after]],
            colWidths=[img_max_w + 6, img_max_w + 6],
        )
        img_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(img_table)

        caption_table = Table(
            [[
                Paragraph("v1 (Before)", styles["Caption"]),
                Paragraph("v2 (After)", styles["Caption"]),
            ]],
            colWidths=[img_max_w + 6, img_max_w + 6],
        )
        story.append(caption_table)
    else:
        story.append(Paragraph("<i>Images not found.</i>", styles["Body"]))

    story.append(section_hr())

    # ── Heatmap ──
    if HEATMAP.exists():
        story.append(Paragraph("Change Heatmap", styles["Section"]))
        heatmap_img = make_scaled_image(HEATMAP, usable_width, max_height=280)
        story.append(heatmap_img)
        story.append(Paragraph("Pixel-level diff heatmap", styles["Caption"]))
        story.append(section_hr())

    # ── Resolved Ambiguities ──
    resolved = data.get("resolved_ambiguities", [])
    if resolved:
        story.append(Paragraph("Resolved Ambiguities", styles["Section"]))

        for i, r in enumerate(resolved, 1):
            typ = r.get("type", "unknown")
            obj = r.get("object", "")
            explanation = r.get("explanation", "")
            conf_r = r.get("confidence", "")

            label = f"<b>{i}. {typ}</b>"
            if obj:
                label += f"  →  <font color='#555555'>{obj}</font>"

            block = [
                Paragraph(label, styles["Body"]),
            ]
            if explanation:
                block.append(Paragraph(explanation, styles["BodyIndent"]))
            if conf_r:
                block.append(Paragraph(
                    f"<i>Confidence: {conf_r}</i>", styles["BodyIndent"]
                ))
            block.append(Spacer(1, 6))

            # KeepTogether prevents splitting a single ambiguity across pages
            story.append(KeepTogether(block))

        story.append(section_hr())

    # ── Detected Events ──
    events = data.get("events", [])
    if events:
        story.append(Paragraph("Detected Events", styles["Section"]))

        for i, ev in enumerate(events, 1):
            objects = ", ".join(ev.get("objects", [])) or "scene-wide"
            ev_type = ev.get("type", "unknown")
            ev_sig = ev.get("significance", "")
            interp = ev.get("interpretation", "")
            just = ev.get("justification", "")

            block = [
                Paragraph(
                    f"<b>{i}. {ev_type}</b>  →  {objects}"
                    f"  <font color='#888888'>({ev_sig})</font>",
                    styles["Body"],
                ),
            ]
            if interp:
                block.append(Paragraph(interp, styles["BodyIndent"]))
            if just:
                block.append(Paragraph(
                    f"<i>{just}</i>", styles["BodyIndent"]
                ))
            block.append(Spacer(1, 6))

            story.append(KeepTogether(block))

        story.append(section_hr())

    # ── Object Summaries ──
    obj_summaries = data.get("object_summaries", [])
    if obj_summaries:
        story.append(Paragraph("Object Summaries", styles["Section"]))

        header_style = ParagraphStyle(
            "TableHeader", parent=styles["Body"],
            fontName="Helvetica-Bold", fontSize=10, textColor=colors.white,
        )
        cell_style = ParagraphStyle(
            "TableCell", parent=styles["Body"],
            fontName="Helvetica", fontSize=9, leading=13, spaceAfter=0,
        )
        table_data = [[
            Paragraph("Object", header_style),
            Paragraph("Summary", header_style),
            Paragraph("Significance", header_style),
        ]]
        for o in obj_summaries:
            table_data.append([
                Paragraph(o.get("object", ""), cell_style),
                Paragraph(o.get("summary", ""), cell_style),
                Paragraph(o.get("significance", ""), cell_style),
            ])

        obj_table = Table(
            table_data,
            colWidths=[80, usable_width - 180, 90],
            repeatRows=1,
        )
        obj_table.setStyle(TableStyle([
            # header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            # body rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(obj_table)
        story.append(Spacer(1, 10))

    # ── Conflicts ──
    conflicts = data.get("conflicts", [])
    if conflicts:
        story.append(Paragraph("Conflicts", styles["Section"]))
        for c_item in conflicts:
            story.append(Paragraph(
                f"• {json.dumps(c_item)}", styles["Body"]
            ))
        story.append(section_hr())

    return story


# ──────────────────────────────────────
# main
# ──────────────────────────────────────
def main():
    if not SEMANTIC.exists():
        print("semantic report missing")
        return

    data = load_json(SEMANTIC)
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    story = build_story(data, styles)
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    print(f"[MeshMerge] PDF report generated → {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
