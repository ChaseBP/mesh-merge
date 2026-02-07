import json
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types


# --- Resolve the project root and add to sys.path ---
file_path = Path(__file__).resolve()
project_root = file_path.parent.parent
sys.path.append(str(project_root))
# ----------------------------------------------
from config import GEMINI_API_KEY


# -----------------------------
# CONFIG
# -----------------------------
MODEL_NAME = "gemini-3-flash-preview"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# project paths
BASE_DIR = Path(__file__).resolve().parent.parent

ENRICHED_DIFF_PATH = BASE_DIR / "outputs" / "enriched_diff.json"
SCENE_V1_PATH = BASE_DIR / "inputs" / "v1" / "scene.json"
SCENE_V2_PATH = BASE_DIR / "inputs" / "v2" / "scene.json"

IMAGE_V1_PATH = BASE_DIR / "inputs" / "v1" / "viewport.png"
IMAGE_V2_PATH = BASE_DIR / "inputs" / "v2" / "viewport.png"

OUTPUT_PATH = BASE_DIR / "outputs" / "semantic_scene_report.json"


# -----------------------------
# SYSTEM PROMPT
# -----------------------------
SYSTEM_PROMPT = """
You are the semantic reasoning core of a 3D scene change interpretation system.

All changes have already been verified by deterministic analysis.
You must ONLY interpret the provided evidence.

Your responsibilities:
1. Group related changes into semantic events
2. Assign significance to events
3. Interpret spatial overlaps as conflicts
4. Produce a scene-level summary
5. Produce per-object summaries
6. Sort events by significance (highest first)

You must NOT:
- Infer artistic intent
- Suggest improvements
- Invent changes
- Override provided facts

Use cautious language.
State uncertainty explicitly.
Use professional 3D terminology.

Significance levels:
- minor
- structural
- scene-level
- critical

Return EXACTLY one JSON object.
No markdown.
No extra text.
"""


SCHEMA_DESCRIPTION = """
Return JSON in this exact structure:

{
  "scene_summary": {
    "description": "...",
    "dominant_change_type": "...",
    "overall_significance": "minor | structural | scene-level | critical",
    "confidence": "high | medium | low"
  },
  "events": [
    {
      "event_id": "event_001",
      "type": "...",
      "objects": [],
      "axes": [],
      "visual_confirmation": true,
      "spatial_scope": "localized | multi-object | scene-wide",
      "significance": "minor | structural | scene-level | critical",
      "interpretation": "...",
      "justification": "...",
      "confidence": "high | medium | low"
    }
  ],
  "conflicts": [],
  "object_summaries": [
    {
      "object": "...",
      "summary": "...",
      "significance": "minor | structural | scene-level | critical",
      "confidence": "high | medium | low"
    }
  ]
}
"""


# -----------------------------
# HELPERS
# -----------------------------
def load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def extract_json(text: str):
    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in Gemini response: {text[:100]}...")

    return json.loads(text[start:end])


def validate_schema(data: dict):
    required_keys = {"scene_summary", "events", "conflicts", "object_summaries"}
    if not required_keys.issubset(data.keys()):
        raise ValueError(f"Schema validation failed: missing top-level keys. Found: {list(data.keys())}")


# -----------------------------
# GEMINI CALL
# -----------------------------
def run_gemini_reasoning():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY missing")

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        enriched_diff = load_json(ENRICHED_DIFF_PATH)
        scene_v1 = load_json(SCENE_V1_PATH)
        scene_v2 = load_json(SCENE_V2_PATH)
    except FileNotFoundError as e:
        print(f"[Gemini] Error loading input files: {e}")
        return

    prompt = f"""
{SYSTEM_PROMPT}

{SCHEMA_DESCRIPTION}

VERIFIED DIFF DATA:
{json.dumps(enriched_diff, indent=2)}

SCENE V1:
{json.dumps(scene_v1, indent=2)}

SCENE V2:
{json.dumps(scene_v2, indent=2)}
"""

    for attempt in range(MAX_RETRIES):
        print(f"[Gemini] Attempt {attempt + 1}")

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=IMAGE_V1_PATH.read_bytes(), mime_type="image/png"),
                    types.Part.from_bytes(data=IMAGE_V2_PATH.read_bytes(), mime_type="image/png"),
                ],
            )

            if not response.text:
                raise ValueError("Empty response from Gemini")

            raw_text = response.text.strip()
            parsed = extract_json(raw_text)
            validate_schema(parsed)

            # Ensure output directory exists
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

            with open(OUTPUT_PATH, "w") as f:
                json.dump(parsed, f, indent=2)

            print(f"[Gemini] Semantic report generated successfully at {OUTPUT_PATH}")
            return

        except Exception as e:
            print(f"[Gemini] Error: {e}")
            if attempt < MAX_RETRIES - 1:
                print("[Gemini] Retrying...")
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError("Gemini failed after retries")


# -----------------------------
# ENTRY
# -----------------------------
if __name__ == "__main__":
    run_gemini_reasoning()
