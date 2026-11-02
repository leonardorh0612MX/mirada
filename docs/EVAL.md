# Evaluation

## Question

Do semantic anchors keep webcam gaze error lower over 15-20 minutes than initial calibration alone and than click-based recalibration, on identical data?

## Protocol

1. Session length: 15-20 min of mixed reading, typing, and dwell-click tasks in the demo app.
2. Ground truth: a fixation dot appears roughly every 2 min at a recorded position. The participant fixates it for about 1 s. Dot position and timing are logged by the app, not by hand.
3. Participants: the builder plus 5 volunteers (n=6). Two 15-20 min sessions per person when possible. Standard conditions for all: frontal light (target frame brightness >80), 50-70 cm from the screen, same protocol from docs/GUIA_PARTICIPANTE.md. Report per-participant results. Never pool silently across people.
4. Everything is recorded (recorder/). All strategies run in replay on the same sessions.
5. Conditions kept as constant as possible: same screen, same lighting note per session, same calibration at session start.

## Strategies

- A: initial calibration only. No updates.
- B: click and mouse recalibration, WebGazer-style. Anchor is the click point at click time.
- C: semantic anchors. App events plus Spark proposals.
- D: C plus SAM 3.1 localization. Anchor point is the mask centroid.

## Metrics

- Fixation error at each dot: px, cm, degrees. Primary number.
- Error over time: per-dot error plotted against session minute, per strategy.
- Drift slope: linear fit of error versus time, per strategy.
- Anchor precision: fraction of anchors within an agreed pixel threshold of the known target. Computed from the anchor ledger.
- Anchor harm rate: fraction of accepted anchors that increased error at the next dot. This metric exists to catch confident nonsense.
- Latency: median and p95 for Spark calls, SAM calls, and local loop frame time.
- Cost: API calls and estimated spend per session, per strategy.

## Success criteria, fixed in advance

- Primary: at minute 15, mean dot error for C is lower than A on the same sessions.
- Secondary: D beats C on anchor precision.
- Honesty clause: if C does not beat B, the headline result is that finding, reported plainly. No metric shopping after the fact.

## Threats to validity, stated now

- n is tiny. Results are a demonstration, not a population claim.
- The builder is also a participant. Expect optimistic bias in builder sessions. Volunteer sessions carry the claim.
- Controlled app, not the open desktop. Generalization beyond the app is unproven.
- Lighting and posture are noted, not controlled.

## Reporting

- One figure: error over time, four lines, all participants small-multiples.
- One table: mean final error, drift slope, cost per session, per strategy.
- Negative results in the same table, same font size.

## Results (Oct 28, builder sessions, replayed offline)

Five recorded 15-min sessions (7 ground-truth dots each), strategies replayed
on identical data with `tools/replay_v2.py`. A-refit = today's standardized
fit (fixed scales + ridge 25) on the stored calibration samples.

| Session | A-legacy | A-refit | Delta |
|---|---|---|---|
| sess-20261027-144550 | 1246px | 691px | -45% |
| sess-20261027-181528 | 1975px | 780px | -61% |
| sess-20261027-193736 | 659px | 400px | -39% |
| sess-20261027-203334 | 599px | 304px | -49% |
| sess-20261027-210940 | 1997px | 555px | -72% |
| **Mean** | **1295px** | **546px** | **-58%** |

Anchor strategies on sess-20261027-210940 (29 Spark anchors, 5 SAM anchors):

| Strategy | Mean error | Slope | Note |
|---|---|---|---|
| A-refit | 555px | +0.31 px/s | no anchors |
| C consensus/150px gate | 555px | +0.31 | zero anchors ever applied: circular gate trap, measured |
| C forced RLS p0=0.05 | 501px | +0.40 | -10% vs A-refit |
| C forced RLS p0=0.5 | 467px | +0.47 | -16%, slope worsens |
| D forced (SAM) | 568-631px | +0.30 | hurts: 5 sparse anchors |

Findings, honestly:

1. The largest measured gain is numerical, not semantic: standardizing the
   calibration fit (fixed physical scales, ridge 25) cuts error 58% on
   identical data. The Oct 27 fit solved unscaled normal equations whose
   coefficients reached +-55,000 and inverted under head-led gaze.
2. Semantic anchors help modestly (-10 to -16%) only when applied without a
   hard residual gate. Any gate calibrated to a healthy map rejects every
   anchor exactly when the map is broken (residuals 500-4000px vs 150px
   gate). Gating must be soft-weighted and consensus-based, and even then
   bias-only correction cannot fix a posture-warped map.
3. SAM-refined anchors (D) did not beat Spark points (C) on study screens:
   SAM segments natural objects, not UI text (5 usable anchors vs 29).
4. Live controlled-app result (the working configuration): gaze keyboard
   typed HOLA in 33.2s with 0 errors (session beta-20261028-164342), using
   exact key-centre anchors, human-in-the-loop steering, long-blink select.
5. Remaining limits: n=1 participant for anchors; posture change outside
   the enrollment family still breaks the base map within a minute;
   transformation-matrix head-frame features probed and rejected
   (invariance not better than image features, worse on pitch-down).

## T14 verdict (Nov 1): the pre-registered criteria, answered

Figure: docs/fig_error_time.svg (tools/t14_figure.py). Two anchor-bearing
sessions replayed identically (sess-20261027-210940: 29 C + 5 D anchors;
sess-20261030-084907: 29 C + 3 D, 34 clicks). Pooled over 14 dots:

| Strategy | Mean | Late (>=600 s) |
|---|---|---|
| A refit only | 490 px | 759 px |
| B click anchors (gated) | 490 px | 759 px |
| C Spark anchors, batch4-Huber | 469 px | 717 px |
| D SAM anchors (consensus) | 490 px | 759 px |

1. **Primary criterion (C beats A at minute 15): NO, as designed.** The
   pre-registered C (consensus corrector) applied zero anchors on both
   sessions; its series is identical to A. The gate trap of Oct 28 is
   the result, not an excuse.
2. **Revised discipline (post-hoc, labeled as such):** batch4-Huber C
   gives -4% pooled mean and -6% late-window (per session -2% and -7%).
   Modest and real; not a headline. B also never fired (gated corrector
   rejected the session's click anchors), so B = A here.
3. **Secondary (D beats C on anchor precision): NOT demonstrated** on
   study sessions (D = A; SAM produced only 3-5 anchors). It holds only
   in the controlled probe (D median 1 px vs C 4 px, tools/ui_precision).
4. **Availability finding:** the four Nov 1 study sessions (fullscreen
   video) have black screenshots and yielded 0-1 anchors total. The
   semantic lane requires capturable screen content; video-study is its
   blind spot, recorded plainly.

Gate consequence, per the rule fixed in advance: the demo story is the
honest version - fit identifiability (-58%) and appearance (-44%) carry
the science; semantic anchors contribute a measured -4..-7% in free
screens and exact, large corrections inside controlled apps.

## T28: update discipline and corruption ablation (Oct 28)

Batch-of-4 one-step-ahead Huber-weighted full-RLS updates (GazeAgent-style
protocol, adapted), plus the corruption experiment GazeAgent declares
unverified: seeded permutation of anchor positions at rates 0/10/25/50% on
sess-20261027-210940 (29 Spark anchors). Base A-refit = 555px.

| rho | gated 150px | forced full-RLS | consensus | batch4-Huber |
|---|---|---|---|---|
| 0.00 | 555 | 501 | 555 | 545 |
| 0.10 | 555 | 507 | 555 | 547 |
| 0.25 | 555 | 505 | 555 | 546 |
| 0.50 | 555 | 517 | 555 | 551 |

Reading: gated and consensus never fire on noisy semantic anchors (immune
but useless - they were designed for exact key-centre anchors). Forced
full-RLS extracts -10% at rho=0 and degrades gracefully to -7% at 50%
corruption. Batch4-Huber is a damped forced: +2% gain, flat under
corruption. Conclusion: with sparse noisy anchors, soft/no gating beats
hard gating; with exact anchors, consensus protects against poison (beta
HOLA run: single accidental anchors never moved the map).

## Factorial enrollment ablation (Nov 1)

tools/factorial_ablation.py: fit on block A only (9 natural dots) vs
A+B (34, with the 5-pose block), scored on block E (9 held-out repeats)
across the 18 sessions whose logs carry a full factorial plan.
Median held-out error: A-only 600 px, A+B 488 px (-19%); A+B wins
14/18. One A-only fit collapses entirely (6068 px, beta-20261028-160434)
where A+B stays at 555 px - the identifiability failure in miniature.
Caveats: E is minutes later in the same session (not cross-day), and
sessions with mid-session recalibration mix blocks; the median is
robust to both. Conclusion: the gain comes from posture coverage, not
point count - 43 points in one posture would plateau near 16.

## T27: population residual field (Nov 1, LOSO)

Gaussian-basis (kernel-ridge) residual field over the 7 geometric
features, trained on other sessions' dot residuals, tested on a held-out
session (tools/t27_residual.py; 10 sessions, 68 dots, sigma = median
pairwise distance, lambda = 1.0, single pre-set configuration):

Pooled LOSO: base 785 px -> corrected 780 px (-1%), 6/10 sessions
improved. The four Nov 1 sessions all improve (-27 to -223 px); the
Oct 27-30 sessions mostly worsen (+75 to +218 px). Reading: residual
structure is specific to the day's posture/lighting regime, not a
universal population prior - a frozen cross-day field does not transfer,
which is evidence FOR per-session enrollment plus an online corrector
rather than for a shipped population model. Verdict: do not adopt live;
keep as a documented negative result (docs/PAPER_DRAFT.md Sec. 4.4).
