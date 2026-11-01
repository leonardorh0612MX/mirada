"""Gaze desktop demo (T29). Gaze cursor plus floating keyboard.

Flow: factorial-style enrollment (4x4 grid x2, averaged), then a transparent
overlay shows the gaze cursor on the real desktop. A 0.6 s eye-hold clicks
(in CURSOR mode) or selects a key (in KEYBOARD mode). Selections inject real
keystrokes/clicks into the focused app via app.inject. Keyboard auto-shows
when the foreground window title matches --app (default Discord); corner
buttons (RECAL / KB / QUIT) are gaze-operated since the overlay never takes
keyboard focus.
Usage: .\\.venv\\Scripts\\python.exe app\\desktop.py --monitor 1 --camera 0
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deskkeys import OSKEYS, bar_keys, label_to_tokens, place  # noqa: E402
from app.inject import (  # noqa: E402
    click_at,
    foreground_title,
    send_text,
    shift_q_pressed,
)
from app.keyboard_layout import hit_key, layout  # noqa: E402
from corrector.corrector import BiasCorrector  # noqa: E402
from gaze.blink import LongBlink, mean_ear  # noqa: E402
from gaze.calibration import fit_calibration  # noqa: E402
from gaze.clock import MonoClock  # noqa: E402
from gaze.features import extract_features, map_to_screen  # noqa: E402
from tools.env_check import estimate_distance_cm, light_label  # noqa: E402
from tools.record_session import (  # noqa: E402
    FixationBuffer,
    list_monitors,
    set_dpi_aware,
)

TRANSPARENT = "#0a0a0a"


def pose_hint(ref, nose, fw):
    """Where to move to match calibration pose. '' means aligned.

    Thresholds in face-width fractions: lateral/vertical 0.15, scale 0.12.
    (Same rule as app.beta; duplicated so the apps stay independent.)
    """
    if ref["nose"] is None or ref["fw"] is None or nose is None or not fw:
        return ""
    hints = []
    dx = (nose[0] - ref["nose"][0]) / ref["fw"]
    dy = (nose[1] - ref["nose"][1]) / ref["fw"]
    if dx > 0.15:
        hints.append("move RIGHT")
    elif dx < -0.15:
        hints.append("move LEFT")
    if dy > 0.15:
        hints.append("move DOWN")
    elif dy < -0.15:
        hints.append("move UP")
    if ref["fw"] and abs(fw - ref["fw"]) / ref["fw"] > 0.12:
        hints.append("move CLOSER" if fw < ref["fw"] else "move BACK")
    return " | ".join(hints)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--app", default="Discord",
                    help="auto-show keyboard when foreground title matches")
    args = ap.parse_args()
    set_dpi_aware()
    monitors = list_monitors()
    mleft, mtop, mw, mh = monitors[args.monitor]

    import tkinter as tk

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from recorder.session import append_event, new_session

    session = new_session(os.path.join(repo, "data"),
                          time.strftime("desk-%Y%m%d-%H%M%S"),
                          meta={"app": args.app})
    print(f"session: {session}")
    model_path = os.path.join(repo, "data", "face_landmarker.task")

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    base = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.geometry(f"{mw}x{mh}+{mleft}+{mtop}")
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#181818",
                       highlightthickness=0)
    canvas.pack()

    t0 = time.perf_counter()
    state = {"typed": "", "clicks": 0, "keys": 0, "corrections": 0,
             "started": None, "done": False, "mode": "CURSOR"}
    words = ["", "", ""]
    try:
        from app.words import load_words, suggest

        wordlist = load_words()
    except Exception:
        wordlist = []
        suggest = lambda prefix, words, k=3: []

    ear_gate = [None]

    def snap():
        ok, frame = cap.read()
        if not ok:
            return None, None, None, {}
        gray_mean = float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None, None, None, {"brightness": gray_mean}
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        ear = mean_ear(lms)
        face_px = lms[454][0] - lms[234][0]
        dist = estimate_distance_cm(face_px, w)
        hud = {"brightness": gray_mean, "distance_cm": dist}
        if ear is not None and ear_gate[0] is not None and ear < ear_gate[0]:
            feats = None
        return (feats if valid else None), ear, lms, hud

    print("CALIBRATION")
    calib = []
    ear_open = []
    ref_nose, ref_fw = [], []

    grid = [(mleft + mw * fx, mtop + mh * fy)
            for fy in (0.08, 0.36, 0.64, 0.92)
            for fx in (0.08, 0.36, 0.64, 0.92)]

    def calibrate():
        del calib[:], ear_open[:], ref_nose[:], ref_fw[:]
        total = len(grid) * 2
        done_n = 0
        for pass_no in (1, 2):
            for gx, gy in grid:
                fb = FixationBuffer(min_frames=12)
                done_n += 1
                while not fb.ready():
                    feats, ear, lms, _ = snap()
                    fb.add(feats)
                    if ear is not None:
                        ear_open.append(ear)
                    if lms is not None:
                        ref_nose.append(lms[1])
                        ref_fw.append(lms[454][0] - lms[234][0])
                    try:
                        canvas.delete("all")
                        canvas.create_oval(gx - mleft - 45, gy - mtop - 45,
                                           gx - mleft + 45, gy - mtop + 45,
                                           fill="#ffffff")
                        canvas.create_text(gx - mleft, gy - mtop,
                                           text=f"{done_n}/{total}",
                                           fill="#111111", font=("Arial", 16))
                        canvas.create_text(mw // 2, 28,
                                           text=f"Pass {pass_no}/2. Look at the dot...",
                                           fill="#ffffff", font=("Arial", 18))
                        root.update()
                    except Exception:
                        return
                calib.append((fb.average(), gx, gy,
                              "A" if pass_no == 1 else "E"))

    def refit():
        calibrate()
        if len(calib) < 16:
            raise ValueError(f"calibration interrupted ({len(calib)} samples)")
        for feats, gx, gy, block in calib:
            append_event(session, "calib",
                         {"features": feats, "target": [gx, gy],
                          "block": block})
        samples = [(feats, gx, gy) for feats, gx, gy, b in calib
                   if b in ("A", "E")]
        matrix = fit_calibration(samples)
        append_event(session, "calibration_matrix", {"matrix": matrix})
        means = [sum(s[0][j] for s in samples) / len(samples) for j in range(7)]
        return matrix, means, samples

    corrector = [None]
    pose_ref = [None]
    blink = [None]

    def refit_all():
        matrix, means, samples = refit()
        errs = []
        for feats, gx, gy in samples:
            px, py = map_to_screen(feats, matrix)
            errs.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
        err = sum(errs) / len(errs)
        print(f"calibration resub={err:.0f}px")
        append_event(session, "calibration_quality", {"resub_px": err})
        if corrector[0] is not None and err > 350:
            print("recalibration REJECTED - keeping old map")
            return
        if corrector[0] is None and err > 300 and not state.get("retried"):
            state["retried"] = True
            print("initial fit weak - hold still, enrolling again...")
            refit_all()
            return
        corrector[0] = BiasCorrector(lambda f: map_to_screen(f, matrix), means)
        ref_nose.sort()
        ref_fw.sort()
        pose_ref[0] = {"nose": ref_nose[len(ref_nose) // 2] if ref_nose else None,
                       "fw": ref_fw[len(ref_fw) // 2] if ref_fw else None}
        ear_open.sort()
        med = ear_open[len(ear_open) // 2] if ear_open else 0.30
        blink[0] = LongBlink(ear_threshold=min(0.25, max(0.12, med * 0.6)),
                             hold_s=0.6)
        ear_gate[0] = blink[0].ear_threshold
        state["enroll_thr"] = blink[0].ear_threshold
        print(f"EAR: open_median={med:.3f} threshold={blink[0].ear_threshold:.3f}")

    refit_all()

    # Geometry: corner buttons always live; keyboard floats in KEYBOARD mode.
    kb_h = int(mh * 0.52)
    kb_y = mh - kb_h - 8
    kb_keys = place(layout(mw - 16, kb_h), 8, kb_y)
    sug_keys = bar_keys(["", "", ""], 8, kb_y - 64, mw - 16, 52)
    os_keys = bar_keys(OSKEYS, 8, kb_y - 128, mw - 16, 52)
    corners = place([
        {"label": "RECAL", "rect": (0, 0, 150, 60)},
        {"label": "QUIT", "rect": (0, 0, 150, 60)},
        {"label": "KB", "rect": (0, 0, 150, 60)},
    ], 0, 0)
    corners[0]["rect"] = (8, 8, 158, 68)
    corners[1]["rect"] = (mw - 158, 8, mw - 8, 68)
    corners[2]["rect"] = (mw - 158, mh - 68, mw - 8, mh - 8)
    state["started"] = time.perf_counter()
    canvas.configure(bg=TRANSPARENT)
    root.attributes("-transparentcolor", TRANSPARENT)

    smooth = {"x": None, "y": None}
    last_hl = [None]
    kb_history = []
    smooth_history = []
    feat_history = []
    feat_window = []
    ear_open_ema = [None]

    def draw_live(hl, hud, hint):
        canvas.delete("all")
        if state["mode"] == "KEYBOARD":
            for k in kb_keys + os_keys:
                x1, y1, x2, y2 = k["rect"]
                active = k["label"] == hl
                canvas.create_rectangle(x1, y1, x2, y2,
                                        fill="#ffd54a" if active else "#2e2e2e",
                                        outline="#666666")
                canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                   text=k["label"],
                                   fill="#111111" if active else "#eeeeee",
                                   font=("Arial", 28))
            for k, w in zip(sug_keys, words):
                x1, y1, x2, y2 = k["rect"]
                active = w != "" and w == hl
                canvas.create_rectangle(x1, y1, x2, y2,
                                        fill="#7b1fa2" if active else "#4a4a4a",
                                        outline="#888888")
                canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=w,
                                   fill="#ffffff", font=("Arial", 22))
        else:
            if smooth["x"] is not None:
                cx, cy = smooth["x"] - mleft, smooth["y"] - mtop
                canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18,
                                   outline="#ffd54a", width=3)
                canvas.create_line(cx - 26, cy, cx + 26, cy, fill="#ffd54a")
                canvas.create_line(cx, cy - 26, cx, cy + 26, fill="#ffd54a")
        for k in corners:
            x1, y1, x2, y2 = k["rect"]
            active = k["label"] == hl
            canvas.create_rectangle(x1, y1, x2, y2,
                                    fill="#ffd54a" if active else "#333333",
                                    outline="#666666")
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=k["label"],
                               fill="#111111" if active else "#cccccc",
                               font=("Arial", 16))
        canvas.create_text(170, 40, text=f"[{state['mode']}] {state['typed'][-40:]}",
                           fill="#ffffff", font=("Arial", 18), anchor="w")
        if hint:
            canvas.create_text(mw // 2, mh - 100 if state["mode"] == "KEYBOARD"
                               else mh - 40, text=hint, fill="#ff8a65",
                               font=("Arial", 20))
        if time.perf_counter() < state.get("armed_until", 0):
            canvas.create_text(mw // 2, 80, text="CLICK ARMED - hold again",
                               fill="#ffd54a", font=("Arial", 24))
        root.update()

    def blind_click(x, y):
        # Our overlay is topmost: hide it for the click so the point lands
        # on the real app even where our own pixels are drawn.
        root.withdraw()
        root.update()
        time.sleep(0.05)
        click_at(x, y)
        time.sleep(0.05)
        root.deiconify()
        root.update()

    def loop():
        if state["done"]:
            return
        if state.get("calibrating"):
            root.after(100, loop)
            return
        feats, ear, lms, hud = snap()
        now = time.perf_counter()
        if shift_q_pressed():
            state["force_quit"] = True
        select_event = False
        if ear is not None:
            if ear > blink[0].ear_threshold:
                ear_open_ema[0] = ear if ear_open_ema[0] is None \
                    else 0.995 * ear_open_ema[0] + 0.005 * ear
                cap = state.get("enroll_thr", 0.19) * 1.1
                thr = min(cap, max(0.12, ear_open_ema[0] * 0.6))
                blink[0].ear_threshold = thr
                blink[0].open_threshold = thr * 1.25
                ear_gate[0] = thr
            select_event = blink[0].update(ear, now) == "select"
        hint = ""
        if lms is None:
            hint = "NO FACE - come back to the camera"
        else:
            hint = pose_hint(pose_ref[0], lms[1], lms[454][0] - lms[234][0])
        if feats is not None:
            feat_history.append((now, feats))
            while len(feat_history) > 120:
                feat_history.pop(0)
            feat_window.append(feats)
            while len(feat_window) > 7:
                feat_window.pop(0)
            avg = [sorted(f[j] for f in feat_window)[len(feat_window) // 2]
                   for j in range(len(feats))]
            px, py = corrector[0].predict(avg)
            # Never return early on jumps: a "select" verdict for this frame
            # would be dropped while the detector already fired (board-223131).
            jumped = (smooth["x"] is not None
                      and ((px - smooth["x"]) ** 2
                           + (py - smooth["y"]) ** 2) ** 0.5 > 400)
            if jumped:
                feat_window.pop()
            elif smooth["x"] is None:
                smooth.update(x=px, y=py)
            else:
                smooth["x"] = 0.4 * px + 0.6 * smooth["x"]
                smooth["y"] = 0.4 * py + 0.6 * smooth["y"]
            if smooth["x"] is not None:
                lx, ly = smooth["x"] - mleft, smooth["y"] - mtop
                # Frozen across invalid frames: closure must not erase the
                # highlight the hold is about to select (board-124331).
                last_hl[0] = hit_key(corners, lx, ly)
                if last_hl[0] is None and state["mode"] == "KEYBOARD":
                    sug_labels = [dict(k, label=w if w else "\x00")
                                  for k, w in zip(sug_keys, words)]
                    last_hl[0] = hit_key(kb_keys + os_keys + sug_labels,
                                         lx, ly)
                    if last_hl[0] == "\x00":
                        last_hl[0] = None
        hl = last_hl[0]
        smooth_history.append((now, smooth["x"], smooth["y"]))
        while len(smooth_history) > 120:
            smooth_history.pop(0)
        kb_history.append((now, hl))
        while len(kb_history) > 90:
            kb_history.pop(0)
        if args.app and args.app.lower() in foreground_title().lower():
            if state["mode"] != "KEYBOARD":
                state["mode"] = "KEYBOARD"
        if now - state.get("last_log", 0) > 0.5:
            state["last_log"] = now
            append_event(session, "trace",
                         {"gaze": [smooth["x"], smooth["y"]],
                          "mode": state["mode"], "hl": hl, "ear": ear,
                          "hint": hint, "window": foreground_title(),
                          "brightness": hud.get("brightness"),
                          "distance_cm": hud.get("distance_cm")})
        draw_live(hl, hud, hint)
        force_quit = state.pop("force_quit", False)
        if select_event or force_quit:
            past = [h for t, h in kb_history if t <= now - 0.45]
            target = "QUIT" if force_quit else (past[-1] if past else hl)
            if target == "QUIT":
                state["done"] = True
                secs = now - state["started"]
                print(f"done: typed={state['typed']!r} clicks={state['clicks']} "
                      f"keys={state['keys']} corrections={state['corrections']} "
                      f"secs={secs:.0f}")
                root.after(500, root.destroy)
                return
            if target == "RECAL":
                state["calibrating"] = True
                append_event(session, "recalibrate", {})
                try:
                    smooth.update(x=None, y=None)
                    canvas.configure(bg="#181818")
                    root.attributes("-transparentcolor", "")
                    refit_all()
                except Exception as e:
                    print(f"recalibrate aborted: {e}")
                canvas.configure(bg=TRANSPARENT)
                root.attributes("-transparentcolor", TRANSPARENT)
                state["calibrating"] = False
            elif target == "KB":
                state["mode"] = "CURSOR" if state["mode"] == "KEYBOARD" \
                    else "KEYBOARD"
            elif target is not None and state["mode"] == "KEYBOARD":
                tokens, state["typed"] = label_to_tokens(target, state["typed"])
                send_text(tokens)
                state["keys"] += 1
                if "BKSP" in tokens:
                    state["corrections"] += 1
                pre = [f for t, f in feat_history if t <= now - 0.7]
                anchor_feats = pre[-1] if pre else None
                verdict = "no_anchor"
                if anchor_feats is not None:
                    labeled = ([(k["label"], k["rect"]) for k in kb_keys + os_keys]
                               + [(w, k["rect"]) for k, w in zip(sug_keys, words)
                                  if w])
                    for label, rect in labeled:
                        if label == target:
                            x1, y1, x2, y2 = rect
                            cx = (x1 + x2) / 2 + mleft
                            cy = (y1 + y2) / 2 + mtop
                            stt, info = corrector[0].update(anchor_feats,
                                                             (cx, cy),
                                                             certain=True)
                            verdict = f"{stt}:{info.get('residual', 0):.0f}"
                            break
                append_event(session, "selection",
                             {"key": target, "typed": state["typed"],
                              "ear": ear, "anchor": verdict,
                              "window": foreground_title()})
            elif state["mode"] == "CURSOR":
                past_xy = [(x, y) for t, x, y in smooth_history
                           if t <= now - 0.7 and x is not None]
                if not past_xy:
                    root.after(33, loop)
                    return
                # Two-stage click: a lone 0.6s hold only arms (natural long
                # blinks reach 1.7s in our blink trials). A second hold
                # within 2.5s confirms. Desktop clicks must never be cheap.
                if now > state.get("armed_until", 0):
                    state["armed_until"] = now + 2.5
                    append_event(session, "arm", {"at": list(past_xy[-1])})
                    draw_live(hl, hud, hint)
                    root.after(33, loop)
                    return
                state["armed_until"] = 0
                cx, cy = past_xy[-1]
                blind_click(cx, cy)
                state["clicks"] += 1
                pre = [f for t, f in feat_history if t <= now - 0.7]
                anchor_feats = pre[-1] if pre else None
                verdict = "no_anchor"
                if anchor_feats is not None:
                    stt, info = corrector[0].update(anchor_feats, (cx, cy))
                    verdict = f"{stt}:{info.get('residual', 0):.0f}"
                append_event(session, "click",
                             {"at": [cx, cy], "ear": ear,
                              "anchor": verdict,
                              "window": foreground_title()})
        if state["mode"] == "KEYBOARD" and wordlist:
            from app.words import current_prefix

            words[:] = suggest(current_prefix(state["typed"]), wordlist, k=3)
            while len(words) < 3:
                words.append("")
        root.after(33, loop)

    root.after(33, loop)
    root.mainloop()
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
