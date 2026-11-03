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

## D14. Demo hierarchy (Oct 31)

- Choice: the headline demo is the web communication board (proven live, voice output, accessibility story in 10 seconds). Second act: the gaze keyboard typing free text (appearance map). Discord (T29) is a bonus closing clip only if it passes its live test beforehand — never the main demo.
- Rationale: Discord rides the desktop cursor at 5-7 cm error with real-app injection unknowns; the board is verified end-to-end (web-20261031-231736) and the keyboard has two clean PASS runs. Judges get reliability first, ambition second, stretch last.
- Status: Accepted.

## D15. The board is also a native app window (Oct 31)

- Choice: `app/board_app.py` hosts the unchanged web UI and engine in a native pywebview window (Edge WebView2 on Windows 11) with the app icon (`site/mirada.ico`). It starts windowed (title bar, draggable, minimizable); when the user picks a monitor it moves onto that monitor and goes fullscreen there — calibration is only pixel-true when the page covers exactly the chosen screen (first live run opened on the other monitor and calibration followed the window, not the choice). F11 toggles fullscreen (page key → `/action fullscreen` → window); on session end it returns to a closable window. `app/board_web.py` (browser) and `app/board.py` (Tk) remain as fallbacks. A full Qt/QML rewrite was rejected for the hackathon window: days of rework and re-verification to reproduce a UI that already passes live, for zero engine gain.
- Rationale: the builder is right that quality design does not require a browser tab — but the design investment lives in the CSS/JS, and WebView2 renders exactly that inside a real application window. Packaging to .exe (PyInstaller) becomes possible later without touching the UI.
- Status: Accepted. Builder Nov 1: window opens natively; icon generated (`site/mirada.ico`) and wrapper tests pass; the wrong-monitor report motivated the move-to-chosen-monitor fix, whose live re-check is pending.

## D16. Apps open from gaze-sized tiles, not from the taskbar (Nov 1)

- Choice: T29 re-scoped again. Selecting Discord from the Windows taskbar failed live (desk-20261101-114853: 48 px icons vs ~280 px gaze scatter — the regime Tobii owns, not ours). The board gains an APPS page instead: huge tiles (DISCORD, NAVEGADOR, YOUTUBE, WHATSAPP, CORREO, MAPAS; editable in data/board_config.json) that launch apps via app/apps.py and minimize the board window. FRASES returns to the phrase page. Typing inside Discord after launch remains out of the demo; the launch itself is the verifiable outcome.
- Alternatives: keep desktop.py cursor for everything (rejected on live evidence); zoom-lens magnification for small targets (real work, unbudgeted before Nov 4); drop apps entirely (loses the "integrate my applications" story the builder asked for).
- Status: Accepted. First live run web-20261101-122657: DISCORD opened natively, phrases fine — but CORREO/YOUTUBE also fired because the engine kept selecting while the user was inside the opened app. Fixes same day: (1) gaze firing pauses entirely while an app is launched; (2) app tiles need a second confirming hold within 5 s (mouse click stays one-shot); (3) tiles carry brand badges; (4) a frameless always-on-top 210 px "← MIRADA" circle floats top-right (over the display-only bar) — gaze-dwell 0.9 s or caregiver click restores the board fullscreen. Re-verified web-20261101-185048: WHATSAPP and DISCORD launched, "returned to board" twice, settings voice logged Sabina.

## D17. Board enrollment becomes factorial (Nov 1)

- Choice: the web board's calibration replaces its flat 4x4 grid x2 with the beta's factorial plan (app/board.py enrollment_plan: A 3x3 natural + B 5 dots x 5 instructed poses + E repeat = 43 median captures, on-screen pose instructions). Trigger: web-20261101-185048 felt badly calibrated at resub 269 px - the board enrolled only natural-posture points while the keyboard enrolls gaze x posture. The builder independently proposed the same design (fingerprint-style multi-position capture); his spacebar trigger was not adopted (single frames are noisy; median-of-fixation is strictly better) and grid density was kept moderate (posture variety, not point count, is the measured bottleneck).
- Status: Accepted. Live check web-20261101-210049: single enrollment, natural resub 225 px. The weak-fit gate now judges natural blocks only (cross-pose resub ~305 px is legitimate and no longer re-enrolls).

## D18. Board anchors move bias only (Nov 1)

- Choice: on both board surfaces, certain (hold-confirmed) anchors update only the corrector's bias intercept - the head-coupled slope stays frozen, trust region tightens 25 -> 15 px, and residuals beyond 3 sigma are flagged instead of applied. Beta keeps full updates (its steering task measured well).
- Evidence: web-20261101-210049 - user reported selections progressively DE-calibrated the board; log shows 6 applied anchors with residuals 145-347 px that never shrank. Mechanism: each certain update also re-fit the head-coupled slope at whatever head pose the selection happened in, re-tilting the plane for every neighbour.
- Status: Accepted. Live check: residuals across selections should shrink or hold, never seesaw.

## D19. The board grows a keyboard page with send-to-app (Nov 1)

- Choice: TECLADO page in the board (Spanish QWERTY with Ñ, word suggestions, typed buffer in the bar) with VOLVER/DECIR/ENVIAR/QUIT. ENVIAR minimizes Mirada (the launched-pause machinery), waits 0.8 s, and injects text + {ENTER} into the focused window via the desktop demo's proven SendInput lane (app/inject.py). Text goes to whatever has focus - Discord's message box normally keeps focus; that caveat is stated, not hidden. DECIR speaks the buffer instead.
- Alternatives: gaze-typing directly inside the external app via the desktop cursor (rejected on the desk-20261101 evidence: fine targets are out of our regime); clipboard paste (SendInput Unicode already handles accents and was live-tested).
- Status: Accepted. Live check: type a short message, ENVIAR with Discord focused, confirm it lands; return via the floating circle.

## D20. Eye-mouse inside opened apps (Nov 1)

- Correction first: the builder's three "gaze returns" were mouse clicks - the dwell return never fired live and failed silently. The watcher now uses real elapsed time, prints dwell/restore diagnostics to the console, and reports window-call failures instead of swallowing them.
- Choice: while an app is open, the yellow ring follows the gaze over the app (small always-on-top window moved by the watcher), a deliberate 0.4 s hold clicks at the gaze point via SendInput (except over the floating buttons), and the floating window now carries two gaze targets: MIRADA (back) and TECLADO (opens the keyboard page). ENVIAR (D19) delivers the text into the focused field. This is the desktop interaction the builder asked for, built from board-grade pieces instead of the discarded fine-cursor demo.
- Status: Accepted. Live check: in Discord, gaze-click a channel, dwell TECLADO, type, ENVIAR, confirm the message; dwell MIRADA to return. Console must show the dwell lines.

## D21. App-mode dwell-click + head-follow calibration (Nov 1)

- Correction: the first D20 live run (web-20261101-230023) fired 11 clicks while the builder just looked around WhatsApp/Discord - blink-hold is the wrong gesture inside apps, where blinking is reading. Replaced with AppDwell: rest the gaze 0.9 s within 110 px to click, 1.5 s refractory. Blink stays only for board/keyboard cells.
- Correction: SPACE and hold selections died on the bottom row - downgaze-open eyes (~0.24 EAR) straddle the 0.6 x open-median threshold. Factor 0.52 (board + web); shut stays far below (~0.07-0.11 measured).
- Choice: calibration now instructs head-follow ("cabeza y ojos juntos"). The builder's best calibration ever came from pointing his head at the dots - natural gaze/posture covariation is the identifiability data the factorial design wants (§Q3), not noise to suppress. Block B keeps the explicit pose on top.
- Polish: floating dock and ring cursor restyled as dark glass (the flat circles read as cheap placeholders).
- Status: Accepted, pending live. 187 tests OK. Live check: open Discord, look around without intending clicks (expect zero `app click` lines), rest on a channel (expect one click), type via TECLADO with SPACE working.

## D22. English default + in-app dwell that survives jitter (Nov 2)

- Choice: the contest is judged in English, so the setup screen now opens with an EN/ES toggle (EN preselected, live preview) driving cells, funcs, default apps, phrases, TTS voice, enrollment cues and all chrome (new app/i18n.py + I18N dict in board.html, parity-checked both sides). Func dispatch matches stable ids, never display labels. Tk fallback takes --lang (default en). Settings can still switch the TTS voice mid-session, but never the session language.
- Correction: the WebView2 ring painted a white square despite transparent=True, so the in-app cursor is now a Tk overlay (Win32 -transparentcolor + click-through): guaranteed chromeless on any runtime. The dock window gets the missing transparent=True flag plus letterspaced-cap typography. If the dock still shows white live, it goes Tk too.
- Correction: resting on a target was near-impossible because the live point wanders - AppDwell now clicks on the rest centroid (running mean, radius 130 px), the engine smooths harder in app mode (alpha 0.15 vs 0.4), and the ring draws a white fill arc so the builder can see the charge and hold through it. Dwell 1.0 s, refractory 2.0 s.
- Status: Accepted, pending live. 196 tests OK, page script node-checked. Live check: setup shows EN default; open YouTube, confirm zero-background ring with charging arc; rest on a video (one click at the centroid); switch to ES once and confirm full translation.

## D23. Fusion: coarse labels + posture guardrail (Nov 2)

- Correction: the first volunteer session died from a poisoning spiral - a stuck highlight fired WATER 3x in 8 s, each "certain" anchor applied with 220-245 px residuals until bias hit 400 px and the board became unusable. Enrollment was healthy (steadier than the builder's), so the map was born fine and learned itself to death.
- Choice, three parts (corrector/fusion.py): (1) selections carry tile-size uncertainty (sigma_px = tile half-diagonal scales the RLS step: huge cells teach slowly, small keys faster; a 2-3 cm-off tile centre no longer jumps the map); (2) same-label gaze anchors cool down 2.5 s - speech still fires, only the teaching waits; (3) a PostureGuard freezes all anchor learning when live features drift beyond 3x the enrollment spread for 3 s, shows "you moved - press R", and resumes on return. Thresholds from real data (spread 0.157, freeze > 0.47: far above frame noise ~0.05).
- Also: sessions now log a setup event (camera, monitor, rect, lang) - the volunteer diagnosis needed it and meta was empty.
- Status: Accepted, pending live. 204 tests OK. Live check: hold one cell repeatedly (expect "cooldown" verdicts, map stays sane); lean far back for 4 s (expect freeze prompt + "posture drifted" console line); return (expect resume).

## D24. Baseten points are 0-1000 normalized, not pixels (Nov 2)

- Correction: the first Baseten anchor batches looked weak (off-screen points, replay C neutral). Overlaying the reported points on the volunteer screenshots showed concepts landing right but points systematically off - and rescaling by W/1000, H/1000 produced three exact bullseyes (taskbar clock, Firefox icon, cube centre). Spark Open ignores the "pixel coordinates" instruction; Meta Spark honors it. The Baseten path now rescales by true image size (mock-tested). Lesson: a new backend needs one visual overlay check before any replay verdict.
- Status: Accepted. 205 tests OK. Invalidates the "Baseten points are weak" reading of sess-20261102-163519 - both Baseten batches must be regenerated before judging.

## D25. Floating chrome goes full Tk: tiles + ghost fade (Nov 2)

- Correction: the dock's WebView2 window still painted a white slab despite every CSS/flag attempt, and it popped over launched apps intrusively. All floating chrome is now Tk: two PIL-rendered glass tiles as separate windows (the gap between them stays clickable), mouse bindings for the caregiver, gaze dwell zones from tile_rects. Render verified headless (rounded, transparent corners); Segoe UI lacks U+2301 so the keyboard tile carries no glyph.
- Choice: ghost fade - tiles rest at 0.45 alpha and solidify only when the gaze comes within ~260 px, so they sit over the app without covering it. Smaller too (2x 200x124 vs the 440x210 slab). Tiles exist only while an app is launched.
- Status: Accepted, pending live. 206 tests OK. Live check: open YouTube, confirm two floating glass tiles with zero white box, ghost at rest, solid on approach, MIRADA returns, TECLADO opens the keyboard.

## D26. Setup hot-plug: monitors + cameras appear live (Nov 2)

- Correction: a volunteer plugged a second monitor and a camera with Mirada already on the setup screen and saw nothing - devices were enumerated once at startup. Now /monitors re-reads every call (it already did), /cameras rescans indices 0-4 for new devices (throttled to 6 s, setup-phase only, additive under a lock the engine release shares), dead feeds drop after 4 consecutive read failures, and the setup page re-polls both lists every ~3 s and rebuilds only when the set changes (picks preserved, vanished picks cleared so Continue can't fire on a ghost device).
- Status: Accepted, pending live. 207 tests OK. Live check: open mirada.py, plug/unplug a USB camera on the setup screen, confirm the card appears/vanishes within ~6 s without restart.
