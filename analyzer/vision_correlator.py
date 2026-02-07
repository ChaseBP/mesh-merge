import json
import sys
from pathlib import Path

from PIL import Image

# -------------------------
# CONFIG
# -------------------------

MIN_OVERLAP_RATIO = 0.15  # require 15% overlap


# -------------------------
# HELPERS
# -------------------------


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def get_image_size(image_path):
    with Image.open(image_path) as img:
        return img.size  # (width, height)


def rect_overlap(a, b):
    dx = min(a["max_x"], b["max_x"]) - max(a["min_x"], b["min_x"])
    dy = min(a["max_y"], b["max_y"]) - max(a["min_y"], b["min_y"])
    if dx <= 0 or dy <= 0:
        return 0
    return dx * dy


def rect_area(r):
    return (r["max_x"] - r["min_x"]) * (r["max_y"] - r["min_y"])


def approximate_projection(bounds, image_width, image_height):
    """
    Conservative projection heuristic:
    Maps world X/Z bounds to screen X/Y.
    Assumes centered camera.
    """

    world_width = bounds["max"][0] - bounds["min"][0]
    world_height = bounds["max"][2] - bounds["min"][2]

    center_x = image_width // 2
    center_y = image_height // 2

    scale = 40  # pixels per world unit (heuristic)

    half_w = int((world_width * scale) / 2)
    half_h = int((world_height * scale) / 2)

    return {
        "min_x": max(center_x - half_w, 0),
        "max_x": min(center_x + half_w, image_width),
        "min_y": max(center_y - half_h, 0),
        "max_y": min(center_y + half_h, image_height),
    }


# -------------------------
# MAIN
# -------------------------


def main(diff_path, scene_path, regions_path, image_path, out_path):
    diffs = load_json(diff_path)
    scene = load_json(scene_path)
    regions = load_json(regions_path)

    image_width, image_height = get_image_size(image_path)

    objects = {o["name"]: o for o in scene.get("objects", [])}

    enriched = []

    for d in diffs:
        obj_name = d.get("object")
        obj = objects.get(obj_name)

        visual_confirmed = False

        if obj and obj.get("bounds") and regions:
            obj_rect = approximate_projection(obj["bounds"], image_width, image_height)

            for region in regions:
                overlap = rect_overlap(obj_rect, region)
                if overlap > 0:
                    ratio = overlap / rect_area(obj_rect)
                    if ratio >= MIN_OVERLAP_RATIO:
                        visual_confirmed = True
                        break

        d["visual_confirmation"] = visual_confirmed
        enriched.append(d)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(enriched, f, indent=2)

    print(f"[MeshMerge] Vision correlation complete → {out_path}")


# -------------------------
# ENTRY
# -------------------------

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(
            "Usage: python vision_correlator.py "
            "diff.json scene_v2.json regions.json viewport.png output.json"
        )
        sys.exit(1)

    main(
        sys.argv[1],  # diff.json
        sys.argv[2],  # scene_v2.json
        sys.argv[3],  # regions.json
        sys.argv[4],  # viewport.png
        sys.argv[5],  # output.json
    )
