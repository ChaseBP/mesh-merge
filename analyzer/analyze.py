import subprocess
import sys
from pathlib import Path

# ---------------------------------------
# PATH SETUP
# ---------------------------------------

BASE_DIR = Path(__file__).resolve().parent        # /mesh-merge/analyzer
PROJECT_ROOT = BASE_DIR.parent                    # /mesh-merge

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"

EXPORT_SCRIPT = PROJECT_ROOT / "exporter" / "export_scene.py"

INPUT_V1 = PROJECT_ROOT / "inputs" / "v1"
INPUT_V2 = PROJECT_ROOT / "inputs" / "v2"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
VISION_DIR = OUTPUT_DIR / "vision"

SCENE_V1 = INPUT_V1 / "scene.json"
SCENE_V2 = INPUT_V2 / "scene.json"

IMG_V1 = INPUT_V1 / "viewport.png"
IMG_V2 = INPUT_V2 / "viewport.png"

DIFF_JSON = OUTPUT_DIR / "diff.json"
REGIONS_JSON = VISION_DIR / "regions.json"
ENRICHED_JSON = OUTPUT_DIR / "enriched_diff.json"
SEMANTIC_REPORT = OUTPUT_DIR / "semantic_scene_report.json"
CHANGELOG_MD = OUTPUT_DIR / "CHANGELOG.md"


# ---------------------------------------
# HELPERS
# ---------------------------------------

def run_step(name, cmd):
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"[ERROR] {name} failed")
        sys.exit(1)


def run_and_capture(name, cmd, output_path):
    print(f"\n=== {name} ===")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.stdout)

    print(f"[OK] wrote {output_path}")


def assert_exists(path):
    if not path.exists():
        print(f"[ERROR] Missing expected file: {path}")
        sys.exit(1)


# ---------------------------------------
# BLENDER EXPORT
# ---------------------------------------

def export_blend(blend_path: Path, target_dir: Path):
    print(f"\n=== Exporting {blend_path.name} → {target_dir} ===")

    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        BLENDER_EXE,
        "--background",
        str(blend_path),
        "--python",
        str(EXPORT_SCRIPT),
        "--",
        "--out",
        str(target_dir),
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("[ERROR] Blender export failed")
        sys.exit(1)


# ---------------------------------------
# PIPELINE
# ---------------------------------------

def run_pipeline():
    print("\nMeshMerge pipeline starting...\n")

    OUTPUT_DIR.mkdir(exist_ok=True)
    VISION_DIR.mkdir(exist_ok=True)

    # -------------------------
    # Semantic diff
    # -------------------------
    run_and_capture(
        "Semantic Diff",
        [
            sys.executable,
            str(BASE_DIR / "semantic_diff.py"),
            str(SCENE_V1),
            str(SCENE_V2),
        ],
        DIFF_JSON,
    )

    assert_exists(DIFF_JSON)

    # -------------------------
    # Image diff
    # -------------------------
    run_step(
        "Image Diff",
        [
            sys.executable,
            str(BASE_DIR / "image_diff.py"),
            str(IMG_V1),
            str(IMG_V2),
            str(VISION_DIR),
        ],
    )

    assert_exists(REGIONS_JSON)

    # -------------------------
    # Vision correlation
    # -------------------------
    run_step(
        "Vision Correlation",
        [
            sys.executable,
            str(BASE_DIR / "vision_correlator.py"),
            str(DIFF_JSON),
            str(SCENE_V2),
            str(REGIONS_JSON),
            str(IMG_V2),
            str(ENRICHED_JSON),
        ],
    )

    assert_exists(ENRICHED_JSON)

    # -------------------------
    # Gemini reasoning
    # -------------------------
    run_step(
        "Gemini Reasoning",
        [sys.executable, str(BASE_DIR / "gemini_reasoning.py")],
    )

    assert_exists(SEMANTIC_REPORT)

    # -------------------------
    # Changelog
    # -------------------------
    run_step(
        "Changelog Generation",
        [sys.executable, str(BASE_DIR / "changelog_generator.py")],
    )

    assert_exists(CHANGELOG_MD)

    # -------------------------
    # Visual report (required for PDF)
    # -------------------------
    run_step(
        "Visual Report",
        [sys.executable, str(BASE_DIR / "visual_report.py")],
    )

    # -------------------------
    # PDF (optional)
    # -------------------------
    pdf_script = BASE_DIR / "pdf_report.py"
    if pdf_script.exists():
        run_step(
            "PDF Report",
            [sys.executable, str(pdf_script)],
        )

    print("\nPipeline complete.")
    print("Outputs available in /outputs\n")


# ---------------------------------------
# ENTRY
# ---------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("\nUsage:")
        print("python analyzer/analyze.py before.blend after.blend\n")
        sys.exit(1)

    before_blend = Path(sys.argv[1]).resolve()
    after_blend = Path(sys.argv[2]).resolve()

    if not before_blend.exists():
        print("Missing:", before_blend)
        sys.exit(1)

    if not after_blend.exists():
        print("Missing:", after_blend)
        sys.exit(1)

    export_blend(before_blend, INPUT_V1)
    export_blend(after_blend, INPUT_V2)

    run_pipeline()