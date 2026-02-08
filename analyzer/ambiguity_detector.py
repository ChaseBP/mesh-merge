import json
from pathlib import Path
from math import isclose, sqrt

BASE_DIR = Path(__file__).resolve().parent.parent

SCENE_V1 = BASE_DIR / "inputs" / "v1" / "scene.json"
SCENE_V2 = BASE_DIR / "inputs" / "v2" / "scene.json"

ENRICHED = BASE_DIR / "outputs" / "enriched_diff.json"
REGIONS = BASE_DIR / "outputs" / "vision" / "regions.json"

OUT_PATH = BASE_DIR / "outputs" / "ambiguities.json"

VISUAL_CHANGE_AREA_THRESHOLD = 200  # pixels


# -------------------------
# helpers
# -------------------------
def load_json(p):
    with open(p, "r") as f:
        return json.load(f)


def get_camera(scene):
    cams = scene.get("cameras", [])
    return cams[0] if cams else None


def camera_distance(cam):
    if not cam:
        return None
    x, y, z = cam.get("location", [0, 0, 0])
    return sqrt(x * x + y * y + z * z)


def camera_moved(cam1, cam2):
    if not cam1 or not cam2:
        return False

    loc1 = cam1.get("location", [0, 0, 0])
    loc2 = cam2.get("location", [0, 0, 0])

    return any(not isclose(a, b, rel_tol=1e-5) for a, b in zip(loc1, loc2))


def fov_changed(cam1, cam2):
    if not cam1 or not cam2:
        return False

    f1 = cam1.get("fov")
    f2 = cam2.get("fov")

    if f1 is None or f2 is None:
        return False

    return not isclose(f1, f2, rel_tol=1e-5)


def lighting_changed(scene1, scene2):
    l1 = scene1.get("lights", [])
    l2 = scene2.get("lights", [])

    if len(l1) != len(l2):
        return True

    for a, b in zip(l1, l2):
        if a.get("intensity") != b.get("intensity"):
            return True
        if a.get("color") != b.get("color"):
            return True

    return False


# -------------------------
# main
# -------------------------
def main():
    if not ENRICHED.exists():
        print("[Ambiguity] No enriched diff found. Skipping.")
        return

    scene1 = load_json(SCENE_V1)
    scene2 = load_json(SCENE_V2)
    diffs = load_json(ENRICHED)
    regions = load_json(REGIONS) if REGIONS.exists() else []

    cam1 = get_camera(scene1)
    cam2 = get_camera(scene2)

    ambiguities = []

    cam_changed = camera_moved(cam1, cam2)
    fov_change = fov_changed(cam1, cam2)
    light_change = lighting_changed(scene1, scene2)

    total_area = sum(r.get("area", 0) for r in regions)

    # -------------------------------------------------
    # CAMERA DISTANCE METRICS 
    # -------------------------------------------------
    dist1 = camera_distance(cam1)
    dist2 = camera_distance(cam2)

    distance_delta = None
    distance_pct = None

    if dist1 is not None and dist2 is not None:
        distance_delta = round(dist2 - dist1, 4)
        if dist1 > 0:
            distance_pct = round(((dist2 - dist1) / dist1) * 100, 2)

    # -------------------------------------------------
    # SCALE CHANGES TRACKING 
    # -------------------------------------------------
    scale_changes = [
        d for d in diffs
        if d.get("type") == "TRANSFORM_CHANGED"
        and d.get("details", {}).get("transform") == "scale"
    ]

    # -------------------------------------------------
    # per-diff ambiguity detection
    # -------------------------------------------------
    for d in diffs:
        obj = d.get("object")
        dtype = d.get("type")

        # -------------------------------------------------
        # CAMERA vs GEOMETRY
        # -------------------------------------------------
        if d.get("visual_confirmation") and dtype in ["BOUNDS_CHANGED", "TRANSFORM_CHANGED"]:
            if cam_changed or fov_change:
                ambiguities.append(
                    {
                        "type": "CAMERA_VS_GEOMETRY",
                        "object": obj,
                        "reason": "Object appearance changed while camera parameters also changed",
                        "possible_causes": [
                            "camera_moved",
                            "camera_fov_changed",
                            "object_scaled",
                            "object_moved",
                        ],
                        "confidence": "medium",
                    }
                )

        # -------------------------------------------------
        # LIGHTING vs MATERIAL
        # -------------------------------------------------
        if dtype == "MATERIAL_CHANGED" and light_change:
            ambiguities.append(
                {
                    "type": "LIGHTING_VS_MATERIAL",
                    "object": obj,
                    "reason": "Material appearance changed but lighting also changed",
                    "possible_causes": [
                        "material_update",
                        "light_intensity_change",
                        "light_color_change",
                    ],
                    "confidence": "medium",
                }
            )

        # -------------------------------------------------
        # CASCADING TRANSFORM
        # -------------------------------------------------
        if dtype == "TRANSFORM_CHANGED":
            transform_type = d.get("details", {}).get("transform")

            if transform_type == "location":
                ambiguities.append(
                    {
                        "type": "CASCADE_TRANSFORM",
                        "object": obj,
                        "reason": "Object moved but may be affected by parent transform or constraint",
                        "possible_causes": [
                            "direct_move",
                            "parent_moved",
                            "constraint_effect",
                        ],
                        "confidence": "low",
                    }
                )

        # -------------------------------------------------
        # APPARENT SCALE CHANGE
        # -------------------------------------------------
        if d.get("visual_confirmation") and dtype != "TRANSFORM_CHANGED":
            if cam_changed and total_area > VISUAL_CHANGE_AREA_THRESHOLD:
                ambiguities.append(
                    {
                        "type": "APPARENT_SCALE_CHANGE",
                        "object": obj,
                        "reason": "Object appears different in viewport but no scale transform detected",
                        "possible_causes": [
                            "camera_moved_closer",
                            "perspective_shift",
                            "mesh_rescaled",
                        ],
                        "confidence": "low",
                    }
                )

    # -------------------------------
    # SCALE vs CAMERA CONTRADICTION 
    # -------------------------------
    if scale_changes and cam_changed:
        ambiguities.append(
            {
                "type": "SCALE_CAMERA_CONTRADICTION",
                "objects": [d["object"] for d in scale_changes],
                "camera_distance_before": dist1,
                "camera_distance_after": dist2,
                "camera_distance_delta": distance_delta,
                "camera_distance_change_pct": distance_pct,
                "reason": "Object scale changed while camera distance also changed",
                "possible_causes": [
                    "object_scaled",
                    "camera_moved",
                    "perceptual_cancellation",
                ],
                "confidence": "high",
            }
        )

    # -------------------------------
    # PERCEPTUAL ONLY CHANGE
    # -------------------------------
    if not diffs and total_area > VISUAL_CHANGE_AREA_THRESHOLD:
        ambiguities.append(
            {
                "type": "PERCEPTUAL_CHANGE_ONLY",
                "object": None,
                "reason": "Viewport changed but no semantic diff detected",
                "possible_causes": [
                    "camera_move",
                    "lighting_change",
                    "render_setting_change",
                ],
                "confidence": "low",
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w") as f:
        json.dump(ambiguities, f, indent=2)

    print(f"[MeshMerge] Ambiguities written → {OUT_PATH}")


if __name__ == "__main__":
    main()

