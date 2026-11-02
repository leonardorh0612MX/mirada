# Mirada

Webcam gaze tracking that stays accurate without manual recalibration.

A local gaze model drifts within minutes as posture and light change.
Mirada corrects it with **semantic anchors**: moments where screen
context makes the gaze target nearly certain (a deliberate hold on a
cell, the typing caret, a click target). A Meta multimodal model
(Muse Spark) proposes what the user is looking at; SAM 3.1 localizes
it. Local recursive least squares applies the correction. The large
models are never in the fast loop.

Primary use case: accessibility — using a computer by gaze for 15+
minutes without recalibrating, on a $0 webcam.

## Try the demo (Windows 11, PowerShell)

```powershell
cd C:\path\to\mirada
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install mediapipe opencv-python pillow openai meta-sam-parser numpy pywebview
Copy-Item .env.example .env   # put your Meta Model API key in MODEL_API_KEY
.\.venv\Scripts\python.exe tools\t3_mediapipe_probe.py   # downloads the face model, checks camera
```

Then pick your surface:

```powershell
.\.venv\Scripts\python.exe app\board_app.py    # communication board, native app window (recommended)
.\.venv\Scripts\python.exe app\beta.py         # gaze keyboard: type with your eyes (appearance map)
.\.venv\Scripts\python.exe app\board_web.py    # same board in a browser tab (fallback)
.\.venv\Scripts\python.exe app\board.py        # same board, Tkinter (fallback)
```

In the board: choose monitor and camera with live previews, sit
naturally (the ceremony learns YOUR comfortable pose), follow the
calibration dots including the head-turn prompts, then hold your gaze
~0.4 s on a cell to speak it. APPS opens huge tiles that launch real
applications (two holds to confirm); a floating "← MIRADA" circle
brings the board back. QUIT by gaze, or Shift+Q anywhere.

For the science workflow:

```powershell
.\.venv\Scripts\python.exe tools\record_session.py --seconds 900 --camera 0 --monitor 1
.\.venv\Scripts\python.exe tools\replay_v2.py data\sess-YYYYMMDD-HHMMSS
.\.venv\Scripts\python.exe tools\t14_figure.py        # A/B/C/D figure + table
.\.venv\Scripts\python.exe tools\t20_appearance.py    # appearance vs geometric, pooled
.\.venv\Scripts\python.exe tools\t27_residual.py      # population residual (negative result)
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Measured results (Nov 1, builder sessions, replayed identically)

- **The calibration fit was the biggest bug.** Standardizing it (fixed
  physical scales, group ridge, factorial gaze×posture enrollment)
  cut replay error **−58 %** (1295 → 546 px) on identical data.
- **Appearance beats geometry.** Per-session ridge over eye-crop
  pixels: **237 vs 427 px** leave-one-dot-out (n=373, −44 %). It is
  the keyboard default; trained fresh each session in ~90 s and
  discarded — no stored biometrics.
- **Semantic anchors: modest on free screens.** Batch-of-4 Huber
  updates give −4 % mean error (−6 % late-session); the pre-registered
  consensus gate applied zero anchors and is reported as a failed
  design (docs/EVAL.md, T14 verdict). Inside controlled apps, anchors
  are exact and corrections are large.
- **Population residual does not transfer** across days (LOSO −1 %):
  residuals belong to the day's posture/lighting regime. Documented
  negative result (T27).
- Live task proof: gaze keyboard typed HOLA in **33–36 s, 0 errors**;
  communication board: 12 selections in 67 s, gaze-only quit.

## How it works

- `gaze/`: MediaPipe landmarks → geometric features → screen point;
  appearance model over eye crops; coverage hull; saccade gate.
- `corrector/`: 4-parameter bias/head-drift RLS over the frozen base
  map. Anchors carry certainty: deliberate holds apply directly
  (bias-only on the board), uncertain proposals need consensus.
- `anchors/`: Spark names the attended element (Responses API);
  SAM 3.1 segments it; mask centroid is the anchor. Degrades to
  clicks, then to calibration-only.
- `recorder/`: append-only monotonic session logs (features, events,
  screenshots with monitor provenance, ground-truth dots every 2 min).
  Every strategy comparison replays identical data.
- `eval/`: A (calibration only), B (clicks), C (semantic), D (+SAM):
  error over time, drift slope, anchor precision and harm rate.

## Honest limitations

- One participant so far; volunteer sessions are the missing evidence.
  Per-session results are reported, never silently pooled.
- Posture outside the enrollment family still breaks the base map;
  anchors correct bias, not a warped map.
- SAM localizes UI text poorly on free-form screens; Spark anchors
  need capturable screen content (fullscreen video yields black
  frames and no anchors).
- Webcam gaze starts at several degrees of error. This project fights
  drift and cost, not the physics of a $0 sensor.

## Docs

- [PAPER_DRAFT.md](docs/PAPER_DRAFT.md) — paper draft with the full
  results and reproduction commands.
- [EVAL.md](docs/EVAL.md) — protocol fixed in advance, and the
  verdicts including the negative ones.
- [DECISIONS.md](docs/DECISIONS.md) — every technical decision with
  alternatives (D1–D18).
- [ARCHITECTURE.md](docs/ARCHITECTURE.md), [RESEARCH.md](docs/RESEARCH.md),
  [TASKS.md](docs/TASKS.md), [GUIA_VOLUNTARIO.md](docs/GUIA_VOLUNTARIO.md).
