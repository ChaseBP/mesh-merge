import json
import sys
from collections import defaultdict


def load_diffs(path):
    with open(path, "r") as f:
        return json.load(f)


def main(enriched_diff_path, output_path):
    diffs = load_diffs(enriched_diff_path)

    grouped = defaultdict(list)
    for d in diffs:
        grouped[d["object"]].append(d)

    lines = [
        "# MeshMerge Change Log",
        "",
        "## Summary",
        f"{len(diffs)} semantic change(s) detected between scene versions.",
        "",
        "## Details",
    ]

    for obj, changes in grouped.items():
        bounds_changes = [c for c in changes if c["type"] == "BOUNDS_CHANGED"]

        if bounds_changes:
            axes = sorted({c["details"]["axis"] for c in bounds_changes})
            visually_confirmed = all(
                c.get("visual_confirmation") for c in bounds_changes
            )

            if visually_confirmed:
                axis_str = " and ".join(axes)
                lines.append(
                    f"- The silhouette of `{obj}` expanded along the {axis_str} axis, "
                    f"with visible shape changes in the rendered view."
                )
            else:
                for c in bounds_changes:
                    axis = c["details"]["axis"]
                    before = c["details"]["before_extent"]
                    after = c["details"]["after_extent"]
                    direction = "increased" if after > before else "decreased"

                    lines.append(
                        f"- The spatial extent of `{obj}` {direction} along the {
                            axis
                        } axis "
                        f"(from {before:.2f} to {after:.2f})."
                    )

        # Other change types (future-safe)
        for c in changes:
            if c["type"] == "MATERIAL_CHANGED":
                lines.append(f"- The material assignment of `{obj}` changed.")
            if c["type"] == "TRANSFORM_CHANGED":
                lines.append(f"- The object transform of `{obj}` was modified.")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"[MeshMerge] Vision-aware CHANGELOG.md written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python changelog_generator.py enriched_diff.json CHANGELOG.md")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
