"""Guided blink test: the tool instructs, you comply, it scores.

Modes: double (5 singles + 5 deliberate doubles) or long (5 naturals +
5 holds of ~0.6 s). Each trial: prompt for 3 s, then verdict. You blink
exactly as instructed and nothing else. Output: confusion counts.
Usage: .\\.venv\\Scripts\\python.exe tools\\blink_test.py [--mode double|long]
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.blink import DoubleBlink, LongBlink, mean_ear
from gaze.clock import MonoClock

BASELINE_S = 5.0
TRIAL_S = 4.0


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["double", "long"], default="double")
    mode = ap.parse_args().mode
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

    def ear_now():
        ok, frame = cap.read()
        if not ok:
            return None
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        return mean_ear(lms)

    print(f"BASELINE: eyes open, {BASELINE_S:.0f} s...")
    base_ears = []
    while time.perf_counter() - t0 < BASELINE_S:
        ear = ear_now()
        if ear is not None:
            base_ears.append(ear)
    base_ears.sort()
    med = base_ears[len(base_ears) // 2]
    thr = min(0.25, max(0.12, med * 0.6))
    print(f"open_median={med:.3f} threshold={thr:.3f}\n")

    if mode == "double":
        trials = ["single"] * 5 + ["double"] * 5
        det = DoubleBlink(ear_threshold=thr)
    else:
        trials = ["still"] * 3 + ["natural"] * 4 + ["double"] * 3 + ["hold"] * 5
        det = LongBlink(ear_threshold=thr, hold_s=0.6)
    random.Random(7).shuffle(trials)
    results = []
    try:
        for i, kind in enumerate(trials, 1):
            prompts = {"single": "BLINK ONCE", "double": "BLINK TWICE (slow, deliberate)",
                       "still": "STARE, DO NOT BLINK",
                       "natural": "BLINK NATURALLY AS NEEDED",
                       "hold": "CLOSE EYES ~0.6 s, THEN OPEN"}
            want = (kind == "double" and mode == "double") or kind == "hold"
            print(f"trial {i}/{len(trials)}: {prompts[kind]}", flush=True)
            for attr in ("_state", "_closed_at", "_opened_at", "_fired_at"):
                if hasattr(det, attr):
                    setattr(det, attr, "open" if attr == "_state" else None)
            fired = False
            below, below_max, cur = 0.0, 0.0, 0.0
            n_none, n_tot = 0, 0
            t_prev, ear_min = None, 1.0
            tend = time.perf_counter() + TRIAL_S
            while time.perf_counter() < tend:
                ear = ear_now()
                now = time.perf_counter()
                n_tot += 1
                if ear is None:
                    n_none += 1
                    det.update(None, now)
                    continue
                ear_min = min(ear_min, ear)
                if t_prev is not None:
                    dt = now - t_prev
                    if ear < thr:
                        cur += dt
                        below_max = max(below_max, cur)
                    else:
                        below += cur
                        cur = 0.0
                t_prev = now
                if det.update(ear, now) == "select":
                    fired = True
            ok = fired == want
            results.append((kind, fired, ok))
            print(f"  -> detected={'SELECT' if fired else 'none'} "
                  f"expected={'SELECT' if want else 'none'} "
                  f"minEAR={ear_min:.3f} longest_shut={below_max * 1000:.0f}ms "
                  f"invalid={n_none}/{n_tot} "
                  f"{'OK' if ok else 'WRONG'}")
    except KeyboardInterrupt:
        print("\naborted.")
    cap.release()
    n_ok = sum(1 for _, _, ok in results if ok)
    neg = ("single", "natural", "still") + (() if mode == "double" else ("double",))
    pos = ("double", "hold") if mode == "double" else ("hold",)
    false_fire = sum(1 for k, f, _ in results if k in neg and f)
    missed = sum(1 for k, f, _ in results if k in pos and not f)
    print(f"\nscore: {n_ok}/{len(results)} correct. "
          f"false selects={false_fire}, intentional missed={missed}")
    print("Blink test done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
