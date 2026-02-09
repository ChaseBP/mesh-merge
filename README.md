# 🧠 MeshMerge

### *An AI scene-diff engine that understands **why** a 3D scene changed — not just what changed.*



---

## 📍 Quick Links
* [🚨 The Problem](#-the-problem-git-diff-cant-understand-3d)
* [💡 The Solution](#-the-solution-a-causal-scene-diff-engine)
* [🏗️ System Architecture](#️-system-architecture)
* [🛠️ Installation & Setup](#️-installation--setup)
* [▶️ Run MeshMerge](#️-run-meshmerge)


---

### 📺 [Watch the Full Walkthrough](https://www.youtube.com/watch?v=vLYj7rjWTIE)


**🏆 Built for Gemini 3 Hackathon**

---

## 🚨 The Problem: Git Diff Can’t Understand 3D

Version control works great for code.

It completely fails for **3D scenes**.

When a `.blend` file changes:

* ❌ You can’t see what changed
* ❌ You can’t see *why* it changed
* ❌ You can’t tell if it’s camera, lighting, or geometry
* ❌ You can’t review scene edits like a PR

If an artist scales a building but moves the camera back…

Git shows:

```
binary file changed
```

But the real question is:

> **Was the building scaled?
> Or did it just *look* scaled because the camera moved?**

**Traditional diff tools cannot answer this.**

---

## 💡 The Solution: A Causal Scene Diff Engine

**MeshMerge** is a multimodal AI system that analyzes two 3D scenes and produces a human-readable explanation of what changed — and *why it appears different.*

Instead of:

```
file_v1.blend → file_v2.blend
```

MeshMerge does:

```
3D scene → structural diff → visual diff → ambiguity detection → AI reasoning → changelog + report
```

The result:

> A Git-style change log for 3D scenes.
---
## 🏗️ System Architecture

<img width="371" height="1107" alt="Image" src="https://github.com/user-attachments/assets/3ec7d427-bbbf-49d3-8254-3b524b14647b" />

The result:

> A Git-style change log for 3D scenes.

---

## ✨ Key Differentiators

| Capability                     | Traditional Tools | MeshMerge                    |
| ------------------------------ | ----------------- | ---------------------------- |
| Scene diff                     | ❌ Binary only     | **✅ Structural diff**        |
| Visual confirmation            | ❌ None            | **🖼 Image heatmaps**        |
| Camera vs geometry reasoning   | ❌ Impossible      | **🧠 Depth-aware inference** |
| Lighting vs material ambiguity | ❌ None            | **🔎 Causal resolution**     |
| Multi-change correlation       | ❌ No              | **📊 Event grouping**        |
| Human-readable changelog       | ❌ No              | **📄 Yes**                   |
| PDF visual report              | ❌ No              | **📘 Yes**                   |

---


## 🧠 The Core Idea

MeshMerge separates scene changes into three layers:

### 1️⃣ Deterministic Facts

* object scaled
* light intensity changed
* camera moved

### 2️⃣ Perceptual Observations

* object looks bigger
* scene looks darker
* region changed visually

### 3️⃣ AI Causal Reasoning

Gemini resolves contradictions like:

> Object scaled + camera moved back
> → net visual size unchanged

This is something pure JSON diff **cannot** do.

---

## 🔬 Example Output

```md
# MeshMerge Change Log

## Scene Summary
The scene underwent a structural object scale increase while the camera simultaneously moved backward, resulting in near-identical viewport framing.

**Overall significance:** structural

## Events
- Cube scaled up by 25%
- Camera moved back by 23%
- Light intensity reduced by 30%

## Interpretation
The camera movement partially cancels the visual impact of the scale change.
```

---

## 🧠 Under the Hood: The Reasoning Engine

MeshMerge uses Gemini as a **causal inference layer**, not just a formatter.

It receives:

* verified structural diffs
* visual regions
* ambiguity hypotheses
* depth metrics

Then outputs a strict JSON schema describing:

* semantic events
* conflicts
* causal explanations
* confidence levels

Example:

```json
{
  "event": "SCALE_CAMERA_COMPENSATION",
  "explanation": "Object scaled 25% while camera moved back 23%, producing minimal visual change.",
  "confidence": "high"
}
```

---

## 🛠️ Installation & Setup

### 📋 Requirements

* Python 3.10+
* Blender 4.x or 5.x
* Google Gemini API key



### Clone Repo

```bash
git clone https://github.com/ChaseBP/mesh-merge
cd meshmerge
```



### Install Dependencies

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```



### Setup .env 

**⚠️ Configure Environment Variables**
1. Look for the `.env.example` file in the main folder and rename it to `.env`
2. Open `.env` and paste your keys.

```python
GEMINI_API_KEY = "your_key_here"
```

---

## ▶️ Run MeshMerge

```bash
python analyzer/analyze.py before.blend after.blend
```


Outputs:

```
/outputs
 ├── CHANGELOG.md
 ├── semantic_scene_report.json
 ├── meshmerge_report.pdf
 ├── diff.json
 └── enriched_diff.json
```

---

## 📄 Output Artifacts

| File                       | Purpose                   |
| -------------------------- | ------------------------- |
| CHANGELOG.md               | Human readable scene diff |
| semantic_scene_report.json | AI reasoning output       |
| meshmerge_report.pdf       | Visual report             |
| diff.json                  | Structural changes        |
| enriched_diff.json         | Vision-confirmed diffs    |
| ambiguities.json           | Hypothesis layer          |

---

## 🎬 Demo Scenarios

MeshMerge can detect:

* Camera move vs object scale
* Lighting vs material change
* Parent transform cascades
* Perceptual-only changes
* Multi-object correlation

---

## 💻 Tech Stack

| Layer              | Tech                  |
| ------------------ | --------------------- |
| Blender Automation | bpy                   |
| Diff Engine        | Python                |
| Vision Diff        | Pillow + NumPy        |
| AI Reasoning       | Gemini                |
| Reports            | ReportLab             |
| Output             | JSON + Markdown + PDF |

---


## 🚀 Future Roadmap

* [ ] Depth-accurate projection instead of heuristic
* [ ] Scene graph parent detection
* [ ] Real-time Blender plugin
* [ ] GitHub PR diff viewer for `.blend`
* [ ] Video timeline diff

---

## 🏁 Final Note

MeshMerge is not a renderer.

It’s not a diff tool.

It’s a **scene reasoning engine**.

It answers:

> Why does this scene look different?

And that’s something Git never could.

---

## ⭐ If You Like This Project

Star the repo.
Share it with 3D devs.
Break it. Improve it. Extend it.

