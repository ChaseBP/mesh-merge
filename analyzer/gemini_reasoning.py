import json
import math
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

AMBIG_PATH = BASE_DIR / "outputs" / "ambiguities.json"

OUTPUT_PATH = BASE_DIR / "outputs" / "semantic_scene_report.json"


# -----------------------------
# SYSTEM PROMPT
# -----------------------------

SYSTEM_PROMPT = """
You are the causal reasoning engine of a 3D scene change analysis system.

Deterministic modules have already produced:
- verified structural diffs
- visual change regions
- ambiguity hypotheses

Your job is to resolve *why* the scene appears different.

You must:
1. Determine causal events behind visual changes
2. Resolve ambiguities using scene data
3. Distinguish camera changes vs geometry changes
4. Distinguish lighting vs material changes
5. Detect perceptual-only changes
6. Produce a coherent scene narrative

Important reasoning rules:

CAMERA REASONING
- If camera moved and objects appear larger → likely perceptual change
- If camera FOV changed → apparent scale change possible
- If no object transforms but viewport changed → camera or lighting

DEPTH REASONING
- Compare object bounds + camera distance
- Apparent size change without scale change → perceptual
- Multiple objects changing uniformly → camera movement

LIGHTING REASONING
- If material changed AND light changed → ambiguous
- If only lighting changed → scene-level perceptual shift

CASCADE REASONING
- If parent moved → child objects appear moved
- Avoid attributing all movement to object itself

NUMERIC DEPTH REASONING
If depth metrics are provided:
- Compare camera distance change vs object scale change
- Determine net perceptual size shift
- Use numeric justification when possible
- Example: "Camera distance increased by 7.2 units while object scale increased by 25%, resulting in a net apparent size increase"
- Always quantify when data is available

AMBIGUITY RESOLUTION
You will receive ambiguity hypotheses.
For each ambiguity:
- Evaluate evidence
- Resolve if possible
- Otherwise keep uncertainty explicit

Do NOT:
- Invent changes not in data
- Assume artistic intent
- Override provided facts

Be precise, cautious, and technical.

Return EXACTLY one JSON object.
No markdown.
No extra commentary.
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
  ],
  "resolved_ambiguities": [
   {
     "type": "...",
     "object": "...",
     "explanation": "...",
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
    required_keys = {"scene_summary", "events",
                     "conflicts", "object_summaries"}
    if not required_keys.issubset(data.keys()):
        raise ValueError(
            f"Schema validation failed: missing top-level keys. Found: {list(data.keys())}")


def compute_depth_metrics(scene1, scene2):
    """Compute camera distance deltas and object scale deltas for numeric reasoning."""

    def get_cam(scene):
        cams = scene.get("cameras", [])
        return cams[0] if cams else None

    def dist(v):
        return math.sqrt(sum(x * x for x in v))

    metrics = {}

    # Camera distance
    cam1 = get_cam(scene1)
    cam2 = get_cam(scene2)

    if cam1 and cam2:
        d1 = dist(cam1["location"])
        d2 = dist(cam2["location"])
        metrics["camera_distance_before"] = round(d1, 3)
        metrics["camera_distance_after"] = round(d2, 3)
        metrics["camera_distance_delta"] = round(d2 - d1, 3)
        if d1 > 0:
            metrics["camera_distance_change_pct"] = round(
                ((d2 - d1) / d1) * 100, 2)

    # Object scale deltas
    objs1 = {o["name"]: o for o in scene1.get("objects", [])}
    objs2 = {o["name"]: o for o in scene2.get("objects", [])}

    scale_deltas = []
    for name in objs1:
        if name in objs2:
            s1 = objs1[name].get("scale", [1, 1, 1])
            s2 = objs2[name].get("scale", [1, 1, 1])
            if s1 != s2:
                scale_deltas.append({
                    "object": name,
                    "scale_before": [round(v, 4) for v in s1],
                    "scale_after": [round(v, 4) for v in s2],
                    "scale_change_pct": [
                        round(((s2[i] - s1[i]) / s1[i]) *
                              100, 2) if s1[i] != 0 else 0
                        for i in range(min(len(s1), len(s2)))
                    ],
                })

    if scale_deltas:
        metrics["object_scale_deltas"] = scale_deltas

    return metrics


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

    ambiguities = load_json(AMBIG_PATH) if AMBIG_PATH.exists() else []

    depth_metrics = compute_depth_metrics(scene_v1, scene_v2)

    prompt = f"""
{SYSTEM_PROMPT}

{SCHEMA_DESCRIPTION}

VERIFIED DIFF DATA:
{json.dumps(enriched_diff, indent=2)}

AMBIGUOUS OBSERVATIONS:
{json.dumps(ambiguities, indent=2)}

DEPTH METRICS:
{json.dumps(depth_metrics, indent=2)}

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
                    types.Part.from_bytes(
                        data=IMAGE_V1_PATH.read_bytes(), mime_type="image/png"),
                    types.Part.from_bytes(
                        data=IMAGE_V2_PATH.read_bytes(), mime_type="image/png"),
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

            print(
                f"[Gemini] Semantic report generated successfully at {OUTPUT_PATH}")
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
