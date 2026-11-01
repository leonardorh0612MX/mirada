"""T26 probe: is the facial transformation matrix usable for head-frame gaze?

Checks, with numbers:
1. Matrix present, rotation block ~orthonormal.
2. Invariance: gaze fixed on centre dot, head turns L/R/U/D. In head frame
   the eye vector should move LESS than the raw image features do.
3. Sensitivity: head fixed, gaze moves to L/R dots. Head-frame vector must
   still move (signal preserved, not normalized away).

Usage: .\\.venv\\Scripts\\python.exe tools\\t26_geo_probe.py --monitor 1 --camera 0
"""

import argparse
import os
import sys
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.features import LEFT_INNER, LEFT_IRIS, LEFT_OUTER  # noqa: E402
from gaze.features import RIGHT_INNER, RIGHT_IRIS, RIGHT_OUTER  # noqa: E402
from tools.record_session import list_monitors, set_dpi_aware  # noqa: E402


def eye_vec(lms3, outer, inner, iris_ids):
    """Iris minus eye-corner midpoint, in landmark 3D space."""
    cx = (lms3[outer][0] + lms3[inner][0]) / 2.0
    cy = (lms3[outer][1] + lms3[inner][1]) / 2.0
    cz = (lms3[outer][2] + lms3[inner][2]) / 2.0
    ix = sum(lms3[i][0] for i in iris_ids) / len(iris_ids)
    iy = sum(lms3[i][1] for i in iris_ids) / len(iris_ids)
    iz = sum(lms3[i][2] for i in iris_ids) / len(iris_ids)
    w = ((lms3[outer][0] - lms3[inner][0]) ** 2 +
         (lms3[outer][1] - lms3[inner][1]) ** 2) ** 0.5 or 1.0
    return ((ix - cx) / w, (iy - cy) / w, (iz - cz) / w)


def mat_vec(R, v):
    return tuple(sum(R[i][j] * v[j] for j in range(3)) for i in range(3))


def stats(vectors):
    if len(vectors) < 5:
        return None
    out = []
    for j in range(3):
        col = [v[j] for v in vectors]
        mu = sum(col) / len(col)
        sd = (sum((c - mu) ** 2 for c in col) / len(col)) ** 0.5
        out.append((mu, sd))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()
    set_dpi_aware()
    mleft, mtop, mw, mh = list_monitors()[args.monitor]

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print("landmarker (with transformation matrix)...", flush=True)
    landmarker = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=os.path.join(repo, "data", "face_landmarker.task")),
            num_faces=1, output_facial_transformation_matrixes=True))
    print("opening camera...", flush=True)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    print(f"camera opened={cap.isOpened()}", flush=True)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def snap():
        ok, frame = cap.read()
        if not ok:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not res.face_landmarks:
            return None
        h, w = frame.shape[:2]
        lms3 = [(p.x * w, p.y * h, p.z * w) for p in res.face_landmarks[0]]
        mat = None
        if res.facial_transformation_matrixes:
            m = res.facial_transformation_matrixes[0]
            mat = [[float(m[i][j]) for j in range(4)] for i in range(4)]
        return lms3, mat

    root = tk.Tk()
    root.geometry(f"{mw}x{mh}+{mleft}+{mtop}")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#111111")
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#111111", highlightthickness=0)
    canvas.pack()
    state = {"quit": False}
    root.bind("<Key>", lambda e: state.update(
        quit=True) if (e.state & 0x1 and e.keysym in ("Q",)) else None)

    def collect(gx, gy, label, seconds=3.0):
        raw, head = [], []
        end = time.time() + seconds
        while time.time() < end and not state["quit"]:
            s = snap()
            if s is not None:
                lms3, mat = s
                v = eye_vec(lms3, LEFT_OUTER, LEFT_INNER, LEFT_IRIS)
                raw.append(v)
                if mat is not None:
                    R = [[mat[i][j] for j in range(3)] for i in range(3)]
                    # Head frame: apply inverse rotation (transpose).
                    Rt = [[R[j][i] for j in range(3)] for i in range(3)]
                    head.append(mat_vec(Rt, v))
            try:
                canvas.delete("all")
                canvas.create_oval(gx - mleft - 40, gy - mtop - 40,
                                   gx - mleft + 40, gy - mtop + 40, fill="#ffffff")
                canvas.create_text(mw // 2, 28, text=label, fill="#ffffff",
                                   font=("Arial", 18))
                root.update()
            except Exception:
                break
        return raw, head

    cx, cy = mleft + mw // 2, mtop + mh // 2
    phases = [
        ("FIXED gaze centre, head CENTRED", cx, cy),
        ("FIXED gaze centre, turn head LEFT", cx, cy),
        ("FIXED gaze centre, turn head RIGHT", cx, cy),
        ("FIXED gaze centre, tilt head UP", cx, cy),
        ("FIXED gaze centre, tilt head DOWN", cx, cy),
        ("head CENTRED, gaze LEFT dot", mleft + mw // 5, cy),
        ("head CENTRED, gaze RIGHT dot", mleft + 4 * mw // 5, cy),
    ]
    results = {}
    for label, gx, gy in phases:
        raw, head = collect(gx, gy, label)
        results[label] = (stats(raw), stats(head), len(raw))
        print(f"{label}: n={len(raw)}")
    root.destroy()
    cap.release()

    print("\n--- eye vector (x,y,z) mean/std per phase ---")
    for label, (sr, sh, n) in results.items():
        if sr and sh:
            print(f"{label}")
            print(f"  image-frame: mean=({sr[0][0]:+.3f},{sr[1][0]:+.3f}) "
                  f"std=({sr[0][1]:.3f},{sr[1][1]:.3f})")
            print(f"  head-frame : mean=({sh[0][0]:+.3f},{sh[1][0]:+.3f}) "
                  f"std=({sh[0][1]:.3f},{sh[1][1]:.3f})")
    c_img = results[phases[0][0]][0]
    c_head = results[phases[0][0]][1]
    if c_img and c_head:
        print("\n--- invariance (mean shift vs CENTRED, gaze fixed) ---")
        for label, _, _ in phases[1:5]:
            sr, sh, _ = results[label]
            d_img = ((sr[0][0] - c_img[0][0]) ** 2 + (sr[1][0] - c_img[1][0]) ** 2) ** 0.5
            d_head = ((sh[0][0] - c_head[0][0]) ** 2 + (sh[1][0] - c_head[1][0]) ** 2) ** 0.5
            print(f"  {label}: image={d_img:.3f} head={d_head:.3f}")
        print("--- sensitivity (head centred, gaze moves) ---")
        for label, _, _ in phases[5:]:
            sr, sh, _ = results[label]
            d_img = ((sr[0][0] - c_img[0][0]) ** 2 + (sr[1][0] - c_img[1][0]) ** 2) ** 0.5
            d_head = ((sh[0][0] - c_head[0][0]) ** 2 + (sh[1][0] - c_head[1][0]) ** 2) ** 0.5
            print(f"  {label}: image={d_img:.3f} head={d_head:.3f}")
    print("T26 probe done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
