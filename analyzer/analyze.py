import subprocess
import sys
from pathlib import Path

# ---------------------------------------
# PATH SETUP
# ---------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_V1 = BASE_DIR / "inputs" / "v1"
INPUT_V2 = BASE_DIR / "inputs" / "v2"

OUTPUT_DIR = BASE_DIR / "outputs"
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

    with open(output_path, "w") as f:
        f.write(result.stdout)

    print(f"[OK] wrote {output_path}")


def assert_exists(path):
    if not path.exists():
        print(f"[ERROR] Missing expected file: {path}")
        sys.exit(1)


# ---------------------------------------
# MAIN PIPELINE
# ---------------------------------------


def main():
    print("\nMeshMerge pipeline starting...\n")

    # -----------------------------------
    # Check required inputs exist
    # -----------------------------------
    for p in [SCENE_V1, SCENE_V2, IMG_V1, IMG_V2]:
        if not p.exists():
            print(f"[ERROR] Missing required input: {p}")
            sys.exit(1)

    # -----------------------------------
    # Step 1 — semantic diff
    # -----------------------------------
    run_and_capture(
        "Semantic Diff",
        [
            sys.executable,
            "analyzer/semantic_diff.py",
            str(SCENE_V1),
            str(SCENE_V2),
        ],
        DIFF_JSON,
    )

    assert_exists(DIFF_JSON)

    # -----------------------------------
    # Step 2 — image diff
    # -----------------------------------
    run_step(
        "Image Diff",
        [
            sys.executable,
            "analyzer/image_diff.py",
            str(IMG_V1),
            str(IMG_V2),
            str(VISION_DIR),
        ],
    )

    assert_exists(REGIONS_JSON)

    # -----------------------------------
    # Step 3 — vision correlation
    # (image size auto-detected inside script)
    # -----------------------------------
    run_step(
        "Vision Correlation",
        [
            sys.executable,
            "analyzer/vision_correlator.py",
            str(DIFF_JSON),
            str(SCENE_V2),
            str(REGIONS_JSON),
            str(IMG_V2),
            str(ENRICHED_JSON),
        ],
    )

    assert_exists(ENRICHED_JSON)

    # -----------------------------------
    # Step 4 — Gemini reasoning
    # -----------------------------------
    run_step(
        "Gemini Reasoning",
        [sys.executable, "analyzer/gemini_reasoning.py"],
    )

    assert_exists(SEMANTIC_REPORT)

    # -----------------------------------
    # Step 5 — changelog generation
    # (Gemini-driven)
    # -----------------------------------
    run_step(
        "Changelog Generation",
        [sys.executable, "analyzer/changelog_generator.py"],
    )

    assert_exists(CHANGELOG_MD)

    print("\nPipeline complete.")
    print("Outputs available in /outputs\n")


# ---------------------------------------
# ENTRY
# ---------------------------------------

if __name__ == "__main__":
    main()
