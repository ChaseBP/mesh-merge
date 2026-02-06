import json
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph

BASE_DIR = Path(__file__).resolve().parent.parent

VISUAL_DIR = BASE_DIR / "outputs" / "visual"
HEATMAP = BASE_DIR / "outputs" / "vision" / "diff_heatmap.png"
SEMANTIC = BASE_DIR / "outputs" / "semantic_scene_report.json"

IMG_BEFORE = VISUAL_DIR / "annotated_v1.png"
IMG_AFTER = VISUAL_DIR / "annotated_v2.png"

OUTPUT_PDF = BASE_DIR / "outputs" / "meshmerge_report.pdf"


# -----------------------------
# helpers
# -----------------------------


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def draw_image_scaled(c, path, x, y, max_width):
    img = ImageReader(str(path))
    iw, ih = img.getSize()
    aspect = ih / iw

    width = max_width
    height = width * aspect

    c.drawImage(img, x, y - height, width=width, height=height)
    return height


def draw_wrapped_text(c, text, x, y, max_width):
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "Helvetica"
    style.fontSize = 10
    style.leading = 14

    p = Paragraph(text, style)

    # height 80 gives room for wrapping
    frame = Frame(x, y - 80, max_width, 80, showBoundary=0)
    frame.addFromList([p], c)


# -----------------------------
# main
# -----------------------------


def main():
    if not SEMANTIC.exists():
        print("semantic report missing")
        return

    data = load_json(SEMANTIC)

    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A4)
    page_w, page_h = A4

    # -------------------------
    # Title
    # -------------------------
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, page_h - 40, "MeshMerge Visual Report")

    c.setFont("Helvetica", 10)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawString(40, page_h - 60, f"Generated: {now}")

    # -------------------------
    # Scene summary
    # -------------------------
    summary = data["scene_summary"]["description"]
    sig = data["scene_summary"]["overall_significance"]

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, page_h - 90, "Scene Summary")

    draw_wrapped_text(
        c,
        summary,
        40,
        page_h - 110,
        page_w - 80,
    )

    c.setFont("Helvetica", 10)
    c.drawString(40, page_h - 180, f"Overall significance: {sig}")

    # -------------------------
    # Images section
    # -------------------------
    y = page_h - 210

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Before / After")
    y -= 10

    img_width = (page_w - 80) / 2 - 10

    h1 = draw_image_scaled(c, IMG_BEFORE, 40, y, img_width)
    h2 = draw_image_scaled(c, IMG_AFTER, 60 + img_width, y, img_width)

    y -= max(h1, h2) + 20

    # -------------------------
    # Heatmap
    # -------------------------
    if HEATMAP.exists():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Change Heatmap")
        y -= 10
        draw_image_scaled(c, HEATMAP, 40, y, page_w - 80)
        y -= 180

    # -------------------------
    # Events
    # -------------------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Detected Events")
    y -= 20

    c.setFont("Helvetica", 10)

    for ev in data.get("events", []):
        line = f"{ev['type']} → {', '.join(ev['objects'])} ({ev['significance']})"
        c.drawString(40, y, line)
        y -= 14

    c.save()
    print(f"[MeshMerge] PDF report generated → {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
