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
- Follow-up (same day): the first live run showed the failure this design feared - a camera that answers one frame and never streams kept its card on skeleton forever (add/drop/re-add loop). try_open_camera now requires 3 consecutive frames, dropped cameras quarantine 60 s before retry, and adds/drops print to the console. 208 tests OK.

## D27. Hot-plug goes manual: auto-add only + rescan button (Nov 3)

- Correction: the D26 auto-drop fired on its first real outing - the builder's working Logitech stuttered 4 preview reads while sibling cameras opened (routine DSHOW contention) and got dropped + quarantined 60 s, exactly the demo-killing flakiness quarantine was meant to tame. Per the builder's call, removal is no longer automatic: the /cameras poll only ADDS newly-plugged cameras, a failed preview read just serves 204 (card keeps its last frame), and a marble ⟳ button next to the Camera heading runs a manual rescan (POST rescan: prune_dead_caps with 3 read attempts per camera so stutter survives, then sync for newcomers, setup-phase only). Also silenced: the page cancels in-flight preview loads constantly, and each abort printed a ConnectionAbortedError traceback - all socket writes now go through a guarded _write.
- Status: Accepted, pending live. 212 tests OK (4 new: stutter-kept regression, dead-dropped, one-read healthy, mixed bag). Live check: setup shows all 3 cameras stable with no drops in the console; unplug one, hit ⟳, confirm it clears; plug it back, confirm it reappears.

## D28. Setup race, calib banner, tile pixels, cursor discipline (Nov 3)

- Correction (setup): the first D27 run printed `added idx=0` twice and the rescan briefly dropped the Logitech - the engine's startup scan filled PROBE_CAPS inline without the lock while the first /cameras auto-scan ran, opening devices twice and leaving stale handles. Startup now goes through the same additive sync_probe_caps under PROBE_LOCK; one handle per index, no phantoms.
- Correction (calib banner): busy=True wrapped the whole enrollment, so the footer read "fitting the map…" through all 43 dots and no instruction ever showed. busy now flips True only around fit_calibration; dots show their per-dot message, and the wording names the head explicitly ("move head AND eyes together" / "mueve cabeza Y ojos juntos", both UIs + fallback).
- Correction (tiles): two render bugs - RGB mode discarded the gloss/outline alphas (solid white, including the top-margin streak) and soft-alpha silhouette edges blended against the magenta label (pink fringe). render_tile draws on RGBA and flattens over exact magenta behind a thresholded hard edge; glassy inside, surgical outside.
- Choice (cursor): the system cursor used to teleport on every gaze click. click_at now saves/restores it in the same call - the gaze ring is the pointer, the caregiver's mouse never visibly moves. Dwell clicks also clamp to the monitor rect (one landed 74 px off-screen). MediaPipe landmarker closes explicitly (kills the __del__ teardown traceback).
- Status: Accepted, pending live. 216 tests OK (4 new: pink-fringe scan, 3 clamp). Live check: dots show instructions; YouTube tiles crisp with zero fringe; cursor stays put during dwell clicks; clean exit.

## D29. Atomic clicks, ring hunt, readable ghost (Nov 3)

- Correction: the D28 save/restore click still flickered (~0.1 s every few seconds in the live run) - three separate syscalls let the compositor paint the cursor mid-click. click_at now sends ONE SendInput batch (absolute-move to target, down, up, absolute-move back) with pixel->absolute conversion (to_absolute, tested); the cursor never visibly leaves its spot.
- Diagnosis: the builder saw no gaze ring inside YouTube, and the watcher swallowed every overlay exception. ring_draw failures now print once, and a 5 s heartbeat logs launched/gaze/ring-pixels/foreground-window while an app is open - the next live run will show whether the ring draws at sane coords (render/z-order bug) or never fires (state bug).
- Choice: tiles rest at 0.70 alpha (0.45 read as broken, not ghostly) and the splash types the contest line in English ("by Leonardo Rodríguez Hernández · for the Meta Global AI Hackathon").
- Correction: /cameras re-announced cameras after a full startup listing - the before-snapshot sat outside PROBE_LOCK and caught the startup fill mid-way. It moved inside.
- Status: Accepted, pending live. 218 tests OK (2 new: absolute corners/offset). Live check: YouTube clicks with zero cursor flicker; heartbeat lines show ring tracking gaze; ring visible or its first error printed.

## D30. Window placement, fresh-gaze dwell gate, spoken calibration (Nov 3)

- Diagnosis (ring): the heartbeat proved the ring draws at live gaze coords with zero errors - the builder simply couldn't see it because Edge opened YouTube on the laptop while the map aimed at the external monitor. Off-monitor gaze then stacked clamped clicks on the screen edge, and a lost face froze the ring while dwell fired twice on the dead centroid.
- Choice: 2 s after a launch, a daemon thread checks the foreground window - if its center is off the gaze monitor (and it's not Mirada itself), the window moves over and maximizes, with a console line either way. Untouched when already correct.
- Correction: dwell now fires only on fresh (face-this-frame), on-screen gaze; otherwise the ring hides (gaze=None) and AppDwell resets. Looking at the other monitor is silence, not edge clicks.
- Choice: calibration speaks each instruction on change (~7 utterances per enrollment, capture starts after the voice ends via speak_sync with a 12 s cap) - fixating users can't read the footer. Voice follows the session language.
- Status: Accepted, pending live. 221 tests OK (3 new: center-on-monitor). Live check: YouTube opens/moves to the gaze monitor maximized; look at the laptop (no clicks, ring hides); dots speak before capturing.
- Follow-up (same day): the builder corrected the diagnosis - YouTube HAD opened on the right monitor; the system cursor was parked on the laptop, so each click blinked there and back. The window-move stays as a guard (no-op when correct), and each launch now also parks the cursor on the gaze monitor once. The ring still draws error-free yet unseen, so the heartbeat now quotes Tk's own verdict (shown, viewable, geometry) - the next run ends the guessing.

## D31. Cursor parking + ring verdict telemetry (Nov 3)

- Choice: park_cursor moves the system cursor to the gaze-monitor centre once per launch when it rests elsewhere (gaze clicks restore wherever it was, which stranded all feedback on the laptop). Caregiver mouse stays live.
- Diagnosis: Overlay.ring_state exposes (shown, viewable, geometry); the 5 s heartbeat prints it as rs=. If Tk reports viewable at gaze coords and the builder still sees nothing, the fault is pixels/z-order, not state - and the fix will be a different renderer, not more Tk flags.
- Status: Accepted, pending live. 222 tests OK (1 new: point-in-monitor). Live check: launch YouTube with the cursor on the laptop (expect "cursor parked"); heartbeat rs= quotes the ring's real window state.

## D32. Ring drops the click-through flag, hides to click (Nov 3)

- Correction: the builder recalled the Discord-era cursor worked - and diffing it against today named the poison: desktop.py drew on a plain transparent window and withdrew it for each click, while the current ring sets WS_EX_TRANSPARENT via ctypes, the one structural difference on a window that draws error-free yet never paints on Win11. The flag is gone from _float; clicks pass by hiding the ring for their duration instead (RING_HIDE/RING_HIDDEN handshake: engine requests, watcher confirms within its 50 ms tick, 0.3 s cap so a stuck watcher can't hang the loop). Same recipe, proven on this machine.
- Status: Accepted, pending live. 222 tests OK (handshake is cross-thread, covered live). Live check: the yellow ring follows gaze inside YouTube on the chosen monitor; dwell clicks still land (ring blinks out for one frame per click).

## D33. Hold-to-click in apps, smooth ring, warm enrollment (Nov 3)

- Correction (Midas touch): the first visible-ring run fired 11 unintended dwell clicks reading YouTube - resting IS reading, so rest-to-click can never work there. App clicks now use the board grammar: look freely, CLOSE 0.4 s to click at the pre-closure gaze point (0.35 s back, clamped, dock corner excluded). The ring arc fills only while the eyes are actually closed (honest feedback). AppDwell stays tested-but-dormant as the instant fallback until after the video.
- Correction (ring quality): Tk canvas ovals alias ("pixelated"). The ring renders in PIL at 2x and downscales (render_ring, tested: shape, arc delta, no-fringe scan), shown on a Label like the tiles.
- Correction (cold enrollment): first attempts died at 446/366px while retries passed - capture started mid-motion after each spoken pose. Enrollment opens with one unrecorded centre dot (absorbs posture settling + voice surprise) and each new instruction gets 1.2 s to settle after the voice ends before capture.
- Status: Accepted, pending live. 224 tests OK (2 new: ring shape/arc). Live check: single enrollment passes first try; YouTube reads silently with zero clicks; a 0.4 s hold clicks exactly where you looked; smooth yellow ring throughout.

## D34. Enrollment that passes: full-body gate, replace-retry, honest warnings (Nov 3)

- Correction (smear): the stability gate watched iris dims only, so the head-follow style (eyes on the dot, head swinging) passed mid-motion samples and smeared two straight enrollments (390/446px). FixationBuffer gains opt-in gate_dims (board: all 7), average_stable (gated window only, not the 40-frame tail), and average_best (least-moving window); board waits 5 s per dot then falls back with a console line. Legacy average()/iris behavior untouched (research path + old tests green).
- Correction (retry): refit() now clears samples first - the old retry FIT 86 points (bad 43 + new 43) and "improved" 390 into 403. The retry also speaks guidance and rests 2.5 s first; a second failure accepts the map but warns LOUD (console + voice: settle, press R) instead of silently shipping 349px.
- Choice: enrollment wording asks for SMALL head motion ("move your head just a little" / "mueve la cabeza solo un poco") - the poses in block B already supply the designed variation; swinging in A/E only feeds the linear map nonlinearity it can't fit.
- Correction (hold-click aim): the click target is the median over open-eye gaze 0.45-0.9 s back, not one jittery past point.
- Status: Accepted, pending live. 227 tests OK (3 new: head-gate, stable/best windows). Live check: enrollment passes FIRST try under 300; dots print no "unsteady" lines; hold-clicks land on YouTube videos.

## D35. Dots that survive the user: retry, skip, tags (Nov 3)

- Correction: the 5 s dot cap aborted a whole session on dot 30 (chin-down pose lost the face, camera possibly stalled). A dot retries 3x now (voice coaches on the first miss, silent waits after), then skips - and 3 dead dots in a row aborts with "check the camera" instead of grinding 43 dots against dead hardware.
- Correction: skipped dots shift plan indices, so samples carry block tags (A/B/E) and the natural resub filters by tag instead of positional natural_block_indices (dropped from the engine import; the helper stays for research).
- Status: Accepted, pending live. 228 tests OK (1 new: best-None-when-starved). Live check: cover the camera on one dot (expect 3 tries + skip + session continues); enroll normally (expect first-try pass, tags invisible).

## D36. Instant voice + hold interstitial (Nov 3)

- Correction: each spoken instruction lagged ~2 s (a fresh PowerShell per utterance plus a voice-listing one on the first). Speech now runs through ONE persistent PowerShell (voice + text lines in, DONE out), prewarmed when the session language is known - per-utterance cost drops to the synth alone (~0.2 s). Any shell failure falls back to the old one-shot path, and two failures retire the shell for the session; worst case is today's latency, never silence.
- Choice: a holdinfo phase (one big marble line, EN/ES, spoken + shown 5 s) sits between enrollment and the board on the initial run only - the hold is the whole input grammar and was never taught on screen.
- Status: Accepted, pending live. 229 tests OK (1 new: utterance cleaning). Live check: first calib instruction speaks <1 s after its dot; holdinfo shows and speaks before the board; cell speech still works (same shell).

## D37. Clicks need VIRTUALDESK (Nov 3)

- Correction: every D29+ gaze click landed on the laptop while the ring aimed at the external monitor. SendInput absolute coordinates map to the PRIMARY monitor unless MOUSEEVENTF_VIRTUALDESK is set - one missing flag, total misdelivery on multi-monitor rigs. The D28 SetCursorPos path never had this bug (pixels are pixels); the atomic batch does. Fixed + flag-pinned by test.
- Note: this run also confirmed D34 (first-try enrollment 292/272px, zero unsteady dots) and D36 (no voice-lag complaint, 8 cells spoken). posture spread hit 0.45 yet resub passed - smear, not spread, was the killer; the guard threshold is permissive but the board ran great.
- Status: Accepted, pending live. 230 tests OK (1 new: desktop-mapping flags). Live check: hold-clicks land on YouTube videos on the gaze monitor (not the laptop).

## D38. Tile dwell hysteresis (Nov 3)

- Correction: the kb tile restarted its 0.8 s timer 7 times in a row - gaze jitter at the tile border flickered the raw zone in/out and each exit reset the timer, so only a perfect stillness (or the mouse) ever opened the keyboard. tile_dwell_next (pure, tested) adds entering grace 0.12 s and leaving grace 0.35 s around the 0.8 s fire.
- Open: gaze holds on the keyboard page didn't fire (mouse worked, phrase holds worked right after). Engine dispatch is source-blind, so the fault is upstream (hit-test vs trigger) - the session's trigger records will name it.
- Status: Accepted, pending live. 233 tests OK (3 new: dwell enter/fire, jitter-keeps-timer, leave-after-grace). Live check: tiles fire on a normal rest without stillborn "started" spam.

## D39. Dead camera announces itself and reopens (Nov 3)

- Correction: the camera died twice mid-session with zero console evidence - snap() conflated "no frames" (device) with "no face" (user). hud now carries frame_ok; ~90 dead frames prints CAMERA LOST + a session event + an on-screen message, and the engine reopens the index every ~450 frames until frames flow ("camera back"). Reopen is announced LOUD because a physical replug can reshuffle DSHOW indices onto the wrong camera.
- Note: same run confirmed D34 again (261/227 first try, no unsteady dots) and posture-return robustness (stood up, sat back, map held).
- Status: Accepted, pending live. 233 tests OK (loop behavior, covered live). Live check: unplug the camera mid-board (expect CAMERA LOST + message); replug (expect reopen + camera back).

## D40. Splash holds for a cue (Nov 4)

- Choice: the splash auto-advanced on a fixed 2.5 s timer, so narration couldn't pace it. It now waits for click/Space/Enter (hint fades in after the typewriter), with a 12 s auto-fallback so real users are never stranded. Demo direction: hold the logo through the opening line, advance mid-problem-beat.
- Status: Accepted, pending live. Page script node-checked. Live check: splash sits until clicked; hint appears; setup loads on advance.

