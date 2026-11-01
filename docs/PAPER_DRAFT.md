# Mirada: Semantic Recalibration for Drift-Robust Webcam Gaze

**Draft — Oct 31, 2026. All numbers below are measured on recorded sessions
or live runs cited by session id. No number is projected or simulated except
where explicitly labeled. Figures marked TODO are to be generated from the
replay reports before submission.**

Leonardo Rodríguez Hernández (solo builder, Meta Global AI Developer Hackathon)

## Abstract

Webcam gaze tracking fails in practice because the feature-to-screen map is
fit once, under one posture, and posture is not stationary. We present
Mirada, a two-rate system: a local landmark loop (~30 fps, MediaPipe) whose
map is corrected online by sparse *semantic anchors* — screen targets the
user almost certainly fixated, proposed by a multimodal model (Meta Muse
Spark) and localized by segmentation (Meta SAM 3.1) — plus, in controlled
apps, exact anchors from confirmed selections. No model is called per frame;
the large models only supply labels, and local recursive least squares does
the correction. On five recorded 15-minute study sessions replayed offline,
we find (1) the dominant error source is not drift but an *unidentifiable
calibration fit*: standardizing the fit (fixed physical feature scales,
group ridge) cuts mean error 58% on identical data (1295 px to 546 px);
(2) anchor gating is a trap — any hard gate rejects every anchor exactly
when the map is broken — while soft/forced updates yield a modest, honest
−10 to −16%, and remain stable under up to 50% deliberately corrupted
anchors (the ablation GazeAgent declares unverified); (3) a per-session
appearance model (ridge over eye-crop pixels, enrolled in ~90 s, discarded
at session end) beats the geometric map where enrollment data is sufficient
(255 vs 384 px leave-one-dot-out) and typed our target word live in 36.3 s
with 0 errors, versus 33.2 s for the geometric map with exact anchors.
A gaze communication board (8 cells, offline speech) runs end-to-end on a
$0-webcam setup. We state limits plainly: one participant for anchor
results, posture excursions outside the enrollment family still break the
base map, and SAM localizes UI text poorly on free-form screens.

## 1. Introduction

Dedicated eye trackers (Tobii, PCEye) work but cost enough to exclude most
of the people who need gaze input. Webcam gaze is free and, minutes after
calibration, wrong: the user leans, the light changes, and the map — fit
with the head effectively frozen — extrapolates coefficients it never
identified. Users recalibrate constantly, which is precisely what a person
with ALS cannot do.

Our claim is narrow and testable: *the screen itself, understood
semantically, provides a slow stream of gaze labels good enough to keep a
fast local map honest* — the text caret while typing, the control about to
be activated, the element confirmed by a deliberate hold. The architecture
that follows from that claim is two-rate by necessity: large multimodal
models are too slow and too expensive per frame (measured Spark vision
latency ~0.75 s median on our link), so they propose anchors every few
seconds while recursive least squares corrects the map locally at frame
rate.

Contributions:

1. **An identifiability diagnosis of webcam gaze calibration**, with a
   factorial enrollment (gaze × posture) and fixed-scale group-ridge fit
   that removes the failure (−58% replay error, Sec. 4.1).
2. **An anchor-update discipline with a corruption ablation**: hard gates
   and consensus never fire on real noisy anchors (measured, 0 applied);
   soft-weighted updates help modestly and degrade gracefully to −7% at
   50% label corruption (Sec. 4.2).
3. **A per-session appearance map** that needs no stored biometrics and
   wins live typing tests against the geometric map (Sec. 4.3), plus a
   working accessibility board as the product surface (Sec. 5).

## 2. Related work

- **Click self-calibration.** WebGazer.js recalibrates from clicks and
  mouse movement. Our strategy B reproduces that family in replay; our
  disagreement is not with clicks but with their sparsity and bias (clicks
  happen where the mouse already is).
- **Aria / MPS (Meta).** Project Aria estimates a per-frame 3D gaze ray in
  the Central Pupil Frame from dedicated eye cameras (Engel et al., 2023,
  arXiv:2308.13561; facebookresearch/projectaria_eyetracking). MPS
  personalization emits `personalized_eye_gaze.csv` only after an explicit
  in-session calibration, applying scale+offset corrections in angle space
  (facebookresearch/projectaria_tools, reviewed Oct 31). Mirada is the
  same "general model + tiny affine corrector" pattern with two changes:
  the sensor is a commodity webcam, and the corrector's labels come from
  interaction semantics, continuously, with no calibration procedure.
- **Implicit calibration in XR.** Online-EYE (Hou et al., CHI 2025,
  doi:10.1145/3706598.3713461) calibrates head-mounted trackers from
  multimodal implicit cues; two of its findings replicate here on webcam:
  correction holds inside the convex hull of anchor targets, and degrades
  outside it (our board therefore gates highlights to the enrollment hull).
- **GazeAgent** (arXiv:2610.24364) adapts a frozen population residual
  plus an online affine stage; it declares robustness to corrupted
  implicit labels unverified. Sec. 4.2 runs exactly that experiment.

## 3. System

**Local loop.** MediaPipe FaceLandmarker (Tasks API) yields 478 landmarks
at ~28.7 fps measured on the builder's laptop. Seven geometric features
(iris offsets normalized by eye width, head-pose proxies) feed the base
map. A long eye-hold (≥0.4–0.6 s; natural blinks ~100–200 ms never reach
it) selects; guided testing scored long-hold 14/15 against deliberate
doubles, which misfired 5/5 because natural blinks pair inside any window.

**Enrollment (~90 s).** Factorial blocks make gaze and posture vary
independently: 9 centered dots; 5 dots × 5 poses (yaw ±15°, pitch ±10°);
distance/lean variants; blink-threshold block; a repeat block as drift
check. Features are standardized by *fixed* physical scales pooled across
sessions (never re-estimated per fit), and each output coordinate is a
ridge fit over [features, gaze×head interactions, squares] with
interactions penalized harder than main effects (λ 5 vs 25, Huber at
100 px). Error is reported leave-one-gaze-point-out only; resubstitution
is meaningless at n≈32 (it once reported 36 px for a map that collapsed
live; the honest leave-one-out was 191 px).

**Corrector.** Online updates touch only 4 parameters (screen bias +
head-coupled drift) by RLS (λ_f = 0.995), with a per-update trust region
(≤25 px) and soft anchor weight 1/(1+(r/150 px)²). Anchors carry a
certainty label: a completed deliberate hold in a controlled app certifies
intention, so its label is exact and applies directly; uncertain semantic
anchors from free screens require consensus and are down-weighted.
Selections also emit a *pre-blink* feature snapshot (0.7 s before the
hold), because gaze during lid closure is garbage — measured closed-eye
drift median 703 px in our probe.

**Semantic lane.** On free screens, Muse Spark (Responses API, vision)
proposes the attended element ("text caret in the search box", conf.
0.70); SAM 3.1 localizes it (streamed noun-phrase parsing; mask centroid
as anchor). Measured on controlled UI targets: Spark points median 4 px
error, SAM-refined median 1 px, 9/9 matched (`tools/ui_precision.py`).
On uncontrolled study screens Spark proposed 29 anchors in one session,
SAM only 5 usable ones — it segments objects, not UI text (Sec. 4.2).

**Recorder/eval.** Every session logs features, events, screenshots with
monitor identity and scale provenance, calibration samples, eye crops,
and ground-truth dots every 2 min, under one monotonic clock. All
strategies (A initial-only, B click, C semantic, D C+SAM) replay offline
on identical data (`tools/replay_v2.py`).

## 4. Results

All replay numbers: five 15-min builder study sessions, 7 ground-truth
dots each, identical data per strategy (`docs/EVAL.md` holds the full
tables; session ids in the repo's `data/` logs).

### 4.1 The fit was the bug

Replacing the original fit (unscaled normal equations; coefficients to
±55,000; inversion under head-led gaze) with fixed scales + group ridge:

| Session | Legacy fit | Refit | Δ |
|---|---|---|---|
| sess-20261027-144550 | 1246 px | 691 px | −45% |
| sess-20261027-181528 | 1975 px | 780 px | −61% |
| sess-20261027-193736 | 659 px | 400 px | −39% |
| sess-20261027-203334 | 599 px | 304 px | −49% |
| sess-20261027-210940 | 1997 px | 555 px | −72% |
| **Mean** | **1295 px** | **546 px** | **−58%** |

[TODO Figure 1: per-dot error over time, strategies A/B/C/D, from
`tools/replay_v2.py` output.]

### 4.2 Anchors: gating traps, corruption does not kill

On sess-20261027-210940 (29 Spark anchors, 5 SAM anchors), A-refit =
555 px mean, slope +0.31 px/s. With a 150 px hard gate or consensus,
**zero anchors were ever applied** — residuals on a broken map run
500–4000 px, so the gate calibrated for a healthy map rejects help
exactly when help is needed. Forced updates without a hard gate: RLS
−10% (p0=0.05) to −16% (p0=0.5, slope worsens); SAM-refined (D) *hurt*
(568–631 px) on sparse study-screen anchors. In controlled apps the same
discipline inverts: exact key-centre anchors apply directly under
consensus, and in the HOLA run single accidental selections never moved
the map.

Corruption ablation (seeded label permutation; base 555 px):

| ρ corrupted | gated 150 px | forced full-RLS | consensus | batch4-Huber |
|---|---|---|---|---|
| 0.00 | 555 | 501 | 555 | 545 |
| 0.10 | 555 | 507 | 555 | 547 |
| 0.25 | 555 | 505 | 555 | 546 |
| 0.50 | 555 | 517 | 555 | 551 |

Forced full-RLS degrades gracefully (−10% → −7%); batch4-Huber is a
damped variant (+2%, flat). This is the experiment GazeAgent leaves
unverified; the answer is parameter-dependent, not a blanket yes/no.

### 4.3 Appearance map (T20)

Ridge over grayscale eye-crop vectors vs the geometric map,
leave-one-dot-out, pooled recorded crops: no clear win at n=35 pooled
(384 vs 366 px) because early sessions contribute 4–7 crops and overfit
(to 970 px). Where a session yields ≥19 crops, appearance wins clearly
(sess-20261029-222607: 221 vs 382 px; sess-20261030-084907: 289 vs
386 px); pooled sufficient-data regime 255 vs 384 px (−34%). Live
typing (target HOLA, ≤60 s, ≤2 errors = PASS): geometric 33.2 s
(beta-20261028-164342); appearance 45.0 s (beta-20261030-092548) and
36.3 s (beta-20261031-232738), 0 errors both. One appearance collapse
(beta-20261030-093037) predates the honest-LODO quality gate. Adopted
as beta default Oct 31 (D13); a CNN is ruled out at our data scale
(needs n≥200 per-person crops).

### 4.4 Product surfaces

- **Gaze keyboard** (T24): HOLA typed gaze-only as above.
- **Communication board** (T33/D11): 8 huge cells (SÍ/NO/AGUA/BAÑO/
  AYUDA/GRACIAS/LLAMAR/DOLOR) + sentence bar + offline Windows speech,
  web front-end verified live (web-20261031-231736: 12 selections in
  67 s, resub 284 px, leave-and-return robust in Tk runs). Settings
  (voice ES/EN by culture prefix, editable phrases) persist locally.
- **Desktop/Discord** (T29, stretch): built; live proof pending.

## 5. Limitations, stated plainly

- **n=1 participant** for all anchor and typing numbers; volunteer
  sessions are the missing evidence, and the protocol (EVAL.md) fixes
  the success criteria in advance, including reporting C < B if that
  is what replay shows.
- **Posture outside the enrollment family still breaks the base map**
  within a minute; semantic anchors correct bias, not a warped map.
  Head-frame transformation features were probed and rejected
  (invariance no better, worse pitch-down).
- **SAM is weak on UI text**; on free screens D underperforms C. The
  semantic lane currently earns its keep in controlled apps (exact
  anchors), not yet on arbitrary desktops.
- Degrees conversion uses estimated distance (~52 cm, face-width
  proxy); px is the primary unit throughout.
- Spark/SAM calls are cloud (Meta Model API); the gaze loop itself is
  fully local. Cost per 15-min session is bounded by anchor count
  (~30 Spark proposals); TODO: attach the exact token/spend log.

## 6. Reproduction

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests   # 163 tests
.\.venv\Scripts\python.exe app\beta.py                     # gaze keyboard (appearance default)
.\.venv\Scripts\python.exe app\board_web.py                # communication board (browser UI)
.\.venv\Scripts\python.exe tools\record_session.py --seconds 900 --camera 0 --monitor 1
.\.venv\Scripts\python.exe tools\replay_v2.py data\sess-YYYYMMDD-HHMMSS
.\.venv\Scripts\python.exe tools\t20_appearance.py
```

Data (`data/`), keys (`.env`), and eye crops are never committed; code
and protocols are. Protocol, decision log, and honest negative results:
`docs/EVAL.md`, `docs/DECISIONS.md`, `docs/RESEARCH.md`.

## References (verified, minimal)

- Engel et al. Project Aria. arXiv:2308.13561 (2023).
- Hou et al. Online-EYE. CHI 2025. doi:10.1145/3706598.3713461.
- GazeAgent. arXiv:2610.24364.
- facebookresearch/projectaria_tools; facebookresearch/projectaria_eyetracking. GitHub, reviewed Oct 31, 2026.
- WebGazer.js (click/mouse self-calibration baseline family).


