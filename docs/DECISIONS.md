# Decisions

Format per decision: choice, alternatives, rationale, status. Status is Proposed until measured, Accepted after evidence.

## D1. Two-rate architecture, LLM never per frame

- Choice: local gaze loop at camera rate. Semantic loop event-triggered or every 3-5 s.
- Alternatives: per-frame model inference; fixed 1 Hz semantic polling.
- Rationale: latency and cost make per-frame inference infeasible. Fixed polling wastes calls when nothing changed. Events mark the moments of near-certain attention.
- Status: Accepted as principle. Rates to be tuned by measurement.

## D2. Correction model: regularized affine with recursive least squares

- Choice: affine correction (6 parameters) over the initial calibration map, RLS updates, forgetting factor, confidence-weighted anchors.
- Alternatives: full ridge regression from features; Kalman filter on gaze point; periodic full recalibration fits.
- Rationale: anchors are scarce. Six parameters stay identifiable from tens of anchors. Full regression overfits sparse noisy labels. A Kalman point tracker smooths but does not learn a feature mapping.
- Status: Proposed. Falsified or confirmed by synthetic-drift replay.

## D3. Hosted SAM 3.1 as localization layer (revised twice Oct 27)

- Choice: Spark names the attended element as a short noun phrase. Hosted `sam-3.1` segments it via the Responses API with `stream=true`. Geometry arrives as special-token text (`<0f>id<|box;...|><|mask;...|>`). Mask centroid is the anchor point.
- Revision history: v1 assumed hosted SAM exposes geometry conversationally. Two probes returned empty text, so v2 moved to open-weights SAM. Then official docs (dev.meta.ai/docs/sam/segmenting, reading-segmentation) showed the real contract: noun-phrase prompts, streamed deltas. The probes failed on contract, not on capability. v3 restores hosted SAM with the documented contract.
- Alternatives: Spark point only; OCR-first localization; open-weights SAM local or Baseten if hosted latency or quality fails measurement.
- Rationale: attention is a semantic judgment. Geometry is a measurement. The official Spark-then-SAM pattern matches this split exactly.
- Status: Accepted as contract. Streamed probe confirmed geometry live Oct 27. Latency and mask quality gate stays for T12.

## D4. v1 anchor sources: caret and click/dwell only

- Choice: app-emitted caret and click events first, model anchors second. Reading order and next-action prediction excluded from v1.
- Alternatives: all four anchor types from day one.
- Rationale: caret and click have verifiable ground truth inside the controlled app. Reading order anchors cannot be validated without extra instrumentation.
- Status: Accepted for v1. Reading anchors are a labeled Speculative extension.

## D5. Controlled demo app instead of full Windows desktop

- Choice: the demo app renders content and emits its own events. No global OS hooks in v1.
- Alternatives: global screenshot plus global input hooks across Windows.
- Rationale: global capture and hooks are the most fragile and privacy-sensitive layer on Windows. A controlled surface gives exact event coordinates and a recordable demo.
- Status: Accepted for v1.

## D6. Replay-first evaluation on identical sessions

- Choice: strategies A-D compared by replaying recorded sessions. Live A/B comparison is secondary.
- Alternatives: separate live sessions per strategy.
- Rationale: live sessions differ in user behavior and lighting. Replay holds data constant, so differences are attributable to strategy. This is the only honest comparison available to a solo builder.
- Status: Accepted.

## D7. Graceful degradation ladder D to C to B to A

- Choice: each layer falls back silently with a logged reason. The gaze loop never blocks on a model call.
- Alternatives: fail loudly and pause; retry until success.
- Rationale: an accessibility input method that freezes is worse than one that drifts. Fallbacks keep the demo alive under API failure.
- Status: Accepted.

## D8. Reserved: Responses API is the product path for Meta models

- Choice: all product model calls use the Responses API. Chat Completions measured correctly but wastes budget: 98 reasoning tokens of 100 left `content=null`.
- Evidence: T2 raw dumps, Oct 27. Spark Responses returned clean `output_text` with honest usage.
- Status: Accepted.

## D9. Tangible beta goal (Oct 27)

- Choice: the beta is a gaze keyboard. Big keys, gaze-highlighted, long-blink (0.6 s hold) to select. Tangible test: type a preset phrase using only gaze plus holds, <= 60 s, <= 2 wrong selections.
- Revision: double blink was first (user decision). Guided testing showed singles misfiring 5/5 because natural blinks pair inside any window. Long holds scored 14/15 with the only error a genuine 1.7 s closure during a natural trial. Switched on evidence.
- Rationale: judges and users need an outcome, not a plot. Typing is the canonical accessibility task, and a 0.6 s hold never collides with ~100 ms natural blinks. Caret and click anchors are emitted by this same app, so the demo doubles as the evaluation harness.
- Interaction rule: continuous closure >= 600 ms selects. Debounce 800 ms after every selection. Missing frames never count as closed.
- Status: Accepted as interaction. Beta run pending.

## D10. Screenshots carry screen identity; coordinates scale back exactly

- Choice: every captured frame records its source monitor, offset in virtual pixels, original size, and any downscale factor. Anchor points map back to full-resolution virtual pixels before entering the ledger.
- Rationale: T2 thumbnailed before sending, so SAM boxes lived in thumbnail space. Without the scale factor those boxes are decorative. Multi-monitor makes this worse: the wrong screen means the wrong frame entirely.
- Status: Accepted as rule. Enforced from T10 on.

## D11. Board presentation moves to a local web UI (Oct 30)

- Choice: the communication board gets a second front-end: a single-page web UI (splash, pickers, ceremony, board) served by a stdlib Python server on localhost with SSE state streaming. The Python engine (gaze, blink, corrector, speech, logging) is unchanged and shared. The Tkinter board stays as the verified fallback.
- Alternatives: keep polishing Tkinter canvas (rejected Oct 30: its ceiling is below the product's visual bar); PIL pre-rendered panels in canvas (better but slow and rigid); Blender-rendered intro (heavy for the remaining days).
- Rationale: the builder's Tkinter output reads dated next to big-tech references; the web stack already proved its ceiling on the landing page. CSS gives liquid motion, glass, and typography natively. Demo distribution also improves: judges open a URL.
- Status: Accepted. Live-verified web-20261031-231736: 12 selections in 67 s (incl. BAÑO), resub 284 px, settings save logged `voice=es active=Microsoft Sabina Desktop`. All 8 cells hit across web runs; Tk board remains fallback.

## D10. Agent definitions committed under .agents/, runtime state gitignored

- Choice: role definitions live in `.agents/agents/`. `.muse/` holds local runtime state and is gitignored per project spec.
- Alternatives: definitions inside `.muse/`; definitions only in AGENTS.md prose.
- Rationale: the team contract must be reviewable in version control. Runtime state must not be.
- Status: Proposed. Confirm Muse Code discovery path for agent definitions against current docs before relying on auto-loading. See RESEARCH.md open unknowns.

## D12. Head guide centers on the user's comfortable pose (Oct 31)

- Choice: the ceremony samples 1.6 s of natural sitting, takes the median (fx, fy, fw) as reference, and judges 'centered' relative to it (guide_reference/pose_inside). The web ellipse anchors to the bust face (50%/43% of stage, width 24% * fw/ref_fw) when the face is at that reference.
- Evidence: web-20261031-230837 — forcing camera-frame center (fw 0.22-0.48 zone vs natural ~0.20) made the user contort into unnatural positions to fit the statue.
- Rationale: the guide is a comfort check, not a measurement; frame center is a property of camera placement, not of the user's body.
- Status: Accepted. Live-verified web-20261031-231736: user sat naturally, no contorting reported ("esta muy bien").

## D13. Appearance map becomes the beta default (Oct 31)

- Choice: `app/beta.py --map` defaults to `appearance` (per-session ridge on eye-crop vectors); `--map linear` remains as the explicit fallback. The appearance model retrains from scratch every session on that session's A+E enrollment crops (>=10) — nothing persists or accumulates across sessions; only the offline T20 evaluation pool grows.
- Evidence: offline LODO ruling Oct 30 (sufficient-data regime 255 vs 384 px, -34%); live typing wins beta-20261030-092548 (45.0 s, 0 errors) and beta-20261031-232738 (36.3 s, 0 errors, honest LODO resub 191 px). The beta-20261030-093037 collapse predates the honest-LODO gate and the enrollment EAR-gate fix.
- Alternatives: keep linear default (rejected: loses where data is sufficient, and both post-fix live runs favor appearance); persist a cross-session model (rejected: per-session fit is the privacy and robustness story — a new user enrolls in ~90 s with no stored biometrics).
- Status: Accepted. Board (board.py/board_web.py) still runs the linear map; porting appearance there is a separate, later decision.
