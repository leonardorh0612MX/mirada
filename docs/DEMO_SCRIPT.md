# Mirada — demo video script (3:00 hard cap, 2:50 target)

Judges stop watching at 3:00 — so we target 2:50 and leave 10 s of
safety for the end card. English voiceover + English subtitles.
Screen recording (monitor 1) + facecam PiP bottom-right ~300px, static
all take. Every scene below was verified live on master (`738aa37`).

On-screen stat captions (free: they cost zero narration seconds, and
judges remember numbers): "$0 hardware", "holds 14/15", "−2.2% error
vs baseline (honest n=2 pilot)". Place each over its scene, small,
lower-third, 3 s.

## Recording setup (OBS, 10 min)

- Scene: monitor-1 capture full-frame + Logitech PiP bottom-right.
  Bottom-right because the gaze tiles live top-right and must stay
  visible; the PiP only covers a corner func cell at the very end.
- Record takes SILENT (mic muted): screen + facecam must share one
  take so eye↔action sync is real — never composite them from separate
  recordings. Voiceover is recorded afterwards over the edit (perfect
  timing, no filler words). 10 s test: ring, tiles, and your face
  (eyes closing!) all visible before the real take.
- Prep: close Teams/Zoom/extra tabs, USB selective suspend OFF, Logitech
  direct to laptop, frontal light on.

## Script

### 0:00–0:12 — Opening (say exactly this)

> "Nothing existed before October 31st — no repo, no code. This week I
> built Mirada, developed 100% on Meta models: full computer control
> from a plain webcam."

(On screen: logo holds on the hackathon credit line until you click
or press Space — advance it mid-"problem" beat, on your cue.)

### 0:12–0:30 — Problem and product

> "Cheap eye tracking drifts within minutes, so anyone who depends on
> gaze — ALS, spinal injury, motor impairments — must recalibrate
> constantly, or pay five thousand dollars for a dedicated tracker.
> Mirada is a look-plus-hold communication board with semantic
> recalibration: a local 30 fps gaze loop, corrected by sparse AI
> anchors, so it holds calibration with no manual recal."

(On screen: setup screen — pick monitor, camera, language. Caption:
"$0 hardware".)

### 0:30–0:42 — Enrollment montage (label: SPED UP 4×)

> "Forty-three gaze-by-posture dots with spoken instructions. It
> usually passes first try."

(On screen: 3 dots with voice, then cut to the board. Caption on
screen: "43-point voice enrollment — sped up".)

### 0:42–1:25 — Board, live (the heart — slow down here)

> "Look at a cell, close your eyes for half a second — it speaks."

(On screen, do it, don't rush — one cell every ~10 s:)
WATER (hold visible in PiP + voice) → HELP → THANKS. Caption:
"holds 14/15".
Then: "Same grammar types anything:" KEYBOARD page, gaze-hold H-O-L-A.

### 1:25–2:10 — Real apps (the wow)

> "And the same grammar drives any app. My gaze is the mouse now: look
> anywhere, close to click."

(On screen: APPS page → open YouTube (double-hold) → yellow ring
follows gaze → hold-click a video → TECLADO tile → type "hola" →
SEND → MIRADA tile back to the board. ~45 s, one smooth flow.)

### 2:10–2:40 — Meta models, live in the terminal

> "Click-based recalibration is the old way. Mirada innovates: Muse
> Spark reads the screen and infers where you almost certainly looked,
> and SAM 3.1 pinpoints it to the pixel — with Muse open-weights models
> carrying the high-volume runs, Wonder on architecture review, and
> Muse Image on artwork. Those semantic anchors correct the local
> model — never per frame, only as labels. We're writing this up as a
> research paper; the draft and the replay harness ship in the repo."

(On screen, terminal, real commands:)
`tools\gen_anchors.py data\<sess> --backend meta` — show the
`models: muse-spark-1.3 (concepts) + sam-3.1 (boxes)` line + 3–4 live
concept lines → `tools\replay_v2.py` A/B/C/D table (error-over-time).
Caption over the table: "−2.2% vs baseline (honest n=2 pilot)".

### 2:40–2:55 — Close: vision + run-it-yourself (say exactly this)

> "No headset, no eye tracker — and it holds calibration. It runs
> with no API key, just a webcam, so you can try it yourself. Next
> stop: the same anchors correcting drift in headset gaze. Mirada:
> look plus hold."

(On screen: board, Shift+Q quit to black. End card 2:55–3:00: repo
URL + "paper draft in repo". Total target 2:50–2:58 — never past
3:00.)

## Rehearsal protocol (mandatory)

1. One full take, no narration (~6 min). Console must show: single
   enrollment (no retry), `app click (hold)` lines, `sent to app`,
   `returned to board`, clean `done:` — no `CAMERA LOST`, no traceback.
2. Fix-or-cut: rehearsal clean → real take. Tiles/hold-clicks shaky →
   cut apps to a 10 s montage and let board + keyboard carry the video.
   Enrollment retry on camera is honest — keep rolling; restart only on
   camera death.
3. Real take: max 3 attempts, then ship the best one.

## Post checklist

- [ ] Upload best take unlisted to YouTube; verify the link opens logged
      out (private window).
- [ ] English subtitles (YouTube Studio auto-base, fix by hand, 10 min).
- [ ] README: replace the video note with the link (own commit).
- [ ] Submit the form (repo + video links) by 7 PM ET Nov 4 — 2 h buffer
      before the 9 PM ET deadline. Save the confirmation screenshot.

## Why this wins (judge mapping — internal)

| Criterion | Where the video hits it |
|---|---|
| Creativity | Semantic anchors (Spark infers + SAM pinpoints) vs click-only status quo — named in the models segment |
| Technical ambition | 43-dot factorial enrollment, fusion guards, offline A/B/C/D replay harness with honest numbers (incl. rejected approaches in DECISIONS) |
| It actually works | 2+ min of continuous live footage, eye↔action sync in PiP, plus "runs with no API key" (judges verify themselves) |
| Build for Your World | ALS/spinal-injury framing + $0 vs $5,000 contrast, real accessibility tool |
| Push the Frontier | Vision close: same anchors for headset gaze + paper in progress |
| Meta fit | 5 Meta models named with live calls on screen, 100% Meta AI stack |

Honesty is the differentiator: the −2.2% is small and labeled n=2,
drift-without-correction is shown (63→941 px), dead ends are logged.
Judges punish inflated claims harder than small numbers.

## Rules from the organizers (do not break)

- ≤3:00, judges stop at 3:00. Running product only, no slides, no code
  walkthrough. Setup belongs in the README.
- Meta model calls must be visible (output or log line naming the
  model) — the terminal segment covers this.
- Only features built during the event; label sped-up/simulated steps.
- Repo public, created Oct 26+, incremental history; README explains
  models + setup judges can run.
