# Mirada — demo video script (3:00 hard cap, footage locked 2:41)

Judges stop watching at 3:00. Footage locked Nov 4 (2:41) + 12 s
terminal insert + 4 s end card = ~2:53 target. English voiceover +
English subtitles. Screen recording (monitor 1) + facecam PiP
bottom-right ~300px, static all take.

On-screen stat captions (free: they cost zero narration seconds, and
judges remember numbers): "$0 hardware" (over calibration), "holds
14/15" (over board cells), "−2.2% vs baseline, honest n=2 pilot"
(over the terminal insert). Small, lower-third, 3 s each. The
calibration stretch MUST carry a burned-in "SPED UP 4×" label
(organizer rule).

## Recording setup (10 min) — zero camera conflicts

Windows gives one app exclusive camera access, and merely OPENING OBS
with a camera source (even hidden, even not recording) steals the
device from Mirada. So OBS never touches a camera:

- OBS: new Scene Collection "Mirada", ONE scene with ONLY Display
  Capture (monitor 1). No Video Capture sources anywhere — check all
  scenes, including hidden ones. Record SILENT (mic muted).
- Face (front, proves the mechanism): laptop Camera app recording to
  file, if the open lid sees your face; else a phone on tripod facing
  you. PiP bottom-right in the edit (~300px, static all take).
  Bottom-right because the gaze tiles live top-right and must stay
  visible.
- Phone in PROFILE (you + screen + webcam) only for the first ~30 s
  as establishing credibility, then cut to pure screen+PiP. Never two
  PiPs at once (cluttered frame).
- Sync: one hand clap in view of all cameras at take start (same
  performance + slate = honest sync). Voiceover afterwards in post.
- Order: start Mirada FIRST (pick Logitech, calibrate, reach board),
  then start all three recordings. 10 s test: ring, tiles, and your
  face (eyes closing!) all framing correctly before the real take.
- Prep: close Teams/Zoom/extra tabs, USB selective suspend OFF, Logitech
  direct to laptop, frontal light on.

## Script — fitted to locked footage (voiceover recorded in post)

Pace: ~130 wpm, conversational. Stay SILENT under TTS cell speech
and let UI sounds breathe. Pronounce "SAM" as "sam".

### 0:00–0:37 — Opening: hook + problem (face on camera)

> "Nothing existed before October thirty-first — no repo, no code.
> This week I built Mirada, developed one hundred percent on Meta
> models: full computer control from a plain webcam. Here's the
> problem. Cheap eye tracking drifts within minutes — so anyone who
> depends on gaze — ALS, spinal injury, motor impairments — must
> recalibrate constantly, or pay five thousand dollars for a
> dedicated tracker. Mirada is a look-plus-hold communication board
> with semantic recalibration: a local thirty-fps gaze loop,
> corrected by sparse AI anchors."

(~79 words. Ends exactly as calibration starts at 0:37.)

### 0:37–1:18 — Enrollment at 4× (the explanation window)

> "Enrollment: forty-three gaze-by-posture dots with spoken
> instructions — sped up four times here. Each dot teaches a tiny
> map from my eyes to the screen. And here is the key idea: every
> time I confirm a selection, that choice becomes a semantic anchor
> — Muse Spark reads the screen, SAM pinpoints it to the pixel —
> and a small online corrector re-biases the map. Drift absorbed.
> Automatically. No headset. No eye tracker. One thirty-dollar
> webcam. It usually passes first try."

(~75 words over 41 s — deliberately roomy; pause between sentences
and let the dots carry the pace. Caption: "$0 hardware".)

### 1:18–1:38 — Board, live (the heart — get out of the way)

> "Look at a cell, close your eyes for half a second — it speaks."

(Say ONLY this at 1:18. Then silence 1:21–1:38 while the cells
speak. Optional tag at ~1:36 if a silent gap allows: "Eight huge
cells, editable phrases, English and Spanish voices." Caption:
"holds 14/15".)

### 1:38–2:00 — Real apps (the wow)

> "And the same grammar drives any app. Watch: APPS — YouTube. My
> gaze is the mouse now: look anywhere, close to click. Need to
> type? That floating tile opens a full gaze keyboard."

(~33 words. "APPS — YouTube" lands on the 1:38–1:43 tile taps;
"floating tile" lands as the keyboard opens ~2:00.)

### 2:00–2:27 — Typing "meta" (sync with the fingers-that-aren't)

> "Typing with nothing but my eyes — M, E, T, A — with word
> completion finishing my thoughts. SEND delivers it straight into
> YouTube search."

(~26 words. Spell the letters as they appear from 2:07; "SEND
delivers it" lands on the 2:27 enter.)

### 2:27–2:41 — Payoff + close (say exactly this, brisk)

> "Results — one gaze-click, and we're watching. No headset, no eye
> tracker, no API key: just a webcam, so try it yourself. Next: the
> same anchors for headset gaze. Mirada: look plus hold."

(~34 words over 14 s. "We're watching" lands on the Meta VR video
select at 2:34; the rest runs over playback into the end card.)

### Terminal insert (record separately, splice after 2:34)

The locked footage never shows a Meta model call, and the rules
require model calls visible. Record 12 s now (any session dir):

```powershell
.\.venv\Scripts\python.exe tools\gen_anchors.py data\sess-<date> --backend meta
```

Keep the `models: muse-spark-1.3 (concepts) + sam-3.1 (boxes)` line
+ 3–4 live concept lines. Splice: trim the video-play tail to ~3 s,
insert the 12 s terminal, then the 4 s end card (repo URL + "paper
draft in repo"). New total ≈ 2:53. Voiceover over the insert:

> "The AI behind it, live: Spark proposes where I looked, SAM
> pinpoints it, and the replay harness scores every strategy
> offline. Honest numbers, paper draft in the repo."

Caption over the insert: "−2.2% vs baseline, honest n=2 pilot".

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
