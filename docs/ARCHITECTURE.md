# Architecture

## Thesis

Webcam gaze drifts. Manual recalibration breaks flow. Mirada corrects drift with sparse semantic anchors: moments where screen context makes the gaze target nearly certain.

A multimodal Meta model supplies labels. SAM 3.1 supplies geometry. Local math supplies the correction. The model is never in the fast loop.

Labels in this document: Established means supported by prior art or docs. Plausible means reasoned and testable. Speculative means interesting and unproven.

## Design principles

1. Two clocks, two rates. Fast local loop at camera rate. Slow semantic loop at event rate. They never block each other.
2. Replay first. Every live input is recorded with enough state to replay offline. All strategy comparison happens in replay.
3. Anchors are evidence, not truth. Each anchor carries confidence, provenance, and age. The corrector weighs evidence. It does not obey it.
4. Scarce labels, few parameters. Anchors arrive seconds apart. The correction model must stay identifiable from tens of anchors, not thousands.
5. Degrade, never die. SAM down falls back to Spark points. Spark down falls back to clicks. Clicks absent falls back to initial calibration.

## Modules

### gaze/

- Input: webcam frames.
- Job: face and iris landmarks to gaze features to a raw screen point.
- Local only. Target camera rate. No network.
- Output contract: timestamped feature vector plus raw point plus a validity flag. Invalid frames (no face, blink, extreme pose) are marked, never silently interpolated.
- Verification: landmark presence rate and raw error on calibration dots, offline from recordings.

### corrector/

- Input: feature vectors and accepted anchors.
- Job: map features to corrected screen points. Update online as anchors arrive.
- Model choice: regularized affine correction on top of the initial calibration mapping, updated by recursive least squares with a forgetting factor. Plausible. Rationale: six parameters stay stable with sparse anchors. A full feature regression is hungrier and overfits. See DECISIONS.md.
- Anchor gating, three checks in order:
  1. Confidence gate. Anchor confidence below threshold is discarded.
  2. Residual gate. Anchor far from current prediction is quarantined, not applied. Large residuals mean a bad anchor or a real jump. One anchor never decides.
  3. Age gate. Anchors expire. Stale evidence gets zero weight.
- Verification: replay with synthetic drift injected into recorded features. Recovery curve must beat no-correction on the same data.

### anchors/

- Input: screenshot, recent event window, app state (caret position, last click, focus).
- Job: produce anchors. An anchor is `{x, y, confidence, reason, source, t}` in screenshot pixels.
- Anchor sources in v1, in priority order:
  1. App events. Caret while typing and dwell or click targets emitted by the demo app itself. Exact coordinates. Established as high-precision while typing, to be confirmed by measurement.
  2. Spark proposal. Muse Spark sees screenshot plus event context and names the likely attended element. Coarse point. Plausible.
  3. SAM localization. SAM 3.1 segments the element Spark named. Anchor point becomes the mask centroid, constrained to the mask bounding box. Plausible. This is the precision layer.
- Fusion rule: app events outrank model output. SAM geometry outranks Spark points. Confidence combines source prior, Spark confidence, and SAM mask quality. Exact SAM scoring fields are unverified until docs are checked. See RESEARCH.md.
- Triggering: on app events first, periodic 3-5 s second. Never per frame.
- Failure rule: any timeout or error yields no anchor. Absence is safe. A wrong anchor is not.
- Verification: anchor precision on replay. Fraction of anchors within a pixel threshold of the dot ground truth or the known app event target.

### recorder/

- Input: everything. Landmarks, features, screenshots, mouse and keyboard events, raw gaze, corrected gaze, anchors, ground-truth dot fixations.
- Job: append-only timestamped log. One session, one directory, one manifest.
- Clock rule: monotonic timestamps order events. Wall-clock timestamps are display metadata only.
- Privacy rule: session data lives under `data/`, gitignored, never uploaded except explicit model calls during live anchoring.
- Verification: record a short session, replay it, assert event counts and ordering match.

### eval/

- Input: recorded sessions.
- Job: replay each session under strategies A-D and report honestly.
  - A: initial calibration only.
  - B: click and mouse recalibration, WebGazer-style.
  - C: semantic anchors from Spark.
  - D: C plus SAM localization.
- Output: error over time in px, cm, and degrees, drift slope, anchor precision, latency, and API cost per session.
- Conversion rule: cm and degrees derive only from screen geometry config. No hardcoded screen sizes.
- Verification: a synthetic session with known drift must rank strategies in the expected order.

### app/

- Job: gaze typing beta (D9). A big QWERTY keyboard on the working monitor. Gaze moves a highlight. Double blink selects. A double blink is two eye closures inside 600 ms after >= 200 ms open, with 800 ms debounce after every selection.
- The app emits its own caret and click events with exact coordinates. This is deliberate: v1 avoids global OS hooks for content, the most fragile layer on Windows. System-wide caret/click capture for study sessions is a separate path (recorder, Windows APIs).
- Tangible success test: type a preset phrase using only gaze plus double blink, <= 60 s, <= 2 wrong selections.
- The app also renders the ground-truth dot protocol and the session report.
- Verification: scripted session produces caret and click events at the rendered coordinates.

## Data flow

```text
webcam -> gaze/ -> features --+--> corrector/ -> corrected point -> app/
                              |         ^
events -> recorder/ ----------+         | accepted anchors
                              |         |
screenshot + context -> anchors/ (Spark -> SAM) -> anchor ledger -> gating
                              |
sessions -> eval/ (replay A/B/C/D) -> metrics + plots
```

Anchor ledger: anchors/ writes every proposed anchor, accepted or not, with its gate outcome. The ledger is the audit trail for anchor precision and the tuning set for thresholds.

## Interfaces

- All inter-module payloads are plain dicts serializable to JSON lines. One event per line in recorder output.
- Every payload carries `t_mono` (float seconds, monotonic) and `kind` (string).
- Coordinates are screenshot pixels unless the field name states otherwise (`_cm`, `_deg` only inside eval/).
- Model calls cross the boundary only in anchors/. No other module imports a model client. Keys come from environment only.

## Open architectural risks

- Spark and SAM latency on real screenshots is unmeasured. It decides whether SAM runs live or replay-only. Measurement is task 1 in TASKS.md.
- Segmentation quality on small UI elements is unknown. The demo app must use generously sized, high-contrast targets.
- The affine correction assumption may fail if drift is nonlinear. Replay with synthetic nonlinear drift tests this before any model upgrade.
