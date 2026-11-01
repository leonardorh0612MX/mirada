# Mirada

Webcam gaze tracking that stays accurate without manual recalibration.

A local gaze model drifts within minutes. Mirada corrects it with **semantic anchors**: moments where screen context makes the gaze target nearly certain (the typing caret, a click target). A Meta multimodal model proposes what the user looks at. SAM 3.1 localizes it. Local math applies the correction. The model is never in the fast loop.

Primary use case: accessibility. Using a computer by gaze for 15+ minutes without recalibrating.

## Status (Oct 27, 2026)

Working and tested: gaze features, RLS corrector with anchor gating, anchor ledger, Spark proposals, SAM localization (mask centroid agrees with box to <1 px), session recorder, A/B/C/D replay harness with report. 45 unit tests green.

Pending: real volunteer sessions, benchmark numbers, demo video. No headline claim until the replay runs on real data.

## Setup (Windows 11, PowerShell)

```powershell
cd C:\Users\Leonardo.Rodriguez\mirada
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install mediapipe opencv-python pillow openai meta-sam-parser numpy
Copy-Item .env.example .env   # then put your Meta Model API key in MODEL_API_KEY
```

Run the checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe tools\t3_mediapipe_probe.py      # camera + landmarks
.\.venv\Scripts\python.exe tools\record_session.py --seconds 900 --camera 0
```

## How it works

- `gaze/`: MediaPipe landmarks to features to raw screen point, with validity flags.
- `corrector/`: RLS correction over the calibration map. Anchors pass confidence, residual, and age gates. Rejections never touch the filters.
- `anchors/`: Spark names the attended element (Responses API). SAM 3.1 segments it. Mask centroid is the anchor point. Degrades to Spark point, to clicks, to calibration-only.
- `recorder/`: append-only timestamped sessions. Replay-first: every comparison runs on identical data.
- `eval/`: replay A (calibration only), B (clicks), C (semantic), D (plus SAM). Reports error over time, drift slope, cost.

## Honest limitations

- Webcam gaze starts at several degrees of error. This project fights drift, not the base error.
- Semantic anchors are gated guesses. The anchor harm rate is a first-class metric.
- Results so far are synthetic. The benchmark on real sessions decides the headline, including a negative one.

## Docs

- [ARCHITECTURE.md](docs/ARCHITECTURE.md), [DECISIONS.md](docs/DECISIONS.md), [RESEARCH.md](docs/RESEARCH.md), [EVAL.md](docs/EVAL.md), [TASKS.md](docs/TASKS.md).
