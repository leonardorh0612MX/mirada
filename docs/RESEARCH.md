# Research

Rule: a fact enters this file only with a source inspected in this project, or it is listed as an open unknown. Search snippets locate sources. They do not settle facts.

## Verified with sources

### WebGazer self-calibration

- WebGazer.js self-calibrates from clicks and cursor movements and needs no special hardware. Source: project site, https://webgazer.cs.brown.edu/
- A peer-reviewed summary states WebGazer continuously self-calibrates by assuming the user looks at mouse movement and click locations, and reports 4.17 degrees accuracy in a lab study (Papoutsaki et al., 2016). Source: https://link.springer.com/10.3758/s13428-022-02040-x?fromPaywallRec=false
- Implication: click-based recalibration (strategy B) is prior art, not our differentiator. Our claim must rest on semantic anchors beyond clicks, measured against B.

### Hackathon context

- The event provides Muse Spark series, Muse Wonder, Muse Image, and SAM 3.1 through the Meta Model API, plus Muse Spark open weights. Source: https://cerebralvalley.ai/e/meta-ai-developer-hackathon

### T3 result (Oct 27): MediaPipe 1.1.1 works at 28.7 fps

- Measured on the builder machine, 60 s, 640x480: 1780 frames, 28.7 fps, landmark presence 0.88, 478 landmarks per face (468 plus 10 iris).
- API note: `mp.solutions` no longer exists in 1.x. Product code must use `mediapipe.tasks.python.vision.FaceLandmarker` with a `.task` bundle (3670 KB, downloads on first run). Probe updated to the Tasks API.
- Verdict: the local gaze loop at camera rate is viable on CPU. Presence 0.88 means the validity-flag path in `gaze/` will trigger on roughly 1 in 8 frames. Design accordingly.
- Camera map (builder machine, Oct 27): index 0 is the Logitech above the monitor (use this). Index 1 is the integrated laptop camera. Index 2 is unknown, black frames, ignore. Product code must take the camera index as config, default 0. Never assume the default camera.
- Multi-monitor (Oct 27): the builder works on an external monitor, but T2 screenshots captured the laptop screen. PIL `ImageGrab.grab()` takes the primary display unless told otherwise. Anchor coordinates are meaningless if they live in the wrong screen's frame. v1 captures the demo app's own monitor or window only, never the blind default. Screen identity (which monitor, its offset in virtual pixels) is part of every screenshot's metadata from T10 on.

## GazeAgent and Project Aria review (Oct 28, sources read in full)

Sources: arXiv 2610.24364v1 HTML plus PDF (27 pp), Project Aria paper
arXiv 2308.13561v3, Aria MPS eye-gaze data-format docs
(facebookresearch.github.io/projectaria_tools/docs/data_formats/mps/mps_eye_gaze).
Local extracts in data/papers/.

### GazeAgent (Zhang et al., UCSD) - the closest prior art

- Setting: Aria AI glasses. Detects PVA (precise visual attention) events by
  multimodal agreement (IMU stillness, gaze stability, wearer-hand action).
  A LoRA-fine-tuned VLM validates each candidate and localizes the functional
  target ROI. Validated correspondences update calibration in batches of 4.
- Correction model: 6-parameter per-user affine online, plus a FIXED
  population nonlinear correction (25 Gaussian basis functions over the gaze
  field, learned offline, frozen during use). Fit by regularized IRLS with a
  2.5-degree Huber threshold. Evaluation is one-step-ahead (each batch scored
  with parameters fit on previous batches only).
- Anti-circularity by design: the validating VLM never sees the predicted
  gaze overlay when judging an event or localizing its target.
- Results (10-participant scripted study, 820 PVA opportunities): candidate
  recall 100%, VLM validation 95.9% recall / 92.3% precision. Median angular
  error: control 2.61 deg, under device disturbance 2.84 deg, vs explicit
  Aria calibration 3.51 -> 5.08 deg (44.1% lower) and general SocialEye
  4.96 -> 5.23 deg. Case study (n=5): lowest workload, all preferred it.
- Limitations they declare (our measured openings): (a) no controlled
  contamination test with incorrect pseudo-targets; Huber tolerance to false
  correspondences "remains unverified"; (b) no wall-clock update-latency
  measurement from event arrival rate; (c) AEA dataset plus scripted protocol
  only, no long deployments or diverse wearers; (d) no comparison against
  screen/interaction-based implicit calibration (different target
  availability); (e) localization reported separately from end-to-end
  event-to-update coverage.
- Stack required: dedicated inward eye cameras, IMU, hand tracking, a
  fine-tuned VLM. None of that exists on a commodity webcam/desktop.

### Project Aria / Meta MPS (how the platform owner does gaze)

- Output: yaw/pitch per eye (vergence) in the Central Pupil Frame plus depth
  (vergence intersection, capped 4 m) and confidence intervals,
  general_eye_gaze.csv / personalized_eye_gaze.csv, summary.json reporting
  Stage 1 (inference) and Stage 2 (in-session calibration) status.
- general = SocialEye, a ResNet-18 CNN over left/right eye crops trained on
  1,200+ individuals and ~2M Aria eye-camera frames. personalized = the same
  output corrected by 4-6 affine coefficients (scale/offset per axis, plus a
  diopter delta for depth) from an explicit in-session calibration.
- Meta's own uncertainty factors: blinking, hair occlusion, re-adjusting the
  glasses - the same adversaries we measured on webcam.
- Implication: Meta ships calibrate-once; nobody in this stack maintains
  calibration from use. GazeAgent maintains it on glasses with dedicated
  hardware. Mirada's claim is maintenance on commodity webcam for desktop
  accessibility, plus the corruption/gating measurements GazeAgent lists as
  future work.

### Borrowings adopted as tasks

- T27: fixed population residual (Gaussian-basis over the gaze field) learned
  offline from our pooled recorded sessions, frozen online; only the affine
  part adapts. Directly targets posture-warped maps that bias-only
  correction cannot fix.
- T28: replay update discipline - batch-of-4 one-step-ahead anchor updates
  with Huber IRLS, plus the corruption-rate ablation (gated vs forced vs
  consensus) GazeAgent declares unverified. We already have poisoned-anchor
  evidence (beta J selection) and forced/gated numbers on one session;
  T28 makes it systematic.

## GazeAgent reference review (Oct 28)

Read in full from primary sources (extracts in data/papers/refs/): Sugano
and Bulling 2015 (author PDF), Chen and Ji 2014 (RPI author PDF), Hou et al.
Online-EYE 2025 (CHI author PDF), Yang et al. vGaze (arXiv 2209.15196),
Liu et al. 2024 (Frontiers full text), Pani/Park/Peng 2025-26 (arXiv HTML,
abstracts plus structure). Secondary (abstracts plus converging citations):
Salvucci and Goldberg 2000, Pfeuffer et al. 2013, Neggers and Bekkering
2000, Drews and Dierkes 2024, Plopski et al. 2022. Skipped as non-actionable:
model cards, EEG methods, benchmark papers, neuroscience foundations.
Kothari Gaze-in-Wild and Wei et al. 2023 noted as T30 citation follow-ups.

Findings that change our work:

- Online-EYE (VR, UI-interaction anchors, live RLS with forgetting factor):
  independent convergence on our Corrector architecture. Key result:
  implicit matches explicit calibration INSIDE the convex hull of the
  interaction region (t=1.91, p=0.06, n.s.) and loses outside it; grand
  means implicit 3.08 deg vs explicit 1.19 deg. Actionable: trust gaze only
  inside the enrollment/anchor hull (coverage gate); explains why our beta
  works (keys are the covered region) and desktop fails at extremes.
- Sugano and Bulling 2015 (saliency self-calibration, HMD): drift measured
  on 20 users - 12 drifted, error 3.2 deg to 10.1 deg (max 40 deg), gradual
  constant-rate, caused by headset shifts. Saliency reaches
  calibrated-competitive accuracy given enough data but fails on scenes
  without salient objects. Our differentiator stands: task-relevant
  semantic anchors where saliency has nothing to lock onto (productivity
  screens). Their drift magnitudes are our comparison benchmark.
- Chen and Ji 2014 (calibration-free probabilistic 3D gaze, <3 deg):
  estimates kappa-parameter distributions from a gaze prior (saliency),
  fuses optical-axis likelihood with the prior into a gaze posterior,
  incrementally. Mirada reads as its online deterministic descendant with
  semantic anchors replacing the saliency prior and RLS replacing the DBN.
  Cite as the ancestor of prior-plus-axis fusion.
- vGaze 2021/22 (mobile, implicit saliency): opportunistic calibration only
  on "useful" frames (SCS spatial metric, threshold 0.6), recalibration
  TRIGGERED by detected head-movement (relative-position change), scene
  cuts as high-confidence moments. Errors 1.51cm (2.88 deg), 0.99cm with
  history, 0.57cm with indicator. Actionable: head-motion-triggered
  refit/reset from our nose/fw telemetry, same trigger philosophy.
- Liu et al. 2024 (VOG calibration review): calibrate FEW eye-invariant
  parameters, minimize calibration info, redundant convertible parameters
  hurt accuracy; invariant parameters survive head motion, 2D mapping
  coefficients do not. Literature confirmation of our BiasCorrector design
  (4 params) and of the identifiability finding (fixed scales plus ridge
  25, -58% replay). Also: convenient calibration methods rarely reach
  industry for lack of generality verification - matches our honest-limits
  framing.
- Salvucci and Goldberg 2000 (fixation taxonomy, via converging secondary
  sources): I-VT velocity threshold 30 deg/s; I-DT dispersion 0.5-1.0 deg
  with 100-200 ms minimum duration, D=(Xmax-Xmin)+(Ymax-Ymin). Our
  FixationBuffer uses frame counts only. Actionable: upgrade to real I-DT
  with degree-based thresholds (micro-task, proposed T31).
- Pfeuffer et al. 2013 (pursuit calibration, via secondary sources): sample
  only when eye-target movement correlation is high; interruption-tolerant;
  can calibrate without participant awareness; ~0.6 deg, competitive with
  9-point. Actionable: pursuit enrollment (follow a moving dot) as an
  alternative to static dots, with correlation as the quality gate.
- Neggers and Bekkering 2000: gaze is anchored to the target of an ongoing
  pointing movement. Theoretical support for click anchors (strategy B).
- Pani, Park, Peng (2025-26, gaze-VLM): evidence for the bidirectional
  gaze/attention-VLM relationship, no estimator math to borrow. Park
  (language-guided attention prediction) conceptually supports inferring
  attention from scene understanding, our anchor thesis.

## Prior art to position against

- WebGazer.js: browser webcam gaze with click/mouse self-calibration. Our baseline B.
- Saliency-based implicit calibration (research family, specific papers unverified): uses bottom-up visual saliency maps as calibration signal instead of explicit dots. Closest known ancestor to our approach. Difference to defend: saliency predicts what is eye-catching; our anchors predict what is task-relevant via a multimodal model plus interaction context, then localize it with segmentation. Verify before any public claim: find and read at least two papers in this family, record what signal they use, their reported error, and where semantic anchors would beat saliency (e.g. a plain text editor has no salient regions, but the caret is a perfect anchor).
- Positioning (project thesis, Oct 27): with Meta's own models, accessibility-grade gaze runs on commodity hardware anyone already owns. No Tobii, no headset, no new camera. Where saliency fails (low-salience productivity screens), semantic anchors win. Where saliency works, it becomes a cheap additional anchor source, not a rival.
- Apple Eye Tracking (iOS/iPadOS), Google Look to Speak, Windows Eye Control with Tobii hardware, OptiKey (open source): existence noted from the project brief. Capabilities and limits unverified in this repo. Researcher must verify before any comparative claim in the README or video.

## T1 result (Oct 27): Meta Model API contracts

Status: secondary-source consensus only. No official Meta doc was inspected in this session. Nothing below is build-grade truth. T2 smoke test confirms or corrects each line.

Consensus across independent secondary sources:

- Base URL: `https://api.meta.ai/v1`. Auth: Bearer [REDACTED] from `MODEL_API_KEY` env. Sources: https://shipwithmuse.live/blog/muse-spark-for-developers, https://www.promptfoo.dev/docs/providers/meta/, https://www.marktechpost.com/2026/07/09/meta-superintelligence-labs-releases-muse-spark-1-1/
- Three accepted formats: OpenAI Responses, Chat Completions, Anthropic Messages. Sources: https://shipwithmuse.live/blog/muse-developer-platform, https://www.digitalapplied.com/blog/meta-muse-spark-1-1-agentic-model-api-2026
- Model IDs: `muse-spark-1.3` for the chat/reasoning tier, `sam-3.1` for segmentation. Official docs live at muse.ai/platform or dev.meta.ai per secondary pointers. Not opened in-session.
- SAM 3.1 via Meta Model API currently accepts text prompts only, per https://learnopencv.com/sam-3-whats-new/. Interactive point/box refinement exists in the native research implementation (https://github.com/facebookresearch/sam3), not confirmed on the hosted API.
- Design consequence, Plausible: Spark must produce a text referring expression ("the blue Send button") plus an optional coarse box. SAM receives the text phrase. If SAM text-only fails on small UI, the fallback is Spark point directly, no refinement.

Minimal request drafts, to be confirmed by T2 execution (key from `.env`, one small screenshot):

```python
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key="...")
spark = client.chat.completions.create(model="muse-spark-1.3", messages=[...])
```

SAM request shape: unknown at request-schema level. T2 must try the Chat Completions image-plus-text form first and record the exact error or mask output. If the schema differs, update this section before any product code.

Official-doc check still owed: open muse.ai/platform and dev.meta.ai manually in a browser, confirm base URL, auth, model IDs, SAM prompt modes, and pricing. Until then, DECISIONS.md D3 stays Proposed.

### T2 status (Oct 27): blocked in this shell, handed to builder

- The sandboxed shell has no external network: `pypi.org` and `api.meta.ai` both time out, and `pip install` hangs indefinitely. The project `.venv` exists but has neither `openai` nor `pillow` (system Python has `pillow` only).
- The probe `tools/t2_smoke.py` is written and ready. It must run in the builder's own PowerShell, outside the sandbox:

```powershell
cd C:\Users\Leonardo.Rodriguez\mirada
.\.venv\Scripts\python.exe -m pip install openai pillow
.\.venv\Scripts\python.exe tools\t2_smoke.py
```

- Paste the full output back. Expected evidence: per-try lines for `spark_text`, `spark_vision`, `sam_call`, each with median/p95, plus sample outputs. Then T2 closes and D3 is confirmed or corrected.

### T2 results (Oct 27): Spark confirmed live, SAM needs Responses API

Measured on the builder machine, 10 tries each, screenshot 1280x800 (377 KB):

- `muse-spark-1.3` text-only: 10/10 ok. Median 0.70 s, p95 0.92 s, min 0.32 s, max 1.45 s.
- `muse-spark-1.3` screenshot plus text: 10/10 ok. Median 0.75 s, p95 1.40 s, min 0.61 s, max 1.41 s.
- Verdict: Spark latency fits the 3-5 s anchor cadence with wide margin. Base URL and Bearer auth confirmed by execution.
- `sam-3.1` via Chat Completions: 404, `The model sam-3.1 is not available on this endpoint. Use /v1/responses.` Vision cadence for SAM is unmeasured until the Responses shape is probed.
- Open issue: both Spark samples printed `None` content with `max_tokens` set. Possibly a reasoning-token or pagination detail of this endpoint. The follow-up probe `tools/t2_sam_responses.py` prints full output and token usage for SAM; the same check should be applied to Spark parsing before any product code (T11).
- Cost per call: still unmeasured. The follow-up prints `usage` when the API returns it.

### T2 follow-up (Oct 27): SAM via Responses, 5/5 ok but output empty

- `sam-3.1` via Responses API: 5/5 ok. Median 2.42 s, max 4.09 s, min 1.45 s.
- But `output_text` is empty and token usage reports zero, with `images_processed=1`. The mask or box lives in a field the probe did not read.
- Consequence: no more timed loops until the payload shape is known. `tools/t2_dump_shapes.py` makes one call per shape (Spark chat, Spark responses, SAM responses) and dumps the raw payload. Run that, read the fields, then resume timing with the correct parser.
- SAM latency note: median 2.42 s fits a 3-5 s cadence but barely. Live SAM leaves little margin. Replay-offline SAM stays on the table as fallback.

### T2 payload shapes (Oct 27): raw dumps decoded

- Spark via Chat Completions: works, but `finish_reason=length` with `content=null` at `max_tokens=100`. Reasoning consumed 98 of 100 tokens. The parser was never broken. The budget was. Product implication: Chat Completions needs a large token budget or it returns nothing.
- Spark via Responses API: correct path. `output[1]` message holds `output_text="ok"`. Usage reported honestly: 13 input, 61 output (51 reasoning). Decision: the product uses Responses API for Spark. Record in DECISIONS.md.
- SAM via Responses API: `status=completed`, `images_processed=1`, but the single output message has empty text and zero tokens. The mask or box is not in the conversational payload, at least not for a "return its bounding box" prompt.
- Two hypotheses, H1/H2. H1: SAM needs a different prompt contract (descriptive text works, geometry comes back another way). H2: the hosted endpoint does not expose geometry at all, and localization must come from open-weights SAM run locally or on Baseten. `tools/t2_sam_textprobe.py` tests H1 with one descriptive call. If output is still empty, H2 wins and D3 is redesigned around local SAM.

### T2 verdict (Oct 27, corrected by official docs): H2 wrong, hosted SAM viable

- Official docs inspected (primary sources, via direct fetch):
  - https://dev.meta.ai/docs/sam/segmenting — concept prompt is a short noun phrase. Commands ("segment the bus") and questions ("where is the bus?") are unreliable and often return nothing. One concept per request. Geometry streams as special-token text. Spark-then-SAM is the documented pattern: Spark captions, SAM segments.
  - https://dev.meta.ai/docs/sam/reading-segmentation — output is one `output_text` lane, one line per frame: `<Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;x=..;y=..;data=H,W,ENCPAYLOAD|>`. Single image emits frame `<0f>`. Stream with `stream=true`, accumulate `response.output_text.delta`, end on `response.completed`. Empty lane means zero matches, a normal result. Confidence field `c` appears only with `include_confidence`.
- This explains both empty results exactly: our prompts were instructions, which the docs say return nothing, and we did not stream.
- H2 falsified by documentation. New probe `tools/t2_sam_stream.py` tests the official contract: noun-phrase concepts, streamed, delta accumulation.

### T2 closed (Oct 27): SAM geometry confirmed live

- Concept `window`: 3.21 s, zero delta events, empty lane. Per docs, a normal zero-match result.
- Concept `button`: 1.72 s, one delta event, three objects with box plus mask tokens in the documented grammar, frame `<0f>`, coordinates in screenshot pixels (e.g. `x1=1169;y1=737;x2=1181;y2=749;w=1280;h=800`).
- The official contract is confirmed by execution. Parser grammar is fully specified, so T12 writes its own small parser. Third-party `meta-sam-parser` noted as candidate only.
- T11 live check (Oct 27): `anchors/spark.py` returned `('OPEN date cell for October 28', 0.55, 'key press means gaze on active editing caret')` on a real screenshot. JSON contract works. Note: the concept references the laptop screen, but the builder works on the external monitor. All product captures must target the working monitor (D9).
- Measured latencies: Spark vision median 0.75 s, SAM single concept 1.7-3.2 s. A Spark-plus-SAM anchor costs roughly 2.5-4 s. Live use fits a 3-5 s cadence at the slow end. Include `include_confidence` in T12 to get the `c` field for the confidence gate.
- T12 live decode (Oct 27): `decode_mask_to_raster` on a real lane gives a 39x16 raster, 559 px, centroid (19.0, 7.9) mask-local. Plus bounds offset (1177, 89) it lands within 1 px of the box centroid. Mask and box agree. Anchor point: mask centroid, box as fallback. `conf=None` in this lane: the confidence gate needs `include_confidence=true` in product calls.
- Earlier self-correction stands: T1's claim that the API "accepts text prompts only" (from a secondary source) was incomplete. Box and point prompts exist in the same token grammar for known locations, e.g. a click target or a box Spark already returned.

### First real session (Oct 27): base accuracy is the bottleneck

- Session `sess-20261027-141034`: 900 s, 12,610 gaze events, 9 calib samples, 1 dot. Strategy A error at the dot: 2009 px.
- Diagnosis: calibration fit error on its own training data is 388 px mean. Coefficients are huge (tens of thousands): features span ~0.1 across the full screen while session noise stdev is ~0.05. SNR around 2:1. The linear map amplifies noise into hundred-px errors.
- Consequence: no anchor strategy can be evaluated until the base map resolves screen regions. Anchors correct drift; they cannot fix a map that never worked.
- Fixes applied: camera request 1280x720 (logged per session, falls back silently), dot beep plus 10 s window (only 1 of 7 dots got confirmed while studying), dot positions cycle the 9-point grid.
- Next if resolution is not enough: head-pose features (nose displacement, face scale) as extra regressors, temporal smoothing, ridge toward sane gains, 16-point calibration. In that order.

### Gaze-during-blink (Oct 27): closed lids hallucinate, gate required

- 5 trials: open-phase error median 4536 px (probe's own 9-pt calibration, weak), closed-phase drift median 3298 px, peaks 9067-9621 px. Closed-eye landmarks produce confident garbage.
- Response: beta gates gaze on EAR (closed invalidates the frame, highlight holds). Probe upgraded to 16-pt calibration and in-dot instructions ("3/5 FIXATE") after builder feedback that top-bar text forces gaze away.
- Repeat runs (Oct 27): run 1 open 1532 px / closed 5772 px; run 2 open 453 px / closed 703 px. Two conclusions. One, closed always worse than open (1.6-3.8x): the EAR gate is mandatory, confirmed twice. Two, calibration repeatability across minutes is poor (3x spread): same user, same setup, different posture/attention per calibration. The corrector plus live anchors must absorb inter-calibration variance, not just slow drift.

### T22 first run (Oct 27): probe bug, plus a real finding

- First run median C error 881 px, but the probe hid the dot before screenshotting. Spark never saw the target. Fixed: capture while the dot is painted.
- Real finding anyway: on all 9 shots Spark locked onto the "white terminal cursor" behind the overlay. Plausible-but-wrong, consistently. This is the anchor-noise mechanism behind the weak C signal: Spark names a sensible element the user is probably not looking at.
- T22 fixed run (Oct 27): C median 56 px (mean 186, three bottom-row outliers 373-532 px), D median 1 px on 4/9 matches. On salient targets the anchor stack works: Spark ~56 px, SAM essentially exact when it matches (5/9 misses even here, concept-phrasing dependent). Bottom-row outliers unexplained: possible taskbar/edge confusion. Open: T22 measures dots, not real UI content. The UI-content precision run (fixate known labeled buttons) is still owed.
- UI run (Oct 27): C median 4 px, D 9/9 matched at median 1 px on labeled highlighted boxes. Caveat: best case (salient target plus label given in context). Proves localization is solved when identification is right. The frontier is target identification in dense UI without hints, where the terminal-cursor finding (plausible-but-wrong) still stands.

### First real A/C comparison (Oct 27): weak positive signal

- Session `sess-20261027-210940`: 29 C anchors, 5 D anchors, 7 dots. Strategy A mean error 1997 px.
- Residual-gate sweep on C: gate 150 px accepts 0/29 (1997 px); gate 500 accepts 4/29 (1953); gate 2000 accepts 28/29 (1693); forced all accepts 29/29 (1470 px, -26%).
- Reading: forced anchors reduce error monotonically, so they carry some signal. But 1470 px residual means anchor noise is large and the base map never got close. The gate-vs-map circular trap is confirmed: with a broken map, any fixed gate either rejects everything or accepts noise.
- Open question: what fraction is bad anchors vs bad map? Next measurement isolates anchor quality from gaze entirely: fixate known targets, screenshot, Spark/SAM, score distance to known position. See T22.

### SAM on UI text (Oct 27): concept matching fails, pivot to Spark points

- On 29 real productivity screenshots, Spark proposed sensible concepts ("text caret in the search box", "green Policy saved toast") but SAM matched 2/29. SAM 3.1 concept segmentation targets natural objects, not UI text elements.
- Pivot (kept honest): C anchors come from Spark-reported pixel points; D (SAM-refined) applies where matches exist. Spark's point precision becomes the measured quantity. OCR localization noted as the likely D-path for text-heavy screens.
- Recorder now logs left clicks for strategy B on future sessions.

### Offline anchor run (Oct 27): cost lesson on dead frames

- `gen_anchors` on 29 black shots spent 58 API calls to produce 0 anchors. Spark answered "blank black screen" (sometimes conf 0.95!), SAM returned no matches. Pipeline degrades correctly, but the calls were wasted money.
- Fix: `gen_anchors` now skips frames under mean brightness 5.0 with zero API calls. Also note: Spark self-confidence is unreliable ("blank black screen" at 0.95). SAM's no-match verdict is the real gate. The anchor ledger must require SAM confirmation, never Spark confidence alone.
- Full-screen-protected-video remains a suspected cause of black frames. Disambiguation confirmed Oct 27: full-virtual grab returns (3840, 1200) and shows both screens. The DPI-aware grab-plus-crop fix works.

### Averaged-capture session (Oct 27): calibration gate passed, drift is real

- Session `sess-20261027-193736`: calibration fit error 70.6 px mean (max 124.5), down from 350-455 px. The averaged-fixation protocol works. Fit gate (<150 px) passed.
- But dot errors stay 406-1489 px (mean 924), already high at the first dot (120 s). Not gradual drift: an immediate posture/context shift between calibration and studying. Exactly the failure mode semantic anchors exist to correct, once base fit exists.
- Gap found: screenshot events store only metadata, not image bytes. Offline anchor generation (Spark/SAM on session shots) is impossible on these sessions. Recorder now saves thumbnails. Next session doubles as the first offline-C/D dataset.

### Environment diagnostic (Oct 27): light is the dominant factor

- Measured while staring at center 15 s: brightness mean 31.8/255 (very dark), face width 261 px, eye width 54 px, landmark presence 1.00, per-feature noise stdev 0.02-0.05 against a ~0.1 signal range. No glasses, 50-60 cm distance (both fine).
- Interpretation: monitor glow alone is not enough illumination for stable iris landmarks. Every downstream number (fit error, dot error) is conditioned on this. Fix order: frontal light first (target brightness >80), then re-measure noise, then judge features.
- The averaged-fixation capture protocol (mean of ~40 frames per calibration point and dot) is deployed but untested. Averaging divides noise by ~6; combined with light it may rescue the linear map.

### Second session (Oct 27, 1280x720): hypothesis confirmed

- 7 dots logged, strategy A mean error 1181 px. Still unusable. Correlation of iris features with horizontal gaze across calibration targets: 0.11-0.40. Vertical: 0.74-0.76. The user turns their head toward targets; the iris stays near center.
- Response: features v2 adds head pose (nose displacement vs cheek box, yaw, pitch) for 8 features total. Calibration grid is 16 points. Recorder stores landmarks every 5th gaze event so future feature variants can be retrained offline without new sessions.
- If v2 still fails, the next lever is temporal smoothing plus ridge, then questioning whether this camera distance supports pixel-grade gaze at all.

## Open unknowns and how to resolve them

### Latency and cost

- Unknown: Spark and SAM round-trip latency on a real screenshot from this machine and network.
- Resolve: timed smoke test, 10 calls each, report median and p95. This decides live versus replay-only SAM (ARCHITECTURE.md risk 1).

### MediaPipe on Windows, Python 3.11

- Unknown: install health under `uv` on this machine, achievable frame rate, landmark stability on the project webcam.
- Secondary sources describe 478 landmarks including iris points. Treat as unverified until run locally.
- Resolve: minimal capture script, 60 s run, report fps and landmark presence rate. No architecture change until this number exists.

### Muse Code agent definition format

- Unknown: the exact discovery path and frontmatter schema Muse Code uses for subagent definitions in this version.
- Resolve: check Muse Code docs. Current files in `.agents/agents/` follow a conservative name/description/body convention. Update DECISIONS.md D8 with what the docs confirm.

## Novelty assessment, honest version

- Established: click/mouse self-calibration exists and works to a degree.
- Plausible differentiator: anchors from semantic context with no click, localized by segmentation, gated by confidence, evaluated against click recalibration on identical replayed data.
- Weakness to state openly: if semantic anchors only match strategy B, the contribution is an evaluation result, not a product advance. The eval is designed to reveal this either way.

### Project Aria tools (reviewed Oct 31)

- [projectaria_tools](https://github.com/facebookresearch/projectaria_tools/tree/main) is data plumbing, not an eye tracker: C++/Python toolkit reading Aria VRS recordings, device calibration and MPS outputs (eye gaze, hand tracking, SLAM). Install: `pip install projectaria-tools[all]`; loaders `projectaria_tools.core.mps.read_eyegaze` / `get_eyegaze_point_at_depth`. Actively maintained (2026 commits add Python 3.13/3.14 wheels and an Aria Gen2 ET CSV reader). ~858 stars.
- The gaze model itself is a separate repo: [projectaria_eyetracking](https://github.com/facebookresearch/projectaria_eyetracking) — PyTorch model trained on Aria's dedicated inward eye cameras, emitting `general_eye_gaze.csv` compatible with the tools API. Not usable from a webcam.
- Gaze representation: per-frame 3D ray anchored at the Central Pupil Frame, `yaw_rads_cpf` / `pitch_rads_cpf` / `depth_m` (vergence of left/right rays). Eye ray in head frame composed with device pose — same compositional structure as our T26 finding; validates reporting error in degrees, not only px.
- Personalization parallel (key for the paper): MPS emits `personalized_eye_gaze.csv` (same schema) only when the recording has in-session Eye Gaze Calibration. The correction is affine in angle space: `corrected_yaw = s_y*yaw + o_y`, `corrected_pitch = s_p*pitch + o_p` (six-coefficient variant: per-eye yaw scale/offset + shared pitch). Established, Meta-shipped precedent for a tiny affine corrector on a general gaze model — but theirs comes from an explicit calibration procedure, ours from continuous semantic anchors with no procedure at all.
- Not adoptable here: assumes Aria ET cameras + cloud MPS post-processing; nothing in the repo runs on webcam input in real time. Cite and contrast; do not integrate.
- Cheap borrow (Plausible): a scale+offset corrector variant in replay (Aria-style parameterization) vs our bias-only corrector. Untested; only if the schedule survives T20.
