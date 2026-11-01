"""T25 probe: validate the bilinear GazeMap against the legacy linear fit.

Same factorial enrollment as beta (A: 9 dots centred, B: 5 dots x 5 poses,
E: 9 dots centred), then validation dots at UNSEEN postures (head turned
left / right / natural free). Both models fit on identical enrollment
samples; report is per-posture mean error on held-out validation dots.

Usage: .\\.venv\\Scripts\\python.exe tools\\gaze_map_probe.py --monitor 1 --camera 0
Shift+Q quits.
"""

import argparse
import os
import sys
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.calibration import GazeMap, fit_calibration, fit_gaze_map  # noqa: E402
from gaze.features import extract_features  # noqa: E402
from tools.record_session import (  # noqa: E402
    FixationBuffer,
    list_monitors,
    set_dpi_aware,
)

POSES = ["Head CENTRED", "Turn head LEFT, eyes on the dot",
         "Turn head RIGHT, eyes on the dot", "Tilt head UP, eyes on the dot",
         "Tilt head DOWN, eyes on the dot"]
VAL_POSES = ["VAL: turn head LEFT, look at the dot",
             "VAL: turn head RIGHT, look at the dot",
             "VAL: look NATURALLY at the dot (any posture)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()
    set_dpi_aware()
    mons = list_monitors()
    mleft, mtop, mw, mh = mons[args.monitor]
    print(f"monitors: {mons}")

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from recorder.session import append_event, new_session

    session = new_session(os.path.join(repo, "data"),
                          time.strftime("gmap-%Y%m%d-%H%M%S"), meta={})
    print(f"session: {session}")
    model_path = os.path.join(repo, "data", "face_landmarker.task")
    landmarker = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            num_faces=1))
    print("landmarker ready, opening camera...", flush=True)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    print(f"camera opened={cap.isOpened()}", flush=True)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def snap_feats():
        ok, frame = cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not res.face_landmarks:
            return None
        lms = [(p.x * frame.shape[1], p.y * frame.shape[0])
               for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        return feats if valid else None

    root = tk.Tk()
    root.geometry(f"{mw}x{mh}+{mleft}+{mtop}")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()
    root.configure(bg="#111111")
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#111111", highlightthickness=0)
    canvas.pack()
    state = {"quit": False}

    def on_key(event):
        if event.state & 0x1 and event.keysym in ("Q",):
            state["quit"] = True

    root.bind("<Key>", on_key)

    def capture(gx, gy, label):
        fb = FixationBuffer(min_frames=12)
        last_beat = time.time()
        while not fb.ready() and not state["quit"]:
            fb.add(snap_feats())
            if time.time() - last_beat > 2.0:
                last_beat = time.time()
                print(f"  ...waiting for stable face ({label})", flush=True)
            try:
                canvas.delete("all")
                canvas.create_oval(gx - mleft - 45, gy - mtop - 45,
                                   gx - mleft + 45, gy - mtop + 45, fill="#ffffff")
                canvas.create_text(gx - mleft, gy - mtop, text="o",
                                   fill="#111111", font=("Arial", 16))
                canvas.create_text(mw // 2, 28, text=label, fill="#ffffff",
                                   font=("Arial", 18))
                root.update()
            except Exception:
                break
        return fb.average() if fb.ready() else None

    dots9 = [(mleft + mw * fx, mtop + mh * fy)
             for fy in (0.12, 0.5, 0.88) for fx in (0.12, 0.5, 0.88)]
    dots5 = [(mleft + mw * 0.5, mtop + mh * 0.5),
             (mleft + mw * 0.2, mtop + mh * 0.2), (mleft + mw * 0.8, mtop + mh * 0.2),
             (mleft + mw * 0.2, mtop + mh * 0.8), (mleft + mw * 0.8, mtop + mh * 0.8)]

    print("ENROLLMENT: A(9) + B(5x5 poses) + E(9)...")
    samples = []
    plan = [("A", gx, gy, POSES[0]) for gx, gy in dots9]
    plan += [("B", gx, gy, pose) for pose in POSES for gx, gy in dots5]
    plan += [("E", gx, gy, POSES[0]) for gx, gy in dots9]
    for i, (block, gx, gy, pose) in enumerate(plan, 1):
        avg = capture(gx, gy, f"{i}/{len(plan)} {pose}")
        if avg is None:
            print("quit during enrollment")
            return 1
        samples.append((avg, gx, gy))
        append_event(session, "calib",
                     {"features": avg, "target": [gx, gy], "block": block})

    gmap = fit_gaze_map(samples)
    from gaze.features import map_to_screen

    lin = fit_calibration(samples)
    append_event(session, "gaze_map", gmap.to_dict())

    def errs(model_fn):
        es = []
        for feats, gx, gy in samples:
            px, py = model_fn(feats)
            es.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
        return sum(es) / len(es)

    print(f"resub: gazemap={errs(gmap.predict):.0f}px linear={errs(lambda f: map_to_screen(f, lin)):.0f}px")

    print("VALIDATION: unseen postures, 1s average per dot...")
    val_dots = [(mleft + mw * fx, mtop + mh * fy)
                for fy in (0.25, 0.75) for fx in (0.25, 0.5, 0.75)]
    results = {}
    for pose in VAL_POSES:
        eg, el = [], []
        for gx, gy in val_dots:
            avg = capture(gx, gy, pose)
            if avg is None:
                print("quit during validation")
                return 1
            xg, yg = gmap.predict(avg)
            xl, yl = map_to_screen(avg, lin)
            eg.append(((xg - gx) ** 2 + (yg - gy) ** 2) ** 0.5)
            el.append(((xl - gx) ** 2 + (yl - gy) ** 2) ** 0.5)
            append_event(session, "validation",
                         {"pose": pose, "target": [gx, gy],
                          "err_gazemap": eg[-1], "err_linear": el[-1]})
        results[pose] = (sum(eg) / len(eg), sum(el) / len(el))
        print(f"{pose}: gazemap={results[pose][0]:.0f}px linear={results[pose][1]:.0f}px")
    print("T25 probe done. Paste this whole output back.")
    root.destroy()
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
