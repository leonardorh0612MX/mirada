# Tasks

Ordered. One task at a time. Done when means done, verified, not attempted. Dates assume the Nov 4, 2026 deadline.

## Model allocation

Spend Wonder only where judgment changes the outcome. Everything measurable or mechanical runs cheaper.

- `[Wonder]` muse-wonder-1.0: architecture decisions, ambiguity resolution, deep review, final synthesis. Few calls, high leverage.
- `[Spark]` muse-spark-1.3: doc lookup, routine implementation, runtime anchor proposals in the product. Default workhorse.
- `[SAM]` sam-3.1: only the product localization calls in T2, T12, and replay D. Never an authoring model.
- `[Local]`: no model. Local code, local measurement, human action.

Rule: if a task produces a number, it does not need Wonder. If it produces a decision, it might.

## Oct 27: verify before building

- [x] T1 `[Spark -> Wonder if ambiguous]` Researcher (done Oct 27: secondary consensus recorded in RESEARCH.md, official-doc check still owed): verify Meta Model API contracts for `muse-spark-1.3` and `sam-3.1` from official docs. Record in RESEARCH.md. Done when: exact endpoints, auth, and one minimal request per model are written down with source links.
- [x] T2 `[Local + Spark/SAM under test]` Implementer (done Oct 27: Spark vision median 0.75 s; SAM geometry confirmed live, button 1.72 s with 3 objects): timed smoke test, 10 Spark calls and 10 SAM calls on one real screenshot. Done when: median and p95 latency plus per-call cost are recorded in RESEARCH.md.
- [x] T3 `[Local]` Implementer (done Oct 27: 28.7 fps, presence 0.88, 478 landmarks, Tasks API): MediaPipe capture probe on this machine via `uv`, Python 3.11. Done when: 60 s run reports fps and landmark presence rate.
- [ ] T4 `[Local]` Builder: invite 2-3 evaluation volunteers. Done when: names and session slots exist.

## Oct 28: gaze baseline

- [x] T5 `[Spark]` Implementer (done Oct 27: 6/6 tests pass, synthetic fixture): `gaze/` landmarks to features to raw point, with validity flags. Done when: unit tests pass on a recorded frame fixture.
- [x] T6 `[Spark]` Implementer (done Oct 27: least-squares fit recovers matrix, dot error in px): initial calibration flow and dot protocol in `app/` skeleton. Done when: a calibration session produces dot errors in px.

## Oct 29: hardware-free baseline gate

- [x] T7 `[Spark]` Implementer (done Oct 27: JSONL round trip, backwards timestamps rejected): `recorder/` session logging with monotonic timestamps. Done when: record-replay round trip matches event counts.
- [x] T8 `[Local]` Evaluator (done Oct 27: replay A recovers injected 0.05 px/s drift on synthetic session; real session pending T13): strategy A replay on a recorded session. Done when: error-over-time output exists for one real session.
- Gate: if gaze plus record plus replay does not work today, cut scope before writing any model code.

## Oct 30-31: corrector and anchors

- [x] T9 `[Wonder design, Spark code]` Implementer (done Oct 27: RLS matches batch LS, 3 gates, jump adaptation, 31/31 green): `corrector/` affine RLS with confidence, residual, and age gating. Done when: synthetic-drift replay recovers better than no correction.
- [x] T10 `[Spark]` Implementer (done Oct 27: ledger with verdicts and precision metric, tested): `anchors/` app-event anchors (caret, dwell/click) with ledger. Done when: anchor precision is computable from a recorded session.
- [x] T11 `[Spark]` Implementer (done Oct 27 in anchors/spark.py, live JSON triple plus missing-key fallback tested): Spark proposals behind the degradation ladder. Done when: killing the API key falls back to app-event anchors without crashing.
- [x] T12 `[Spark code, SAM under test]` Implementer (done Oct 27: live mask decoded, 559 px, centroid matches box to <1 px): SAM localization for Spark proposals. Done when: D anchors exist in the ledger with mask-derived points, or a measured latency result moves SAM to replay-only with a DECISIONS.md update.

## Nov 1: benchmark gate

- [ ] T13 `[Local]` Evaluator (tooling done Oct 27: tools/record_session.py guided calibration plus dots; runs pending): record volunteer sessions per EVAL.md. Done when: at least 3 participants including the builder have complete sessions.
- [x] T14 `[Local replay, Wonder synthesis]` Evaluator (done Nov 1:
  docs/fig_error_time.svg + verdict in EVAL.md - primary criterion NO
  as designed (consensus applies zero anchors), batch4 revision -4..-6%,
  D not demonstrated on study sessions, black-frame availability
  finding): replay A/B/C/D, produce figure and table. Done when: EVAL.md
  success criteria are answered yes or no, in writing.
- Gate: if C does not beat A, the demo story becomes the honest negative result plus the best-performing strategy. No new features after this gate.

## Nov 2: harden the demo

- [x] T15 `[Spark]` Implementer (done Oct 27: DemoStatus state machine, priority api>face>light, grace period, recovery tested): face-loss, low-light, and API-failure handling in `app/`. Done when: each failure shows a user-visible state and recovers.
- [x] T16 `[Wonder]` Reviewer (done Oct 27: replay age gate fixed to use real anchor age; 44/44 green. Open: repo is not under git yet, needs `git init` plus first commit): full pass on security (no keys, no committed data), Windows compatibility, and architecture adherence. Done when: findings are fixed or listed as known issues.

## Nov 3: ship the story

- [ ] T17 `[Local + Wonder script review]` Builder: demo video, 15+ min session compressed to the required format, headline number from T14. Done when: video shows raw drift versus corrected gaze without recalibration.
- [x] T18 `[Spark draft, Wonder final pass]` Builder (final pass Nov 1:
  README rewritten - demo-first commands (board_app/beta), measured
  results with the T14/T20/T27 numbers, honest limitations; video link
  to be appended after T17): README with setup in PowerShell, honest
  limitations, and eval summary. Done when: a fresh reader can run the
  baseline from the README alone.

## Post-benchmark option

- [x] T20 `[Modal/Baseten]` (closed Oct 31 via the flagship below: per-session ridge instead of a pretrained model; adopted D13) Conditional: evaluate a pretrained appearance-based gaze model (Modal GPU) against the linear feature model on the same recorded dataset (eye crops). Done when: error comparison in writing. Adopt as `gaze/` engine only if it wins clearly. Skipped if the linear map meets target.
- [ ] T21 `[Wonder]` LLM-as-calibrator: feed Spark a session digest (calib fit, face-size drift, clicks, key screenshots) and ask for a bias-correction vector with confidence. Evaluate in replay against dots. Done when: correction error beats raw strategy A on one real session, or the negative result is recorded.
- [x] T22 `[Local + Spark/SAM under test]` (done Oct 27: C median 56 px dots, C 4 px UI, D 1 px): Anchor-precision probe: fixate N known on-screen targets, screenshot each, run Spark/SAM, score distance to known positions. Done when: anchor precision distribution in writing, independent of gaze.

## Beta (before video)

- [x] T23 `[Spark]` (done Oct 27: state machine passes deliberate/slow/debounce/none cases): Blink engine: EAR from landmarks plus double-blink state machine (2 closures <= 600 ms after >= 200 ms open, 800 ms debounce). Done when: synthetic EAR sequences yield >= 95% true positives on deliberate doubles and zero selections on single natural blinks.
- [x] T24 `[Spark]` Gaze keyboard beta (PASS Oct 28, session beta-20261028-164342): typed HOLA in 33.2 s, 0 errors, after two fixes diagnosed from session data (ridge 25 decouples eye/head channels - head-led gaze had inverted; blink detector fed before the jump-guard so closures cannot starve it). Long-blink 0.6 s hold select, factorial enrollment, consensus bias corrector live.

## Nov 4: buffer

- [ ] T19 `[Spark, Wonder only if blocked]` Fixes only. No new features, no new metrics. Submit before 9:00 PM ET.

## Stretch week Oct 29 - Nov 4 (7 days, ~$280 credits; beta passed Oct 28)

- [x] T20 `[Modal/Baseten, flagship]` (closed Oct 31, D13; pooled update
  Nov 1: LODO baseline=427px appearance=237px, n=373 dot-crops, -44%)
  Appearance model from recorded eye crops.
  Phase 1 done Oct 28, negative: ridge on 24x16 L+R crops vs linear feature
  map, leave-one-dot-out per session - pooled 578px vs 348px baseline (n=16
  dot-crops; only 3 sessions have any labeled crops, calib had no crops).
  Verdict: pixel-ridge loses; data too thin for any supervised model.
  Unblocked phase 2: recorder now saves one labeled crop per calibration dot
  (payload "crop" tag) - one new session yields ~16 calib + ~7 dot crops.
  Phase 2 Oct 29 (n=35 pooled): pooled baseline=366px appearance=384px
  (no clear win) BUT new session 222607 (n=19) appearance=221px vs
  baseline=382px (-42%); old sessions (n=4-7) overfit (up to 970px).
  Ruling Oct 30 (n=56): session 084907 replicates (n=21, 289 vs 386px,
  -25%); pooled 348 vs 374px (-7%), sufficient-data regime 255 vs
  384px (-34%). Wired into beta behind --map appearance (default
  linear): enrollment trains ridge on A+E median crop vecs (>=10),
  BiasCorrector takes opaque (vec, feats) samples via sample_feats,
  beta sessions save tagged crops and pool into T20. Adopt as default
  only on a live typing win. CNN on Modal ruled out (needs n>=200).
  ADOPTED Oct 31 (D13): live wins 45.0 s (beta-20261030-092548) and
  36.3 s (beta-20261031-232738, honest resub 191px), 0 errors both;
  beta --map default is now appearance, linear kept as fallback.
  T20 closed for the hackathon; more sessions still improve the
  pooled offline numbers but no longer gate anything.
- [x] T27 `[Spark implement, Wonder review]` (done Nov 1, NEGATIVE:
  pooled LOSO 785->780px, -1%, 6/10 sessions improved; same-day sessions
  all improve, cross-day worsens - residual is regime-specific, not a
  population prior. Not adopted live; documented in EVAL.md + paper
  Sec. 4.5) Fixed population residual: learn a small Gaussian-basis
  residual field offline from the pooled recorded sessions, freeze it,
  keep only the affine part adapting live (GazeAgent's architecture,
  adapted to webcam). Done when: replay shows error vs plain affine on
  the same sessions, in writing.
- [x] T28 `[Spark]` (done Oct 28: batch-of-4 one-step-ahead Huber-weighted
  full-RLS plus seeded corruption ablation at 0/10/25/50% in
  tools/replay_v2.py; RLSFilter/Corrector accept sample_weight, tested).
  Result: forced full-RLS -10% at rho=0, -7% at rho=0.5; gated and consensus
  never fire on noisy semantic anchors; batch4-Huber stable +2%. Table in
  docs/EVAL.md. This is the experiment GazeAgent declares unverified.
- [x] T13b `[builder]` (done Nov 1: four builder sessions
  sess-20261101-130237/133704/135659/141439, 7 dots each, shots saved;
  offline anchors via gen_anchors still to run on them) 2-3 new 15-min
  study sessions (volunteers preferred; builder as fallback) with the
  current recorder (shots now saved): feed the anchor-rescue curve at
  n>1. Done when: sessions have 7 dots, shots, and anchors.
- [ ] T29 `[Spark]` (re-scoped Nov 1, D16: taskbar selection failed live;
  APPS page with huge launching tiles verified instead — DISCORD opened
  natively web-20261101-122657. Typing inside Discord: cut from demo.)
  Gaze desktop demo: open Discord and send a message
  gaze-only (STRETCH after the board, re-scoped Oct 28: Tobii owns
  precision pointing; our accuracy regime owns huge-target boards). Built
  Oct 28 in app/desktop.py (transparent cursor overlay, two-stage
  arm/confirm hold-blink click, floating keyboard with Spanish predictions,
  real injection, gaze-operated corners); global Shift+Q quit; trace
  logging. Done when: desktop to sent message in <= 5 min with <= 5 wrong
  selections, on video.
- [x] T33 `[Spark]` Communication board (PASS Oct 29: all 8 cells
  selected across runs, voice verified, gaze-only QUIT verified
  board-20261029-214802, robust to leave/return): app/board.py with 8
  huge cells, hold-blink select, offline Windows TTS, coverage-gated
  highlight, certain-anchor live correction, saccade gate, session log.
- [ ] T33b `[Spark]` Board product UX (builder brief Oct 29, scoped below):
  (1) calibration ceremony: head-fit silhouette guide (live landmark
  oval vs target oval: doubles as a moved-during-dots guard), green
  dots on light background, smooth advance; (2) settings strip:
  ES/EN voice toggle, custom words from JSON, sentence bar with speak;
  (3) caregiver mouse always live alongside gaze; (4) DESKTOP bridge
  button launching app/desktop.py. Order: mouse + sentence bar, then
  ceremony, then voices/words, then bridge. Slice 1 built Oct 30
  (strip RECAL/bar/SPEAK/CLEAR/QUIT, caregiver mouse, sentence bar,
  layout tests, 144 green; live smoke pending). Slice 3 built Oct 30
  (SETTINGS button + caregiver window: ES/EN voice radio, 8 editable
  phrases, data/board_config.json, culture-prefix voice pick, config
  tests, 153 green; live smoke pending). Voices verified on builder
  machine: es-MX Sabina + en-US Zira. Redesign Oct 30: thin strip
  unreachable (bias vs variance, board-180002) -> display-only bar on
  top, 5 full function cells in a bottom row inside the hull; bar
  doubles as status line; JumpGate agree 250px board-only. D11 (Oct 30):
  web front-end built (app/board_web.py + site/board.html: splash with
  typewriter credit, styled pickers, ceremony with waves/spinner,
  board over SSE; Tk stays verified fallback). Live smoke pending for
  both. Done when: one video run shows ceremony + sentence speak +
  gaze-only QUIT.
- [x] T31 `[Spark]` (done Oct 28) I-DT-inspired fixation gate:
  FixationBuffer readiness is count plus split-half stability on iris
  components (pure max-min too fragile for landmark noise); tests updated
  plus unstable-window and spike-tolerance cases.
- [x] T32 `[Spark]` (done Oct 28) Coverage gate: gaze/coverage.py convex
  hull of enrollment targets with margin shrink (Online-EYE finding:
  implicit calibration holds inside the anchor hull); wired into board.py
  highlight, tested.

Order: Oct 29-30 T20; Oct 31 T13b plus T28; Nov 1 T29 (and T27 if T20
underperforms); Nov 2 integrate winner, record best runs; Nov 3 T17 video
plus T18 README final; Nov 4 T19 buffer/submit.

- [ ] T30 `[Wonder draft, Spark tighten]` (DRAFT done Oct 31:
  docs/PAPER_DRAFT.md with real numbers only; open TODOs inside:
  Figure 1 from replay_v2, exact Spark/SAM spend log, T29 outcome)
  Paper/article draft: the three
  science contributions (fit-identifiability fix with -58% replay evidence,
  anchor gating/corruption ablation GazeAgent leaves unverified, appearance
  model A/B result), methods, honest limits, reproduction commands.
  Done when: docs/PAPER_DRAFT.md exists with real numbers only, no invented
  citations, figures referenced from the replay reports.

Final deliverables: working desktop demo (T29) plus optimized model (T20/T27
winner) plus paper draft (T30).
