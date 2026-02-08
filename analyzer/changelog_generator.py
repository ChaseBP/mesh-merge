import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEMANTIC_REPORT_PATH = BASE_DIR / "outputs" / "semantic_scene_report.json"
OUTPUT_MD_PATH = BASE_DIR / "outputs" / "CHANGELOG.md"


def load_report():
    if not SEMANTIC_REPORT_PATH.exists():
        raise FileNotFoundError(
            "semantic_scene_report.json not found. Run Gemini reasoning first."
        )

    with open(SEMANTIC_REPORT_PATH, "r") as f:
        return json.load(f)


def main():
    report = load_report()

    lines = ["# MeshMerge Change Log", ""]

    # ---------------------
    # Scene Summary
    # ---------------------
    summary = report.get("scene_summary", {})
    lines.append("## Scene Summary")

    if summary:
        lines.append(summary.get("description", "No description provided."))
        lines.append("")

        dominant = summary.get("dominant_change_type")
        if dominant:
            lines.append(f"**Dominant change type:** {dominant}")

        lines.append(
            f"**Overall significance:** {summary.get('overall_significance', 'unknown')}"
        )
        lines.append("")
    else:
        lines.append("No high-level scene summary available.\n")

    # ---------------------
    # Events
    # ---------------------
    events = report.get("events", [])
    lines.append("## Events")

    if not events:
        lines.append("No semantic events detected.\n")
    else:
        for event in events:
            sig = event.get("significance", "unknown").upper()
            interpretation = event.get("interpretation", "No description")
            objects = ", ".join(event.get("objects", []))

            lines.append(f"- **[{sig}]** {interpretation}")

            if objects:
                lines.append(f"  - Objects: {objects}")

            axes = event.get("axes")
            if axes:
                lines.append(f"  - Axes affected: {', '.join(axes)}")

            justification = event.get("justification")
            if justification:
                lines.append(f"  - Evidence: {justification}")

            lines.append("")

    # ---------------------
    # Resolved Ambiguities ⭐ HERO SECTION
    # ---------------------
    resolved = report.get("resolved_ambiguities", [])
    if resolved:
        lines.append("## Resolved Ambiguities")

        for r in resolved:
            typ = r.get("type", "unknown")
            obj = r.get("object")
            explanation = r.get("explanation", "")
            conf = r.get("confidence", "unknown")

            if obj:
                lines.append(f"- **{typ}** ({obj}) — {conf}")
            else:
                lines.append(f"- **{typ}** — {conf}")

            if explanation:
                lines.append(f"  - {explanation}")

            lines.append("")

    # ---------------------
    # Conflicts
    # ---------------------
    conflicts = report.get("conflicts", [])
    if conflicts:
        lines.append("## Conflicts")

        for conflict in conflicts:
            interpretation = conflict.get("interpretation", "Conflict detected")
            objects = ", ".join(conflict.get("objects", []))
            severity = conflict.get("severity", "unknown")

            lines.append(f"- {interpretation}")

            if objects:
                lines.append(f"  - Objects: {objects}")

            lines.append(f"  - Severity: {severity}")
            lines.append("")

    # ---------------------
    # Object Summaries
    # ---------------------
    obj_summaries = report.get("object_summaries", [])
    if obj_summaries:
        lines.append("## Object Summaries")

        for obj in obj_summaries:
            name = obj.get("object", "unknown")
            summary = obj.get("summary", "")
            sig = obj.get("significance", "unknown")

            lines.append(f"- **{name}** ({sig}): {summary}")

    # ---------------------
    # Write file
    # ---------------------
    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[MeshMerge] CHANGELOG.md generated from Gemini semantic report")
    print(f"Location: {OUTPUT_MD_PATH}")


if __name__ == "__main__":
    main()

