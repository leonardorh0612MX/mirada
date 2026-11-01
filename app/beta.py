"""Gaze keyboard beta (T24). Working monitor, long-blink to type.

Flow: factorial enrollment (9 dots x 5 dots/5 poses x 9 dots, averaged),
then the keyboard. Gaze moves the highlight. 0.6s eye-hold selects; each
selection is a consensus-gated bias anchor for the live map.
Usage: .\\.venv\\Scripts\\python.exe app\\beta.py --monitor 1 --camera 0
Shift+Q or Esc exits.
"""

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camselect import resolve_camera, resolve_monitor
from app.keyboard_layout import hit_key, layout
from corrector.corrector import BiasCorrector
from tools.env_check import estimate_distance_cm, light_label
from gaze.appearance import ridge_fit, ridge_predict, vector_from_frame
from gaze.blink import LongBlink, mean_ear
from gaze.calibration import fit_calibration
from gaze.clock import MonoClock
from gaze.features import map_to_screen
from gaze.features import extract_features
from gaze.saccade import JumpGate
from tools.record_session import (FixationBuffer, list_monitors, save_eye_crops,
                                  set_dpi_aware)


def pose_hint(ref, nose, fw):
    """Where to move to match calibration pose. '' means aligned.

    Thresholds in face-width fractions: lateral/vertical 0.15, scale 0.12.
    """
    if ref["nose"] is None or ref["fw"] is None or nose is None or not fw:
        return ""
    hints = []
    # Camera is not mirrored: user's right is image-left. Nose image-x above
    # ref means the user drifted to their LEFT, so send them RIGHT.
    dx = (nose[0] - ref["nose"][0]) / ref["fw"]
    dy = (nose[1] - ref["nose"][1]) / ref["fw"]
    if dx > 0.15:
        hints.append("move RIGHT")
    elif dx < -0.15:
        hints.append("move LEFT")
    if dy > 0.15:
        hints.append("move UP")
    elif dy < -0.15:
        hints.append("move DOWN")
    if fw / ref["fw"] < 0.88:
        hints.append("move CLOSER")
    elif fw / ref["fw"] > 1.12:
        hints.append("move BACK")
    return " | ".join(hints)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=None)
    ap.add_argument("--camera", type=int, default=None)
    ap.add_argument("--target", default="HOLA")
    ap.add_argument("--map", choices=["linear", "appearance"],
                    default="appearance")
    args = ap.parse_args()
    set_dpi_aware()

    import cv2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import mediapipe as mp
    import tkinter as tk

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from recorder.session import append_event, new_session

    session = new_session(os.path.join(repo, "data"),
                          time.strftime("beta-%Y%m%d-%H%M%S"),
                          meta={"target": args.target})
    print(f"session: {session}")
    model_path = os.path.join(repo, "data", "face_landmarker.task")
    if not os.path.exists(model_path):
        print("missing model bundle. Run tools/t3_mediapipe_probe.py once first.")
        return 2
    monitors = list_monitors()
    print(f"monitors: {monitors}")
    mon = resolve_monitor(args.monitor)
    if mon is None:
        return 2
    if mon >= len(monitors):
        print(f"no monitor {mon}. Use one of 0..{len(monitors) - 1}.")
        return 2
    mleft, mtop, mw, mh = monitors[mon]
    cam = resolve_camera(args.camera)
    if cam is None:
        return 2

    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"no_camera: index {cam} did not open.")
        return 2
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
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#181818", highlightthickness=0)
    canvas.pack()

    t0 = time.perf_counter()
    state = {"typed": "", "errors": 0, "started": None, "done": False}

    ear_gate = [None]  # set after calibration: closed eyes invalidate gaze

    def snap():
        ok, frame = cap.read()
        if not ok:
            return None, None, None, {}, None, None
        gray_mean = float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None, None, None, {"brightness": gray_mean}, None, frame
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        ear = mean_ear(lms)
        face_px = lms[454][0] - lms[234][0]
        dist = estimate_distance_cm(face_px, w)
        hud = {"brightness": gray_mean, "distance_cm": dist}
        if ear is not None and ear_gate[0] is not None and ear < ear_gate[0]:
            feats = None  # closed lids hallucinate iris positions; gaze is void
        vec = vector_from_frame(frame, lms)
        if not valid or feats is None:
            vec = None
        return (feats if valid else None), ear, lms, hud, vec, frame

    def draw_dot(x, y, label):
        canvas.delete("all")
        canvas.create_oval(x - 45, y - 45, x + 45, y + 45, fill="#ffffff")
        canvas.create_text(mw // 2, 28, text=label, fill="#ffffff",
                           font=("Arial", 18))
        root.update()

    print("CALIBRATION")
    calib = []
    ear_open = []
    ref_nose, ref_fw = [], []

    POSES = ["Head CENTRED", "Turn head LEFT, eyes on the dot",
             "Turn head RIGHT, eyes on the dot", "Tilt head UP, eyes on the dot",
             "Tilt head DOWN, eyes on the dot"]
    DOTS9 = [(mleft + mw * fx, mtop + mh * fy)
             for fy in (0.08, 0.36, 0.64, 0.92) for fx in (0.08, 0.36, 0.64, 0.92)]
    DOTS5 = [(mleft + mw * 0.5, mtop + mh * 0.5),
             (mleft + mw * 0.2, mtop + mh * 0.2), (mleft + mw * 0.8, mtop + mh * 0.2),
             (mleft + mw * 0.2, mtop + mh * 0.8), (mleft + mw * 0.8, mtop + mh * 0.8)]

    def calibrate():
        """Factorial enrollment (Q3): gaze x posture vary independently.

        A: 9 dots head-centred. B: 5 dots x 5 head poses, gaze locked.
        E: A repeated (drift check + more samples). ~43 averaged points.
        """
        del calib[:], ear_open[:], ref_nose[:], ref_fw[:]
        # Gate off during enrollment: eyes are open by instruction, and a
        # stale gate from the previous fit nulls the extreme-row dots where
        # downgaze physiologically narrows the eyes (beta-093037: stalled
        # dots -> marginal enrollment -> 1127px residuals). refit_all sets
        # the fresh gate afterwards.
        ear_gate[0] = None
        state["enroll_n"] = state.get("enroll_n", 0) + 1
        plan = [("A", gx, gy, POSES[0]) for gx, gy in DOTS9]
        plan += [("B", gx, gy, pose) for pose in POSES for gx, gy in DOTS5]
        plan += [("E", gx, gy, POSES[0]) for gx, gy in DOTS9]
        total = len(plan)
        for done_n, (block, gx, gy, pose) in enumerate(plan, 1):
            fb = FixationBuffer(min_frames=12)
            vecs, last = [], (None, None)
            while not fb.ready():
                feats, ear, lms, _, vec, frame = snap()
                fb.add(feats)
                if vec is not None:
                    vecs.append(vec)
                if frame is not None and lms is not None:
                    last = (frame, lms)
                if ear is not None:
                    ear_open.append(ear)
                if lms is not None:
                    ref_nose.append(lms[1])
                    ref_fw.append(lms[454][0] - lms[234][0])
                try:
                    canvas.delete("all")
                    canvas.create_oval(gx - mleft - 45, gy - mtop - 45,
                                       gx - mleft + 45, gy - mtop + 45, fill="#ffffff")
                    canvas.create_text(gx - mleft, gy - mtop,
                                       text=f"{done_n}/{total}", fill="#111111",
                                       font=("Arial", 16))
                    canvas.create_text(mw // 2, 28, text=pose,
                                       fill="#ffffff", font=("Arial", 18))
                    root.update()
                except Exception:
                    return
            vmed = (np.median(vecs, axis=0).tolist()
                    if vecs else None)
            tag = None
            if last[0] is not None:
                tag = f"e{state['enroll_n']}b{done_n:03d}"
                save_eye_crops(session, tag, last[0], last[1])
            calib.append((fb.average(), gx, gy, block, vmed, tag))

    def refit():
        calibrate()
        if len(calib) < 16:
            raise ValueError(f"calibration interrupted ({len(calib)} samples)")
        for feats, gx, gy, block, _vmed, tag in calib:
            append_event(session, "calib",
                         {"features": feats, "target": [gx, gy],
                          "block": block, "crop": tag})
        # Base map: linear on centred blocks only. Factorial (B) samples
        # measurably hurt centred accuracy (beta-140145: 333 vs 270px) and
        # typing happens at natural posture; B stays logged for offline
        # analysis. Posture drift online is the BiasCorrector's job.
        samples = [(feats, gx, gy) for feats, gx, gy, block, _v, _t in calib
                   if block in ("A", "E")]
        matrix = fit_calibration(samples)
        append_event(session, "calibration_matrix", {"matrix": matrix})
        means = [sum(s[0][j] for s in samples) / len(samples) for j in range(7)]
        atrain = [(v, gx, gy)
                  for _f, gx, gy, block, v, _t in calib
                  if block in ("A", "E") and v is not None]
        app_model = None
        if len(atrain) >= 10:
            X = np.array([v for v, _, _ in atrain])
            Y = np.array([[x, y] for _, x, y in atrain])
            app_model = ridge_fit(X, Y)
        return matrix, means, samples, app_model, atrain

    corrector = [None]
    pose_ref = [None]
    blink = [None]

    def refit_all():
        matrix, means, samples, app_model, atrain = refit()
        use_app = args.map == "appearance" and app_model is not None
        if args.map == "appearance" and app_model is None:
            print("appearance unavailable (<10 crops) - falling back to linear")
        errs = []
        if use_app:
            # Honest resub: leave-one-dot-out over the 34 enrollment
            # samples (train resub ~40px is meaningless for ridge and let a
            # garbage map through in beta-093037). ~34 fast fits.
            X = np.array([v for v, _, _ in atrain])
            Y = np.array([[x, y] for _, x, y in atrain])
            for i in range(len(atrain)):
                m = ridge_fit(np.delete(X, i, axis=0), np.delete(Y, i, axis=0))
                px, py = ridge_predict(X[i][None, :], m)[0]
                gx, gy = atrain[i][1], atrain[i][2]
                errs.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
        else:
            for feats, gx, gy in samples:
                px, py = map_to_screen(feats, matrix)
                errs.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
        err = sum(errs) / len(errs)
        map_name = "appearance" if use_app else "linear"
        print(f"calibration resub={err:.0f}px map={map_name}")
        append_event(session, "calibration_quality",
                     {"resub_px": err, "map": map_name})
        if corrector[0] is not None and err > 350:
            print("recalibration REJECTED (moved during dots?) - keeping old map")
            return
        if corrector[0] is None and err > 300 and not state.get("retried"):
            state["retried"] = True
            print("initial fit weak - hold still, enrolling again...")
            refit_all()
            return
        state["use_app"] = use_app
        if use_app:
            corrector[0] = BiasCorrector(
                lambda s: tuple(ridge_predict(np.array([s[0]]), app_model)[0]),
                means, sample_feats=lambda s: s[1])
        else:
            corrector[0] = BiasCorrector(lambda f: map_to_screen(f, matrix),
                                         means)
        ref_nose.sort()
        ref_fw.sort()
        pose_ref[0] = {"nose": ref_nose[len(ref_nose) // 2] if ref_nose else None,
                       "fw": ref_fw[len(ref_fw) // 2] if ref_fw else None}
        ear_open.sort()
        med = ear_open[len(ear_open) // 2] if ear_open else 0.30
        # 0.5 s: the board ear tape shows deliberate holds at 0.4-1.0 s
        # (0.6 s ate several) while true naturals stay <=0.2 s.
        blink[0] = LongBlink(ear_threshold=min(0.25, max(0.12, med * 0.6)), hold_s=0.5)
        ear_gate[0] = blink[0].ear_threshold
        state["enroll_thr"] = blink[0].ear_threshold
        print(f"EAR: open_median={med:.3f} threshold={blink[0].ear_threshold:.3f}")

    refit_all()
    keys = layout(mw, mh)
    state["started"] = time.perf_counter()

    def draw_keyboard(hl, hud=None, hint=""):
        canvas.delete("all")
        for k in keys:
            x1, y1, x2, y2 = k["rect"]
            active = k["label"] == hl
            canvas.create_rectangle(x1, y1, x2, y2,
                                    fill="#ffd54a" if active else "#2e2e2e",
                                    outline="#666666")
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=k["label"],
                               fill="#111111" if active else "#eeeeee",
                               font=("Arial", 30))
        canvas.create_text(mw // 2, 30,
                           text=f"Type: {args.target}    Got: {state['typed']}",
                           fill="#ffffff", font=("Arial", 20))
        if hud:
            b = hud.get("brightness")
            d = hud.get("distance_cm")
            hud_text = ""
            if b is not None:
                hud_text += f"light {b:.0f}/255 ({light_label(b)})  "
            if d:
                hud_text += f"dist ~{d:.0f}cm"
            canvas.create_text(mw - 10, 30, text=hud_text, fill="#9e9e9e",
                               font=("Arial", 14), anchor="e")
        if hint:
            canvas.create_rectangle(mw // 2 - 260, mh - 90, mw // 2 + 260,
                                    mh - 40, fill="#7b1fa2", outline="")
            canvas.create_text(mw // 2, mh - 65, text=hint, fill="#ffffff",
                               font=("Arial", 20))
        root.update()

    smooth = {"x": None, "y": None}
    gate = JumpGate()
    last_hl = [None]
    hl_history = []  # (t_mono, highlight): selection uses pre-blink target
    last_feats = [None]
    feat_history = []  # (t_mono, feats): anchors need pre-closure features
    feat_window = []  # rolling mean over live features kills single-frame jitter
    last_vec = [None]
    vec_history = []  # (t_mono, crop vec): appearance-mode anchors
    vec_window = []  # median over live crop vecs, same anti-spike role
    ear_open_ema = [None]  # slow tracker: tired eyes lower open-EAR over time

    def loop():
        if state["done"]:
            return
        if state.get("calibrating"):
            root.after(100, loop)
            return
        feats, ear, lms, hud, vec, _frame = snap()
        now = time.perf_counter()
        # Blink FIRST: the jump-guard below returns early on distorted frames
        # and used to starve the detector mid-hold (beta-160434).
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
            last_feats[0] = feats
            feat_history.append((now, feats))
            while len(feat_history) > 120:
                feat_history.pop(0)
            if vec is not None:
                last_vec[0] = vec
                vec_history.append((now, vec))
                while len(vec_history) > 120:
                    vec_history.pop(0)
            feat_window.append(feats)
            while len(feat_window) > 7:
                feat_window.pop(0)
            # Median, not mean: landmark spikes (blinks, glints) poison means.
            avg = [sorted(f[j] for f in feat_window)[len(feat_window) // 2]
                   for j in range(len(feats))]
            sample = avg
            if state.get("use_app"):
                if vec is None:
                    sample = None
                else:
                    vec_window.append(vec)
                    while len(vec_window) > 7:
                        vec_window.pop(0)
                    vavg = np.median(vec_window, axis=0)
                    sample = (vavg, avg)
            if sample is not None:
                px, py = corrector[0].predict(sample)
                # Saccades are confirmed, not rejected (board-171805): 3
                # agreeing frames snap; single spikes still drop. NEVER
                # return early: a "select" verdict for this frame would be
                # dropped while the detector already fired.
                if smooth["x"] is None:
                    smooth.update(x=px, y=py)
                    gate.reset()
                else:
                    eyes_open = ear is not None and ear > blink[0].ear_threshold
                    raw = (vec, feats) if state.get("use_app") else feats
                    verdict = gate.check(px, py, raw, smooth["x"], smooth["y"],
                                         eyes_open=eyes_open)
                    if verdict == "drop":
                        if feat_window:
                            feat_window.pop()
                        if state.get("use_app") and vec_window:
                            vec_window.pop()
                    elif verdict == "snap":
                        pts = gate.points
                        smooth["x"] = sum(p[0] for p in pts) / len(pts)
                        smooth["y"] = sum(p[1] for p in pts) / len(pts)
                        del feat_window[:]
                        if state.get("use_app"):
                            del vec_window[:]
                            for s in gate.frames:
                                feat_window.append(s[1])
                                vec_window.append(s[0])
                        else:
                            feat_window.extend(gate.frames)
                        gate.reset()
                    else:
                        smooth["x"] = 0.4 * px + 0.6 * smooth["x"]
                        smooth["y"] = 0.4 * py + 0.6 * smooth["y"]
                if smooth["x"] is not None:
                    last_hl[0] = hit_key(keys, smooth["x"] - mleft,
                                          smooth["y"] - mtop)
        hl_history.append((now, last_hl[0]))
        while len(hl_history) > 90:
            hl_history.pop(0)
        if now - state.get("last_log", 0) > 0.5:
            state["last_log"] = now
            append_event(session, "trace",
                         {"gaze": [smooth["x"], smooth["y"]], "hl": last_hl[0],
                          "ear": ear, "hint": hint,
                          "map": ("appearance" if state.get("use_app")
                                  else "linear"),
                          "brightness": (hud or {}).get("brightness")})
        draw_keyboard(last_hl[0], hud, hint)
        hl = last_hl[0]
        if select_event:
                # Pre-blink target: eyes are unreliable during the blink.
                past = [h for t, h in hl_history if t <= now - 0.45]
                target = past[-1] if past else hl
                if target is None:
                    root.after(33, loop)
                    return
                hl = target
                if hl == "SPACE":
                    state["typed"] += " "
                elif hl == "DELETE":
                    state["typed"] = state["typed"][:-1]
                else:
                    state["typed"] += hl
                # Exact anchor: user looked at this key's center. Features
                # must be pre-closure (transition frames corrupt the iris).
                verdict = "no_anchor"
                pre = [f for t, f in feat_history if t <= now - 0.7]
                anchor_feats = pre[-1] if pre else last_feats[0]
                anchor = anchor_feats
                if state.get("use_app"):
                    prev = [v for t, v in vec_history if t <= now - 0.7]
                    anchor_vec = prev[-1] if prev else last_vec[0]
                    anchor = ((anchor_vec, anchor_feats)
                              if anchor_vec is not None
                              and anchor_feats is not None else None)
                for k in keys:
                    if k["label"] == hl:
                        x1, y1, x2, y2 = k["rect"]
                        cx, cy = (x1 + x2) / 2 + mleft, (y1 + y2) / 2 + mtop
                        if anchor is not None:
                            state_, info = corrector[0].update(anchor, (cx, cy),
                                                               certain=True)
                            verdict = f"{state_}:{info.get('residual', 0):.0f}"
                        break
                append_event(session, "selection",
                             {"key": hl, "typed": state["typed"],
                              "ear": ear, "gaze": [smooth["x"], smooth["y"]],
                              "anchor": verdict})
                expected = args.target[:len(state["typed"])]
                if not args.target.startswith(state["typed"]):
                    state["errors"] += 1
                if state["typed"] == args.target:
                    secs = now - state["started"]
                    verdict = "PASS" if (secs <= 60 and state["errors"] <= 2) else "MISS"
                    print(f"done: typed={state['typed']!r} secs={secs:.1f} "
                          f"errors={state['errors']} {verdict} "
                          f"map={'appearance' if state.get('use_app') else 'linear'}")
                    state["done"] = True
                    root.after(1500, root.destroy)
                    return
        root.after(33, loop)

    def on_key(event):
        if event.keysym == "r" and not state.get("calibrating"):
            state["calibrating"] = True
            print("recalibrating...")
            append_event(session, "recalibrate", {})
            old_gate = ear_gate[0]
            try:
                smooth.update(x=None, y=None)
                refit_all()
            except Exception as e:
                ear_gate[0] = old_gate
                print(f"recalibrate aborted: {e}")
            state["started"] = time.perf_counter()
            state["calibrating"] = False
        if event.keysym in ("Escape",) or (event.state & 0x1 and event.keysym in ("Q",)):
            root.destroy()

    root.bind("<Key>", on_key)
    root.after(33, loop)
    root.mainloop()
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
