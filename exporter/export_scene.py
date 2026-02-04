import json
import os

import bpy
from mathutils import Vector

# -------------------------
# CONFIG (safe to tweak)
# -------------------------

OUTPUT_DIR = bpy.path.abspath("//meshmerge_export")
SCENE_JSON_PATH = os.path.join(OUTPUT_DIR, "scene.json")
RENDER_PATH = os.path.join(OUTPUT_DIR, "viewport.png")

RENDER_RES_X = 1920
RENDER_RES_Y = 1080

# -------------------------
# HELPERS
# -------------------------


def ensure_output_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def compute_world_bounds(obj):
    """Compute world-space AABB for a mesh object."""
    if obj.type != "MESH" or not obj.data:
        return None

    mesh = obj.data
    world_matrix = obj.matrix_world

    coords = [world_matrix @ v.co for v in mesh.vertices]
    if not coords:
        return None

    min_v = Vector(
        (
            min(v.x for v in coords),
            min(v.y for v in coords),
            min(v.z for v in coords),
        )
    )
    max_v = Vector(
        (
            max(v.x for v in coords),
            max(v.y for v in coords),
            max(v.z for v in coords),
        )
    )

    return {
        "min": [min_v.x, min_v.y, min_v.z],
        "max": [max_v.x, max_v.y, max_v.z],
    }


def get_material_name(obj):
    if not obj.material_slots:
        return None
    slot = obj.material_slots[0]
    return slot.material.name if slot.material else None


# -------------------------
# EXPORT SCENE JSON
# -------------------------


def export_scene_json():
    scene = bpy.context.scene

    data = {"scene": scene.name, "objects": [], "lights": [], "cameras": []}

    for obj in scene.objects:
        if obj.type == "MESH":
            bounds = compute_world_bounds(obj)

            mesh_data = obj.data
            data["objects"].append(
                {
                    "name": obj.name,
                    "type": "MESH",
                    "transform": {
                        "location": list(obj.location),
                        "rotation_euler": list(obj.rotation_euler),
                        "scale": list(obj.scale),
                    },
                    "bounds": bounds,
                    "mesh_stats": {
                        "vertex_count": len(mesh_data.vertices),
                        "face_count": len(mesh_data.polygons),
                    },
                    "material_assignment": get_material_name(obj),
                }
            )

        elif obj.type == "LIGHT":
            light = obj.data
            data["lights"].append(
                {
                    "name": obj.name,
                    "type": light.type,
                    "intensity": light.energy,
                    "color": list(light.color),
                    "location": list(obj.location),
                }
            )

        elif obj.type == "CAMERA":
            data["cameras"].append(
                {
                    "name": obj.name,
                    "location": list(obj.location),
                    "rotation_euler": list(obj.rotation_euler),
                }
            )

    with open(SCENE_JSON_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[MeshMerge] scene.json written to {SCENE_JSON_PATH}")


# -------------------------
# RENDER VIEWPORT
# -------------------------


def render_viewport():
    scene = bpy.context.scene

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = RENDER_RES_X
    scene.render.resolution_y = RENDER_RES_Y
    scene.render.filepath = RENDER_PATH
    scene.render.image_settings.file_format = "PNG"

    # Ensure there is an active camera
    if scene.camera is None:
        print("[MeshMerge] No active camera found. Render skipped.")
        return

    bpy.ops.render.render(write_still=True)
    print(f"[MeshMerge] viewport.png written to {RENDER_PATH}")


# -------------------------
# MAIN
# -------------------------


def main():
    ensure_output_dir(OUTPUT_DIR)
    export_scene_json()
    render_viewport()
    print("[MeshMerge] Export complete.")


if __name__ == "__main__":
    main()
