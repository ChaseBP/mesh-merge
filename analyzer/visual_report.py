import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent

IMG_V1 = BASE_DIR / "inputs" / "v1" / "viewport.png"
IMG_V2 = BASE_DIR / "inputs" / "v2" / "viewport.png"
REGIONS = BASE_DIR / "outputs" / "vision" / "regions.json"
SEMANTIC = BASE_DIR / "outputs" / "semantic_scene_report.json"

VISUAL_DIR = BASE_DIR / "outputs" / "visual"
VISUAL_DIR.mkdir(parents=True, exist_ok=True)

OUT_V1 = VISUAL_DIR / "annotated_v1.png"
OUT_V2 = VISUAL_DIR / "annotated_v2.png"
OUT_COMPARE = VISUAL_DIR / "comparison.png"


# -------------------------
# helpers
# -------------------------


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_label():
    data = load_json(SEMANTIC)
    sig = data["scene_summary"]["overall_significance"].upper()

    if data["events"]:
        obj = data["events"][0]["objects"][0]
        return f"{obj} ({sig})"

    return f"Change detected ({sig})"


def merge_regions(regions):
    if not regions:
        return None

    min_x = min(r["min_x"] for r in regions)
    min_y = min(r["min_y"] for r in regions)
    max_x = max(r["max_x"] for r in regions)
    max_y = max(r["max_y"] for r in regions)

    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
    }


def draw_overlay(image_path, merged_region, label):
    img = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        font = ImageFont.load_default()

    if merged_region:
        box = [
            (merged_region["min_x"], merged_region["min_y"]),
            (merged_region["max_x"], merged_region["max_y"]),
        ]

        # translucent fill
        draw.rectangle(box, fill=(255, 0, 0, 20))

        # border
        draw.rectangle(box, outline=(255, 0, 0, 255), width=4)

    # label box
    draw.rectangle([(10, 10), (420, 50)], fill=(0, 0, 0, 200))
    draw.text((15, 15), label, fill="white", font=font)

    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")


def make_comparison(img1, img2):
    w = img1.width + img2.width
    h = max(img1.height, img2.height)

    canvas = Image.new("RGB", (w, h), "black")
    canvas.paste(img1, (0, 0))
    canvas.paste(img2, (img1.width, 0))
    return canvas


# -------------------------
# main
# -------------------------


def main():
    if not REGIONS.exists():
        print("regions.json missing")
        return

    regions = load_json(REGIONS)
    merged = merge_regions(regions)
    label = get_label()

    img1 = draw_overlay(IMG_V1, merged, label)
    img2 = draw_overlay(IMG_V2, merged, label)

    img1.save(OUT_V1)
    img2.save(OUT_V2)

    comparison = make_comparison(img1, img2)
    comparison.save(OUT_COMPARE)

    print(f"[MeshMerge] Clean visual report → {VISUAL_DIR}")


if __name__ == "__main__":
    main()
