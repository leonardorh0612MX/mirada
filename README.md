# Mirada — look + hold to speak

A gaze communication board that runs on an ordinary webcam. No headset, no
eye tracker, no per-frame cloud calls: look at a cell, close your eyes for
~0.4 s, and the computer speaks. Built for the Meta Global AI Developer
Hackathon (accessibility track).

Demo video: recorded Nov 3–4, linked here on submission day.

This repo was created for the event (initial commit Oct 31, 2026):
nothing in it pre-exists the hackathon — every line was written this
week.

## Why it's special

- **Zero hardware beyond a webcam.** A $30 camera replaces a $5,000
  dedicated eye tracker for phrase-level communication.
- **It corrects its own drift.** Every selection you confirm becomes a
  semantic anchor that re-biases the gaze map (small online correction,
  trust-capped); a posture guard freezes learning when you leave your
  calibrated pose instead of learning garbage.
- **It works inside real apps.** An APPS page launches Discord, the
  browser, YouTube and more with huge tiles; your gaze then becomes the
  mouse (look freely, close your eyes 0.4 s to click — same grammar as
  the board), a floating dock takes you back, and an on-screen keyboard
  types into any field.
- **Private by construction.** Gaze, calibration and speech run fully
  offline on your machine. Cloud models touch only the research tooling,
  never the live loop.

## 60 seconds to your first sentence (Windows 11, PowerShell)

Prerequisites: Windows 10/11, a webcam, and Python 3.11 or 3.12 from
[python.org](https://www.python.org/downloads/) (check "Add python.exe to
PATH"; the Microsoft Store Python lacks pip support for this workflow).
No API key needed — the board runs fully offline.

```powershell
cd C:\path\to\mirada
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe mirada.py
```

Notes: the `.venv` folder is never shipped — every machine creates its own
with the commands above, and there is no need to run `Activate.ps1` (it
trips PowerShell execution policies); all commands call the project's
Python directly. The face model (`data/face_landmarker.task`) ships in the
repo, so nothing downloads at first run.

What happens next, inside the window:

1. Pick your screen, camera and language (EN/ES) with live previews.
2. Get comfortable and follow the dots with head AND eyes together.
3. Look at YES, close your eyes briefly — it speaks. Try WATER, THANKS,
   then the KEYBOARD page and the APPS page.

Caregiver mouse always works alongside gaze. Shift+Q quits anywhere.

## What you can do with it

- **Speak in seconds**: 8 huge cells (YES/NO/WATER/BATHROOM/HELP/THANKS/
  COME/PAIN) with offline speech, editable phrases, EN/ES voices.
- **Type anything**: a full gaze keyboard with word completion and a SEND
  key that delivers the text into the focused app.
- **Use your computer**: launch apps from giant tiles (double-hold to
  confirm), click with a 0.4 s eye-close anywhere you look, return
  anytime with the floating MIRADA tile — ghosted until you look at it.
- **Stay calibrated**: selections quietly re-anchor the map; if you
  slouch out of your pose it tells you to press R instead of dying
  silently.

## Under the hood (30 seconds)

Local MediaPipe landmarks (~30 fps) feed a calibrated gaze map; a tiny
bias-only recursive corrector absorbs drift from your confirmed
selections; tile-size uncertainty, a repeat cooldown and a posture
guardrail keep bad labels from poisoning it. Start here:

- `docs/ARCHITECTURE.md` — modules, data flow, interfaces.
- `docs/DECISIONS.md` — every technical decision with alternatives (D1–D39).
- `docs/RESEARCH.md` — verified prior art (WebGazer, Aria, Online-EYE…).

## Where the Meta models run

| Model | What it does | Where it runs |
|---|---|---|
| `muse-spark-1.3` | Proposes semantic anchors: looks at a screenshot + context and names what you almost certainly looked at, with confidence | Research tooling (`tools/gen_anchors.py`), offline after a session |
| `sam-3.1` | Pinpoints the proposed concept to a pixel box on the screenshot (strategy D) | Same run, Meta Model API |
| `muse-spark-open` (Baseten) | High-volume Spark backend for anchor generation | Same tool, `--backend baseten` |
| `muse-wonder-1.0` | Architecture review (gaze-map math, enrollment design) | Design time, not shipped |
| `muse-image-1.0` | README/site artwork | Design time, committed under `site/` |

Deliberately: the live product calls **no model at all** — the LLM
provides labels offline, local math (affine map + bias corrector) does
the correction at ~30 fps. That is the whole thesis, and why the app
runs for judges with no API key.

## The science

Recorded sessions replay offline under competing strategies (A: calibrate
once, B: WebGazer-style clicks, C: semantic anchors), scored against
fixation dots. First two-participant result: consensus anchors cut mean
error 406 → 397 px (−2.2%) on the volunteer's session; the same rig
documents drift exploding 63 → 941 px in 15 minutes without correction.
Protocol, metrics and honest verdicts: `docs/EVAL.md`. Paper draft:
`docs/PAPER_DRAFT.md`.

Research tooling needs keys (copy `.env.example` to `.env`, fill
`MODEL_API_KEY`, plus `BASETEN_API_KEY` for the Baseten backend):

```powershell
.\.venv\Scripts\python.exe tools\record_session.py --seconds 900
# Camera/monitor auto-detected (a chooser appears if several exist).
.\.venv\Scripts\python.exe tools\gen_anchors.py data\sess-<date> --backend baseten
.\.venv\Scripts\python.exe tools\replay_v2.py data\sess-<date>
```

## Repo map

| Run this | What it is |
|---|---|
| `mirada.py` | **The app.** Native board window: phrases, keyboard, apps, eye-mouse. Start here. |
| `app/board.py` | Same board as plain Tkinter. Fallback if the native window misbehaves. |
| `app/beta.py` | Gaze-typing trainer (type HOLA). Measures raw typing, not communication. |
| `app/desktop.py` | Early fine-cursor experiment. Superseded by the in-app eye mouse. |
| `app/board_web.py` | The engine `mirada.py` serves (web UI). Run directly for browser mode. |

Core (imported, not run): `gaze/` landmarks→features, `corrector/`
online bias + fusion guards, `anchors/` Spark/SAM proposals, `eval/`
replay strategies, `recorder/` session logs.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

233 tests, all green. Covers calibration math, blink/hold detection,
fusion guards, language tables, dock geometry, keyboard injection,
config round-trips and replay determinism.

## Volunteers and credits

- Can you spare 20 minutes in front of a webcam? `docs/GUIA_VOLUNTARIO.md`
  (setup + what to send back), `docs/GUIA_PARTICIPANTE.md` (the session
  script). Sessions stay on your machine unless you share them.
- Built with Meta models: `muse-spark-1.3` (anchor proposals),
  `muse-wonder-1.0` (architecture review), `sam-3.1` (segmentation),
  `muse-image-1.0` (artwork), plus `muse-spark-open` weights via Baseten.
