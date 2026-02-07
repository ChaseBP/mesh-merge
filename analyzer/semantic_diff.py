import json
import sys
from math import isclose

EPSILON = 1e-5


def load_scene(path):
    with open(path, "r") as f:
        return json.load(f)


def index_objects(scene):
    return {obj["name"]: obj for obj in scene.get("objects", [])}


def extent(bounds):
    return {
        "x": bounds["max"][0] - bounds["min"][0],
        "y": bounds["max"][1] - bounds["min"][1],
        "z": bounds["max"][2] - bounds["min"][2],
    }


def diff_bounds(obj1, obj2):
    if not obj1.get("bounds") or not obj2.get("bounds"):
        return []

    diffs = []
    e1 = extent(obj1["bounds"])
    e2 = extent(obj2["bounds"])

    for axis in ("x", "y", "z"):
        if not isclose(e1[axis], e2[axis], rel_tol=1e-4):
            diffs.append(
                {
                    "object": obj1["name"],
                    "type": "BOUNDS_CHANGED",
                    "details": {
                        "axis": axis.upper(),
                        "before_extent": round(e1[axis], 4),
                        "after_extent": round(e2[axis], 4),
                    },
                }
            )
    return diffs


def diff_transforms(obj1, obj2):
    diffs = []
    for key in ("location", "rotation_euler", "scale"):
        v1 = obj1["transform"][key]
        v2 = obj2["transform"][key]
        if any(not isclose(a, b, rel_tol=1e-5) for a, b in zip(v1, v2)):
            diffs.append(
                {
                    "object": obj1["name"],
                    "type": "TRANSFORM_CHANGED",
                    "details": {"transform": key, "before": v1, "after": v2},
                }
            )
    return diffs


def diff_mesh_stats(obj1, obj2):
    diffs = []
    for stat in ("vertex_count", "face_count"):
        if obj1["mesh_stats"][stat] != obj2["mesh_stats"][stat]:
            diffs.append(
                {
                    "object": obj1["name"],
                    "type": "MESH_STATS_CHANGED",
                    "details": {
                        "stat": stat,
                        "before": obj1["mesh_stats"][stat],
                        "after": obj2["mesh_stats"][stat],
                    },
                }
            )
    return diffs


def diff_material(obj1, obj2):
    if obj1.get("material_assignment") != obj2.get("material_assignment"):
        return [
            {
                "object": obj1["name"],
                "type": "MATERIAL_CHANGED",
                "details": {
                    "before": obj1.get("material_assignment"),
                    "after": obj2.get("material_assignment"),
                },
            }
        ]
    return []


def main(v1_path, v2_path):
    v1 = load_scene(v1_path)
    v2 = load_scene(v2_path)

    objs1 = index_objects(v1)
    objs2 = index_objects(v2)

    diffs = []

    # Added / removed objects
    for name in objs1.keys() - objs2.keys():
        diffs.append({"object": name, "type": "OBJECT_REMOVED"})

    for name in objs2.keys() - objs1.keys():
        diffs.append({"object": name, "type": "OBJECT_ADDED"})

    # Modified objects
    for name in objs1.keys() & objs2.keys():
        o1 = objs1[name]
        o2 = objs2[name]

        diffs.extend(diff_transforms(o1, o2))
        diffs.extend(diff_bounds(o1, o2))
        diffs.extend(diff_mesh_stats(o1, o2))
        diffs.extend(diff_material(o1, o2))

    print(json.dumps(diffs, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 semantic_diff.py scene_v1.json scene_v2.json")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])

