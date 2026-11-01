"""Gaze-during-blink probe: where does the prediction go with eyes shut?

Quick 9-point calibration, then 5 trials. Each trial: fixate the center
dot 2 s (open phase), CLOSE on prompt for 1 s (closed phase). Reports
open-phase error vs known target and closed-phase drift distance.
Usage: .\\.venv\\Scripts\\python.exe tools\\gaze_blink_probe.py --monitor 1
"""

import argparse
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corrector.corrector import Corrector
from gaze.blink import mean_ear
from gaze.calibration import fit_calibration
from gaze.clock import MonoClock
from gaze.features import extract_features
from tools.record_session import FixationBuffer, list_monitors, set_dpi_aware


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()
    set_dpi_aware()

    import cv2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import mediapipe as mp
    import tkinter as tk

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(repo, "data", "face_landmarker.task")
    monitor = list_monitors()[args.monitor]
    mleft, mtop, mw, mh = monitor
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
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#181818", highlightthickness=0)
    canvas.pack()
    t0 = time.perf_counter()

    def snap():
        ok, frame = cap.read()
        if not ok:
            return None, None
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None, None
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        return (feats if valid else None), mean_ear(lms)

    def dot(x, y, label, inside=""):
        canvas.delete("all")
        canvas.create_oval(x - mleft - 55, y - mtop - 55, x - mleft + 55,
                           y - mtop + 55, fill="#ffffff")
        canvas.create_text(x - mleft, y - mtop, text=inside or label,
                           fill="#111111", font=("Arial", 14))
        canvas.create_text(mw // 2, 28, text=label, fill="#ffffff", font=("Arial", 18))
        root.update()

    grid = [(mleft + mw * fx, mtop + mh * fy)
            for fy in (0.08, 0.36, 0.64, 0.92)
            for fx in (0.08, 0.36, 0.64, 0.92)]
    calib = []
    for i, (gx, gy) in enumerate(grid):
        fb = FixationBuffer(min_frames=12)
        tend = time.perf_counter() + 8.0
        while not fb.ready() and time.perf_counter() < tend:
            dot(gx, gy, f"Calibrating {i + 1}/16", inside=f"{i + 1}/16\nLOOK")
            feats, _ = snap()
            fb.add(feats)
        calib.append((fb.average() or fb.buf[-1], gx, gy))
    corrector = Corrector(fit_calibration(calib))
    print("calibrated. 5 trials: fixate, then CLOSE on prompt.", flush=True)

    cx, cy = mleft + mw / 2.0, mtop + mh / 2.0
    open_errs, closed_drift = [], []
    try:
        for trial in range(1, 6):
            dot(cx, cy, f"Trial {trial}/5: FIXATE (2 s)", inside=f"{trial}/5\nFIXATE")
            tend = time.perf_counter() + 2.0
            anchor = None
            while time.perf_counter() < tend:
                feats, _ = snap()
                if feats is not None:
                    px, py = corrector.predict(feats)
                    anchor = (px, py)
            if anchor is None:
                print(f"trial {trial}: no open predictions, skipped")
                continue
            open_errs.append(((anchor[0] - cx) ** 2 + (anchor[1] - cy) ** 2) ** 0.5)
            dot(cx, cy, f"Trial {trial}/5: CLOSE EYES 1 s", inside=f"{trial}/5\nCLOSE")
            tend = time.perf_counter() + 1.0
            worst = 0.0
            while time.perf_counter() < tend:
                feats, _ = snap()
                if feats is not None:
                    px, py = corrector.predict(feats)
                    worst = max(worst, ((px - anchor[0]) ** 2 + (py - anchor[1]) ** 2) ** 0.5)
            closed_drift.append(worst)
            print(f"trial {trial}: open_err={open_errs[-1]:.0f}px closed_drift={worst:.0f}px")
    finally:
        root.destroy()
        cap.release()
    if open_errs:
        print(f"open median err={statistics.median(open_errs):.0f}px, "
              f"closed median drift={statistics.median(closed_drift):.0f}px")
    print("Gaze-blink probe done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(130)
