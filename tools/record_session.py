"""T13 capture tool v2: floating dot overlay for real study sessions.

The dot is a small always-on-top borderless window that moves to each target
position. The rest of the screen stays free for studying. SPACE anywhere
confirms fixation (global hotkey). Shift+Q quits.
Usage:
  .\\.venv\\Scripts\\python.exe -m pip install pynput
  .\\.venv\\Scripts\\python.exe tools\\record_session.py [--seconds 900] [--camera 0] [--monitor 1]
"""

import argparse
import ctypes
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.calibration import dot_schedule, fit_calibration
from app.camselect import resolve_camera, resolve_monitor
from gaze.clock import MonoClock
from gaze.features import extract_features
from recorder.session import append_event, new_session, read_events

DOT_EVERY_S = 120.0
DOT_SIZE = 90
DOT_SHOW_S = 10.0


def beep():
    try:
        import winsound

        winsound.Beep(880, 300)
    except Exception:
        pass


def save_eye_crops(session_dir, index, frame, lms):
    """Save left/right eye crops (~60x36) for future appearance-model work.

    Crops are face images: local only, under data/ (gitignored). See EVAL.md.
    """
    import cv2 as _cv2

    crops_dir = os.path.join(session_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)
    h, w = frame.shape[:2]
    for name, ids in (("L", (33, 133, 468, 469, 470, 471, 472)),
                      ("R", (362, 263, 473, 474, 475, 476, 477))):
        xs = [lms[i][0] for i in ids]
        ys = [lms[i][1] for i in ids]
        pad = 12
        x1, x2 = max(0, int(min(xs) - pad)), min(w, int(max(xs) + pad))
        y1, y2 = max(0, int(min(ys) - pad)), min(h, int(max(ys) + pad))
        if x2 - x1 < 10 or y2 - y1 < 6:
            continue
        crop = frame[y1:y2, x1:x2]
        stem = f"{index:06d}" if isinstance(index, int) else str(index)
        _cv2.imwrite(os.path.join(crops_dir, f"{stem}_{name}.jpg"), crop)


def set_dpi_aware():
    """Physical pixels for monitor rects and grabs (else black/offscreen)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def list_monitors():
    """[(left, top, width, height)] per monitor. Primary first. Stdlib only."""
    rects = []

    def cb(hmon, hdc, lprc, data):
        r = lprc.contents
        rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return 1

    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p,
                                 ctypes.c_void_p, ctypes.POINTER(_RECT),
                                 ctypes.c_void_p)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, CMPFUNC(cb), 0)
    return rects


def grid_points(monitor, n=3):
    """n x n stare points in virtual screen pixels for the given monitor."""
    left, top, w, h = monitor
    return [(left + w * (0.1 + 0.8 * i / (n - 1)),
             top + h * (0.1 + 0.8 * j / (n - 1)))
            for j in range(n) for i in range(n)]


def load_dotenv(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


class FixationBuffer:
    """Buffers valid feature frames during a fixation; averages the tail.

    Readiness is count plus a split-half stability gate on the iris
    components (I-DT inspired, Salvucci and Goldberg 2000): the means of
    the two halves of the window must agree within `stability`. Pure
    max-min dispersion is too fragile for landmark noise (single spikes
    reach 0.05-0.2); split-half averages spikes away while a saccade or
    drift mid-window splits the halves apart.
    """

    def __init__(self, min_frames=10, tail_n=40, stability=0.04, iris_dims=4):
        self.buf = []
        self.min_frames = min_frames
        self.tail_n = tail_n
        self.stability = stability
        self.iris_dims = iris_dims

    def add(self, feats):
        if feats is not None:
            self.buf.append(feats)

    def ready(self):
        if len(self.buf) < self.min_frames:
            return False
        win = self.buf[-self.min_frames:]
        half = len(win) // 2
        for j in range(min(self.iris_dims, len(win[0]))):
            m1 = sum(f[j] for f in win[:half]) / half
            m2 = sum(f[j] for f in win[half:]) / (len(win) - half)
            if abs(m1 - m2) > self.stability:
                return False
        return True

    def average(self):
        if not self.ready():
            return None
        tail = self.buf[-self.tail_n:]
        return [sum(f[j] for f in tail) / len(tail)
                for j in range(len(tail[0]))]


def new_key_state():
    return {"space": False, "quit": False, "shift": False}


def press_key(state, key, keyboard):
    """Update state from a pynput key press. Quit requires Shift held."""
    if key == keyboard.Key.space:
        state["space"] = True
    elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        state["shift"] = True
    elif getattr(key, "char", None) and (
            key.char == "Q" or (key.char == "q" and state["shift"])):
        state["quit"] = True


def release_key(state, key, keyboard):
    if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        state["shift"] = False


class DotOverlay:
    """Borderless always-on-top dot. hide() frees the screen completely."""

    def __init__(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        self.canvas = tk.Canvas(self.root, width=DOT_SIZE, height=DOT_SIZE,
                                bg="black", highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_oval(8, 8, DOT_SIZE - 8, DOT_SIZE - 8, fill="white")
        self.root.withdraw()

    def show(self, x, y):
        self.root.geometry(f"{DOT_SIZE}x{DOT_SIZE}+{int(x - DOT_SIZE / 2)}+{int(y - DOT_SIZE / 2)}")
        self.root.deiconify()
        self.root.update()

    def hide(self):
        self.root.withdraw()
        self.root.update()

    def close(self):
        self.root.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=900.0)
    ap.add_argument("--camera", type=int, default=None)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--monitor", type=int, default=None,
                    help="monitor index from list_monitors (0=primary)")
    args = ap.parse_args()

    try:
        from pynput import keyboard
    except ImportError:
        print("missing: pynput. Run: .\\.venv\\Scripts\\python.exe -m pip install pynput")
        return 2
    try:
        import cv2
    except ImportError:
        print("missing: opencv-python.")
        return 2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from PIL import ImageGrab

    set_dpi_aware()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(repo, ".env"))

    monitors = list_monitors()
    print(f"monitors: {monitors}")
    mon = resolve_monitor(args.monitor)
    if mon is None:
        return 2
    if mon >= len(monitors):
        print(f"no monitor {mon}. Use one of 0..{len(monitors) - 1}.")
        return 2
    monitor = monitors[mon]
    cam = resolve_camera(args.camera)
    if cam is None:
        return 2

    model_path = os.path.join(repo, "data", "face_landmarker.task")
    if not os.path.exists(model_path):
        print("missing model bundle. Run tools/t3_mediapipe_probe.py once first.")
        return 2

    session = new_session(os.path.join(repo, "data"), time.strftime("sess-%Y%m%d-%H%M%S"))
    print(f"session: {session}")

    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"no_camera: index {cam} did not open.")
        return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    actual = [int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
              int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))]
    print(f"camera resolution: {actual[0]}x{actual[1]}")
    append_event(session, "camera", {"index": cam, "resolution": list(actual)})

    base = mp_python.BaseOptions(model_asset_path=model_path)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()
    import mediapipe as mp

    # Environment check: light, face size, estimated distance (logged, printed)
    bright_vals, face_vals = [], []
    env_t0 = time.perf_counter()
    while time.perf_counter() - env_t0 < 3.0:
        ok_f, fr = cap.read()
        if not ok_f:
            continue
        bright_vals.append(float(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).mean()))
        mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=fr)
        r = landmarker.detect_for_video(mpi, clock.now_ms())
        if r.face_landmarks:
            hw = fr.shape[1]
            face_vals.append((r.face_landmarks[0][454].x - r.face_landmarks[0][234].x) * hw)
    from tools.env_check import estimate_distance_cm, expected_conditions, light_label

    env = {}
    if bright_vals:
        env["brightness"] = sum(bright_vals) / len(bright_vals)
    if face_vals:
        env["face_width_px"] = sum(face_vals) / len(face_vals)
        env["distance_cm"] = estimate_distance_cm(env["face_width_px"], actual[0])
    env["warnings"] = expected_conditions(env.get("brightness", 0), env.get("distance_cm"))
    append_event(session, "env", env)
    print(f"env: brightness={env.get('brightness', 0):.0f} ({light_label(env.get('brightness', 0))}) "
          f"distance~{env.get('distance_cm') or 0:.0f}cm warnings={env['warnings']}")

    overlay = DotOverlay()
    pressed = new_key_state()

    def on_press(key):
        press_key(pressed, key, keyboard)

    def on_release(key):
        release_key(pressed, key, keyboard)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    from pynput import mouse

    def on_click(x, y, button, pressed_down):
        if pressed_down and button == mouse.Button.left:
            append_event(session, "click", {"pos": [x, y]})

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    t0 = time.perf_counter()

    def snap_features():
        ok, frame = cap.read()
        if not ok:
            return None, None, None
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None, None, frame
        h, w = frame.shape[:2]
        lms = [(round(p.x * w, 1), round(p.y * h, 1)) for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        return (feats, lms, frame) if valid else (None, None, frame)

    def wait_space(min_frames=10):
        """Collect features until SPACE with >= min_frames buffered.

        Single-frame features are too noisy (measured SNR ~2:1). The sample
        is the mean of recent valid frames, taken before the eyes leave.
        SPACE pressed too early is ignored until enough frames exist.
        """
        pressed["space"] = False
        fb = FixationBuffer(min_frames=min_frames)
        hinted = False
        last_frame, last_lms = None, None
        give_up_at = time.perf_counter() + 20.0
        while not pressed["quit"]:
            if not fb.buf and time.perf_counter() > give_up_at:
                print("no valid landmarks captured (check light/camera).")
                return None, None, None
            overlay.root.update()
            feats, lms, frame = snap_features()
            fb.add(feats)
            if feats is not None:
                last_frame, last_lms = frame, lms
            if pressed["space"]:
                if fb.ready():
                    return fb.average(), last_frame, last_lms
                if not hinted:
                    print("hold still a moment (capturing)...")
                    hinted = True
                pressed["space"] = False
            time.sleep(0.01)
        return None, None, None

    print("CALIBRATION: stare at each dot, press SPACE. Shift+Q quits.")
    calib_samples = []
    for dot_i, (gx, gy) in enumerate(grid_points(monitor, n=4)):
        overlay.show(gx, gy)
        feats, frame, lms = wait_space()
        if pressed["quit"]:
            overlay.close()
            return 1
        if feats is None:
            print("no valid landmarks, point repeated")
            overlay.hide()
            continue
        calib_samples.append((feats, gx, gy))
        payload = {"features": feats, "target": [gx, gy]}
        if frame is not None and lms is not None:
            tag = f"c{dot_i:02d}"
            save_eye_crops(session, tag, frame, lms)
            payload["crop"] = tag
        append_event(session, "calib", payload)
    overlay.hide()
    if len(calib_samples) < 5:
        print("too few calibration samples.")
        overlay.close()
        return 2
    matrix = fit_calibration(calib_samples)
    append_event(session, "calibration_matrix", {"matrix": matrix})
    append_event(session, "monitor", {"rect": list(monitor)})
    print(f"calibrated on {len(calib_samples)} points. STUDY FREELY.")

    dot_times = dot_schedule(args.seconds)
    dots_cycle = grid_points(monitor)
    start = time.perf_counter()
    dot_idx, next_shot, di, gi = 0, start, 0, 0
    try:
        while time.perf_counter() - start < args.seconds and not pressed["quit"]:
            overlay.root.update()
            elapsed = time.perf_counter() - start
            if dot_idx < len(dot_times) and elapsed >= dot_times[dot_idx]:
                pos = dots_cycle[di % len(dots_cycle)]
                di += 1
                overlay.show(*pos)
                beep()
                shown_at = time.perf_counter()
                pressed["space"] = False
                fix = []
                while time.perf_counter() - shown_at < DOT_SHOW_S and not pressed["quit"]:
                    overlay.root.update()
                    feats, _, _ = snap_features()
                    if feats is not None:
                        fix.append(feats)
                    if pressed["space"]:
                        avg = ([sum(f[j] for f in fix) / len(fix) for j in range(len(fix[0]))]
                               if len(fix) >= 5 else None)
                        append_event(session, "dot", {"pos": list(pos),
                                                      "features_avg": avg})
                        print(f"dot logged at {elapsed:.0f}s pos={[int(p) for p in pos]}")
                        break
                overlay.hide()
                dot_idx += 1
            feats, lms, frame = snap_features()
            if feats is not None:
                gi += 1
                payload = {"features": feats}
                if gi % 5 == 0:
                    payload["landmarks"] = lms
                append_event(session, "gaze", payload)
                if gi % 12 == 0:
                    save_eye_crops(session, gi, frame, lms)
            if time.perf_counter() - next_shot > 30.0:
                left, top, mw, mh = monitor
                full = ImageGrab.grab(all_screens=True)
                shot = full.crop((left, top, left + mw, top + mh))
                thumb = shot.copy()
                thumb.thumbnail((1280, 1280))
                shots_dir = os.path.join(session, "shots")
                os.makedirs(shots_dir, exist_ok=True)
                shot_name = f"shot_{int(time.perf_counter() - start):05d}.png"
                thumb.save(os.path.join(shots_dir, shot_name), format="PNG")
                append_event(session, "screenshot", {
                    "size": list(shot.size), "file": shot_name,
                    "thumb_size": list(thumb.size)})
                next_shot = time.perf_counter()
            time.sleep(0.05)
    finally:
        overlay.close()
        cap.release()
        listener.stop()
        mouse_listener.stop()
    print(f"done. events={len(read_events(session))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
