"""Environment diagnostic: light, face geometry, feature noise floor.

Stare at the camera center for ~15 s. Reports hard numbers for RESEARCH.md:
frame brightness, face/eye size in px, per-feature noise (stdev), presence.
Usage: .\\.venv\\Scripts\\python.exe tools\\t4_diagnostic.py
"""

import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.clock import MonoClock
from gaze.features import extract_features

DURATION_S = 15


def main():
    import cv2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import mediapipe as mp

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(repo, "data", "face_landmarker.task")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("no_camera")
        return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    base = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()

    frames, with_face, bright, faces_w, eyes_w, feats_all = 0, 0, [], [], [], []
    print("STARE AT THE CAMERA CENTER. 15 s...", flush=True)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < DURATION_S:
        ok, frame = cap.read()
        if not ok:
            continue
        frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright.append(float(gray.mean()))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            continue
        with_face += 1
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        faces_w.append(lms[454][0] - lms[234][0])
        eyes_w.append(((lms[33][0] - lms[133][0]) ** 2 +
                       (lms[33][1] - lms[133][1]) ** 2) ** 0.5)
        feats, valid, _ = extract_features(lms)
        if valid:
            feats_all.append(feats)
    cap.release()
    print(f"frames={frames} presence={with_face / max(frames, 1):.2f}")
    print(f"brightness mean={statistics.mean(bright):.1f} min={min(bright):.1f} max={max(bright):.1f} (0-255)")
    print(f"face_width_px mean={statistics.mean(faces_w):.0f} eye_width_px mean={statistics.mean(eyes_w):.0f}")
    if feats_all:
        cols = list(zip(*feats_all))
        print(f"features n={len(feats_all)}")
        for j, col in enumerate(cols):
            print(f"noise feat{j} stdev={statistics.stdev(col):.5f}")
    print("T4 diag done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
