"""Blink practice and threshold check. Live EAR, closures, doubles.

Stare at the camera. Blink naturally a few times, then try slow deliberate
double blinks. Reports whether the auto-threshold separates your blinks.
Usage: .\\.venv\\Scripts\\python.exe tools\\blink_practice.py
Ctrl+C to quit.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.blink import DoubleBlink, mean_ear
from gaze.clock import MonoClock

BASELINE_S = 5.0


def main():
    import cv2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import mediapipe as mp

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(repo, "data", "face_landmarker.task")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    base = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()

    t0 = time.perf_counter()
    base_ears = []
    print(f"BASELINE: eyes open, {BASELINE_S:.0f} s...", flush=True)
    while time.perf_counter() - t0 < BASELINE_S:
        ok, frame = cap.read()
        if not ok:
            continue
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            continue
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        ear = mean_ear(lms)
        if ear is not None:
            base_ears.append(ear)
    base_ears.sort()
    med = base_ears[len(base_ears) // 2]
    thr = min(0.25, max(0.12, med * 0.6))
    print(f"open_median={med:.3f} threshold={thr:.3f}")
    print("Now: natural blinks, then deliberate DOUBLE blinks. Ctrl+C quits.")

    det = DoubleBlink(ear_threshold=thr)
    closes = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            res = landmarker.detect_for_video(mp_image, clock.now_ms())
            if not res.face_landmarks:
                continue
            h, w = frame.shape[:2]
            lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
            ear = mean_ear(lms)
            if ear is None:
                continue
            now = time.perf_counter()
            bar = "#" * int(ear * 60)
            closed = "SHUT" if ear < thr else "    "
            if ear < thr:
                closes += 1
            sel = det.update(ear, now)
            mark = " <<< DOUBLE!" if sel == "select" else ""
            print(f"\rEAR {ear:.3f} {closed} [{bar:<40}] closes={closes}{mark}   ",
                  end="", flush=True)
    except KeyboardInterrupt:
        print(f"\ncloses={closes}. Adjust if doubles never fire.")
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
