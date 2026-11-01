"""T3 probe: MediaPipe FaceLandmarker (Tasks API) on this machine.

MediaPipe 1.x removed mp.solutions. This uses vision.FaceLandmarker with a
.task bundle downloaded on first run.
Usage:
  .\\.venv\\Scripts\\python.exe -m pip install mediapipe opencv-python
  .\\.venv\\Scripts\\python.exe tools\\t3_mediapipe_probe.py
"""

import os
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
MODEL_PATH = os.path.join(REPO, "data", "face_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
DURATION_S = 60


def main():
    try:
        import cv2
    except ImportError:
        print("missing: opencv-python. Run the pip install line first.")
        return 2
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError:
        print("missing: mediapipe. Run the pip install line first.")
        return 2

    print(f"mediapipe version: {mp.__version__}", flush=True)
    if not os.path.exists(MODEL_PATH):
        print(f"downloading task bundle...", flush=True)
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"task bundle kb: {os.path.getsize(MODEL_PATH) // 1024}", flush=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("no_camera: default webcam did not open.")
        return 2
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"camera resolution: {w}x{h}", flush=True)

    base = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )
    from gaze.clock import MonoClock

    frames = 0
    with_landmarks = 0
    n_points = 0
    t0 = time.perf_counter()
    clock = MonoClock()
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        while time.perf_counter() - t0 < DURATION_S:
            ok, frame = cap.read()
            if not ok:
                continue
            frames += 1
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            res = landmarker.detect_for_video(mp_image, clock.now_ms())
            if res.face_landmarks:
                with_landmarks += 1
                n_points = len(res.face_landmarks[0])
            remaining = int(DURATION_S - (time.perf_counter() - t0))
            print(f"\rframes={frames} with_landmarks={with_landmarks} {remaining}s left", end="", flush=True)
    cap.release()
    elapsed = time.perf_counter() - t0
    print(f"\nframes={frames} elapsed={elapsed:.1f}s fps={frames / elapsed:.1f}")
    print(f"landmark_presence={with_landmarks / max(frames, 1):.2f} landmarks_per_face={n_points}")
    print("T3 done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
