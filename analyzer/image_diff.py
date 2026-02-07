import json
import os
import sys

import numpy as np
from PIL import Image

# -------------------------
# CONFIG
# -------------------------

THRESHOLD = 25  # pixel intensity difference
MIN_REGION_AREA = 500  # ignore tiny noise blobs

# -------------------------
# HELPERS
# -------------------------


def load_image(path):
    return Image.open(path).convert("RGB")


def compute_diff(img1, img2):
    a = np.asarray(img1).astype(np.int16)
    b = np.asarray(img2).astype(np.int16)
    diff = np.abs(a - b)
    return diff.mean(axis=2)  # grayscale diff


def threshold_diff(diff):
    return diff > THRESHOLD


def find_regions(mask):
    visited = np.zeros(mask.shape, dtype=bool)
    regions = []

    h, w = mask.shape

    def flood_fill(x, y):
        stack = [(x, y)]
        xs, ys = [], []

        while stack:
            cx, cy = stack.pop()
            if cx < 0 or cy < 0 or cx >= w or cy >= h:
                continue
            if visited[cy, cx] or not mask[cy, cx]:
                continue

            visited[cy, cx] = True
            xs.append(cx)
            ys.append(cy)

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    stack.append((cx + dx, cy + dy))

        if len(xs) * len(ys) < MIN_REGION_AREA:
            return None

        return {
            "min_x": min(xs),
            "min_y": min(ys),
            "max_x": max(xs),
            "max_y": max(ys),
            "area": len(xs),
        }

    for y in range(h):
        for x in range(w):
            if mask[y, x] and not visited[y, x]:
                region = flood_fill(x, y)
                if region:
                    regions.append(region)

    return regions


def save_heatmap(diff, out_path):
    norm = np.clip(diff * 4, 0, 255).astype(np.uint8)
    heat = Image.fromarray(norm, mode="L")
    heat = heat.convert("RGB")
    heat.save(out_path)


# -------------------------
# MAIN
# -------------------------


def main(img1_path, img2_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    img1 = load_image(img1_path)
    img2 = load_image(img2_path)

    if img1.size != img2.size:
        raise ValueError("Images must be the same resolution")

    diff = compute_diff(img1, img2)
    mask = threshold_diff(diff)

    regions = find_regions(mask)

    save_heatmap(diff, os.path.join(out_dir, "diff_heatmap.png"))

    with open(os.path.join(out_dir, "regions.json"), "w") as f:
        json.dump(regions, f, indent=2)

    print(f"[MeshMerge] Found {len(regions)} changed region(s)")
    print(f"[MeshMerge] diff_heatmap.png + regions.json written to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python image_diff.py v1.png v2.png output_dir")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2], sys.argv[3])
