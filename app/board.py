"""Gaze communication board (T29 product). Eight huge cells plus voice.

Layout: sentence/status bar on top (display), 2x4 phrase grid, function
row (RECAL/SPEAK/CLEAR/SETTINGS/QUIT) at the bottom. All interactive
targets are full cells inside the enrollment band.

Flow: 4x4 enrollment x2 (averaged, split-half fixation gate), then the
board. Gaze moves the highlight; a 0.4 s eye-hold speaks the cell phrase
offline via Windows System.Speech. Cells are ~450x400 px: the accuracy
regime our live error (200-300 px) already meets. A coverage gate blanks
the highlight outside the enrollment hull (Online-EYE finding).
Usage: .\\.venv\\Scripts\\python.exe app\\board.py --monitor 1 --camera 0
Quit: hold gaze on QUIT, or Shift+Q.
"""

import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camselect import resolve_camera, resolve_monitor  # noqa: E402
from app.deskkeys import grid_keys, place  # noqa: E402
from app.inject import shift_q_pressed  # noqa: E402
from app.board_config import load_config, save_config  # noqa: E402
from app.keyboard_layout import hit_key  # noqa: E402
from app.speak import set_language, speak  # noqa: E402
from corrector.corrector import BiasCorrector  # noqa: E402
from gaze.blink import LongBlink, mean_ear  # noqa: E402
from gaze.calibration import fit_calibration  # noqa: E402
from gaze.coverage import convex_hull, inside_hull  # noqa: E402
from gaze.clock import MonoClock  # noqa: E402
from gaze.features import extract_features, map_to_screen  # noqa: E402
from gaze.saccade import JumpGate  # noqa: E402
from tools.env_check import estimate_distance_cm, light_label  # noqa: E402
from tools.record_session import (  # noqa: E402
    FixationBuffer,
    list_monitors,
    set_dpi_aware,
)

CELLS = [("SI", "Sí"), ("NO", "No"),
         ("AGUA", "Quiero agua, por favor"),
         ("BAÑO", "Necesito ir al baño"),
         ("AYUDA", "Necesito ayuda, por favor ven"),
         ("GRACIAS", "Gracias"),
         ("LLAMAR", "Por favor ven, te necesito"),
         ("DOLOR", "Me duele, por favor ayúdame")]
PHRASE = dict(CELLS)


def guide_reference(samples):
    """Median comfortable pose (fx, fy, fw) from ratio samples. Pure."""
    if not samples:
        return (0.5, 0.45, 0.20)

    def med(i):
        col = sorted(s[i] for s in samples)
        return col[len(col) // 2]

    return (med(0), med(1), med(2))


def pose_inside(fx, fy, fw, ref):
    """Inside = near YOUR comfortable pose, not camera-frame center.

    Forcing frame center made users contort into unnatural positions
    (web-230837: natural fw 0.20 vs a 0.22-0.48 zone). Pure (tested).
    """
    return (abs(fx - ref[0]) < 0.05 and abs(fy - ref[1]) < 0.06
            and 0.7 * ref[2] < fw < 1.3 * ref[2])


def head_view(lms, mw, mh, img_w=1280.0, img_h=720.0, ref=None):
    """Live head ellipse for the ceremony, mapped from camera space.

    Returns (cx, cy, rx, ry, inside). The ellipse centers on screen when
    the face sits at the sampled comfortable reference pose. Visual
    guide only, never a measurement. Pure (tested).
    """
    if ref is None:
        ref = (0.5, 0.5, 0.30)
    x1, x2 = lms[234][0] / img_w, lms[454][0] / img_w
    y1, y2 = lms[10][1] / img_h, lms[152][1] / img_h
    fx, fy = (x1 + x2) / 2, (y1 + y2) / 2
    fw = x2 - x1
    ex = mw / 2 + (fx - ref[0]) * mw * 0.9
    ey = mh / 2 + (fy - ref[1]) * mh * 0.9
    rx = max(30.0, fw * 1400)
    return ex, ey, rx, rx * 1.3, pose_inside(fx, fy, fw, ref)


def strip_layout(mw, mh):
    """Board geometry: thin display bar on top, function row at bottom.

    The thin top strip (60px buttons) was unreachable: hull coverage fixes
    bias, not the ~280px live variance (board-180002). All interactive
    targets are now full cells inside the enrollment band. Pure (tested):
    returns (funcs, bar_rect); funcs are gaze-held like phrase cells.
    """
    from app.deskkeys import grid_keys

    m = 16
    bar = (m, 16, mw - m, 60)
    fh = int(mh * 0.22)
    fy1 = mh - m - fh
    funcs = grid_keys(["RECAL", "SPEAK", "CLEAR", "SETTINGS", "QUIT"],
                      1, 5, m, fy1, mw - 2 * m, fh)
    return funcs, bar


def phrase_area(mh):
    """Vertical band for the 2x4 phrase grid, clear of bar and funcs."""
    return 80, mh - 16 - int(mh * 0.22) - 12


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=None)
    ap.add_argument("--camera", type=int, default=None)
    args = ap.parse_args()
    set_dpi_aware()
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

    import tkinter as tk

    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    from recorder.session import append_event, new_session

    session = new_session(os.path.join(repo, "data"),
                          time.strftime("board-%Y%m%d-%H%M%S"), meta={})
    print(f"session: {session}")

    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"no_camera: index {cam} did not open.")
        return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    base = mp_python.BaseOptions(
        model_asset_path=os.path.join(repo, "data", "face_landmarker.task"))
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()

    root = tk.Tk()
    root.geometry(f"{mw}x{mh}+{mleft}+{mtop}")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#181818")
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#181818",
                       highlightthickness=0)
    canvas.pack()

    t0 = time.perf_counter()
    state = {"done": False, "said": [], "started": None}
    ear_gate = [None]

    def snap():
        ok, frame = cap.read()
        if not ok:
            return None, None, {}, None
        gray_mean = float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        res = landmarker.detect_for_video(mp_image, clock.now_ms())
        if not res.face_landmarks:
            return None, None, {"brightness": gray_mean}, None
        h, w = frame.shape[:2]
        lms = [(p.x * w, p.y * h) for p in res.face_landmarks[0]]
        feats, valid, _ = extract_features(lms)
        ear = mean_ear(lms)
        face_px = lms[454][0] - lms[234][0]
        hud = {"brightness": gray_mean,
               "distance_cm": estimate_distance_cm(face_px, w)}
        if ear is not None and ear_gate[0] is not None and ear < ear_gate[0]:
            feats = None
        return (feats if valid else None), ear, hud, lms

    print("CALIBRATION")
    grid = [(mleft + mw * fx, mtop + mh * fy)
            for fy in (0.08, 0.36, 0.64, 0.92)
            for fx in (0.08, 0.36, 0.64, 0.92)]
    calib, ear_open = [], []

    CREAM, COFFEE, GREEN, GREEN_SOFT, CARAMEL = (
        "#f7f2e9", "#221812", "#1b8c4a", "#7fc79b", "#b96f1a")

    def ceremony_guide():
        # Pre-step: learn the user's comfortable pose (1.6 s sampling),
        # then ask them to hold it. "Centered" means near that reference,
        # never at camera-frame center (web-230837: contorting users).
        # Auto-advances; never blocks.
        def ratios(lms):
            return (((lms[234][0] + lms[454][0]) / 2) / 1280.0,
                    ((lms[10][1] + lms[152][1]) / 2) / 720.0,
                    (lms[454][0] - lms[234][0]) / 1280.0)

        samples = []
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 1.6:
            _f, _e, _h, lms = snap()
            if lms is not None:
                samples.append(ratios(lms))
            try:
                canvas.delete("all")
                canvas.create_text(mw // 2, 90, text="PASO 1 · TU ROSTRO",
                                   fill=CARAMEL, font=("Arial", 16, "bold"))
                canvas.create_text(
                    mw // 2, mh - 60,
                    text="ponte cómodo · así como te sientas siempre",
                    fill=COFFEE, font=("Arial", 22))
                root.update()
            except Exception:
                return
        ref = guide_reference(samples)
        t0, stable, last = time.perf_counter(), 0.0, time.perf_counter()
        while True:
            _f, _e, _h, lms = snap()
            now = time.perf_counter()
            try:
                canvas.delete("all")
                canvas.create_text(mw // 2, 90, text="PASO 1 · TU ROSTRO",
                                   fill=CARAMEL, font=("Arial", 16, "bold"))
                cx, cy, rx, ry = mw // 2, mh // 2, 200, 265
                canvas.create_oval(cx - rx, cy - ry, cx + rx, cy + ry,
                                   outline=CARAMEL, width=3)
                msg = "busca tu rostro…"
                if lms is not None:
                    ex, ey, erx, ery, inside = head_view(lms, mw, mh, ref=ref)
                    col = GREEN if inside else CARAMEL
                    canvas.create_oval(ex - erx, ey - ery, ex + erx, ey + ery,
                                       outline=col, width=5)
                    stable = stable + (now - last) if inside else 0.0
                    msg = ("esa es tu postura · empezamos…"
                           if inside else "vuelve a tu postura cómoda")
                else:
                    stable = 0.0
                last = now
                canvas.create_text(mw // 2, mh - 60, text=msg,
                                   fill=COFFEE, font=("Arial", 22))
                root.update()
            except Exception:
                return
            if stable >= 1.2 or now - t0 > 6.0:
                return

    def ceremony_dot(gx, gy, done_n, total, t0_dot, captured=False):
        canvas.delete("all")
        barw = int(mw * 0.5)
        x0 = mw // 2 - barw // 2
        canvas.create_rectangle(x0, 44, x0 + barw, 52, fill="#e4d8c4",
                                outline="")
        fw = int(barw * done_n / max(total, 1))
        if fw > 0:
            canvas.create_rectangle(x0, 44, x0 + fw, 52, fill=GREEN,
                                    outline="")
        canvas.create_text(mw // 2, 88,
                           text=f"CALIBRACIÓN · {done_n}/{total}",
                           fill=CARAMEL, font=("Arial", 15, "bold"))
        dx, dy = gx - mleft, gy - mtop
        if captured:
            canvas.create_oval(dx - 48, dy - 48, dx + 48, dy + 48,
                               fill=GREEN, outline="")
            canvas.create_text(dx, dy, text="✓", fill="#ffffff",
                               font=("Arial", 30, "bold"))
            label = "punto guardado"
        else:
            r = 34 + int(5 * math.sin((time.perf_counter() - t0_dot) * 3))
            canvas.create_oval(dx - r - 12, dy - r - 12, dx + r + 12,
                               dy + r + 12, outline=GREEN_SOFT, width=3)
            canvas.create_oval(dx - r, dy - r, dx + r, dy + r,
                               fill=GREEN, outline="")
            label = "mira el punto verde · rostro quieto"
        canvas.create_text(mw // 2, mh - 60, text=label,
                           fill=GREEN if captured else COFFEE,
                           font=("Arial", 20))
        root.update()

    def calibrate():
        del calib[:], ear_open[:]
        plan = grid * 2
        total = len(plan)
        try:
            canvas.configure(bg=CREAM)
            # Stale gate from a previous fit stalls dots (beta-093037).
            ear_gate[0] = None
            ceremony_guide()
            done_n = 0
            for gx, gy in plan:
                fb = FixationBuffer(min_frames=12)
                done_n += 1
                t0_dot = time.perf_counter()
                while not fb.ready():
                    feats, ear, _, _ = snap()
                    fb.add(feats)
                    if ear is not None:
                        ear_open.append(ear)
                    try:
                        ceremony_dot(gx, gy, done_n, total, t0_dot)
                    except Exception:
                        return
                ceremony_dot(gx, gy, done_n, total, t0_dot, captured=True)
                time.sleep(0.16)
                calib.append((fb.average(), gx, gy))
                append_event(session, "calib",
                             {"features": fb.average(), "target": [gx, gy]})
        finally:
            canvas.configure(bg="#181818")

    def refit():
        calibrate()
        if len(calib) < 16:
            raise ValueError(f"calibration interrupted ({len(calib)} samples)")
        samples = [(f, x, y) for f, x, y in calib]
        matrix = fit_calibration(samples)
        append_event(session, "calibration_matrix", {"matrix": matrix})
        means = [sum(s[0][j] for s in samples) / len(samples) for j in range(7)]
        return matrix, means, samples

    corrector, blink, hull = [None], [None], [None]

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
        hull[0] = convex_hull([(gx, gy) for _, gx, gy in samples])
        ear_open.sort()
        med = ear_open[len(ear_open) // 2] if ear_open else 0.30
        # Board holds: 0.4 s. The 171805 ear tape shows deliberate
        # closures at 0.4-1.0 s (three 0.4-0.5 s attempts were eaten by the
        # 0.5 s line, one missed by 10 ms) while true naturals stay <=0.2 s.
        # Huge cells keep false selections cheap.
        blink[0] = LongBlink(ear_threshold=min(0.25, max(0.12, med * 0.6)),
                             hold_s=0.4)
        ear_gate[0] = blink[0].ear_threshold
        print(f"EAR: open_median={med:.3f} threshold={blink[0].ear_threshold:.3f}")

    refit_all()

    _py0, _py1 = phrase_area(mh)
    cells = grid_keys([c[0] for c in CELLS], 2, 4, 16, _py0, mw - 32,
                      _py1 - _py0)
    # Function buttons are full cells in the bottom row, inside the
    # enrollment band (a thin top strip was unreachable: board-180002).
    funcs, bar_rect = strip_layout(mw, mh)
    cfg_path = os.path.join(repo, "data", "board_config.json")
    cfg = load_config(cfg_path, [c[0] for c in CELLS])
    PHRASE.update(cfg["phrases"])
    set_language(cfg["voice_lang"])
    state["started"] = time.perf_counter()
    state["sentence"] = []

    def do_recalibrate():
        if state.get("calibrating"):
            return
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
        state["calibrating"] = False

    root.bind("<Key>", lambda e: do_recalibrate() if e.keysym == "r" else None)

    def speak_sentence():
        text = ". ".join(state["sentence"])
        if text:
            speak(text)
            append_event(session, "speak_all", {"text": text})

    def do_quit(now):
        state["done"] = True
        import json as _json

        with open(os.path.join(session, "ear_stream.json"), "w") as fh:
            _json.dump(ear_stream, fh)
        print(f"done: said={state['said']} secs={now - state['started']:.0f}")
        root.after(500, root.destroy)

    def fire_cell(target, source, ear, now):
        # Shared by gaze holds (certain anchor) and caregiver mouse clicks
        # (no anchor: the user's gaze is not necessarily on the cell).
        phrase = PHRASE[target]
        speak(phrase)
        state["said"].append(target)
        state["sentence"].append(phrase)
        verdict = "no_anchor"
        if source == "gaze":
            pre = [f for t, f in feat_history if t <= now - 0.7]
            if pre:
                for k in cells:
                    if k["label"] == target:
                        x1, y1, x2, y2 = k["rect"]
                        stt, info = corrector[0].update(
                            pre[-1],
                            ((x1 + x2) / 2 + mleft, (y1 + y2) / 2 + mtop),
                            certain=True)
                        verdict = f"{stt}:{info.get('residual', 0):.0f}"
                        break
        append_event(session, "selection",
                     {"key": target, "phrase": phrase, "ear": ear,
                      "anchor": verdict, "source": source})

    def on_click(event):
        if state["done"] or state.get("calibrating"):
            return
        now = time.perf_counter()
        label = hit_key(cells + funcs, event.x, event.y)
        if label == "QUIT":
            do_quit(now)
        elif label == "RECAL":
            do_recalibrate()
        elif label == "SPEAK":
            speak_sentence()
        elif label == "CLEAR":
            state["sentence"] = []
            append_event(session, "clear", {})
        elif label == "SETTINGS":
            open_settings()
        elif label is not None and label in PHRASE:
            fire_cell(label, "mouse", None, now)
        else:
            x1, y1, x2, y2 = bar_rect
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                speak_sentence()

    settings_win = [None]

    def open_settings():
        # Caregiver-operated (mouse + keyboard): voice language plus one
        # editable phrase per cell, saved to data/board_config.json and
        # applied live. Gaze can open it via the SETTINGS hold.
        if settings_win[0] is not None:
            try:
                settings_win[0].lift()
                return
            except Exception:
                settings_win[0] = None
        win = tk.Toplevel(root)
        win.title("Mirada · Ajustes")
        win.geometry(f"560x600+{mleft + mw // 2 - 280}+{mtop + mh // 2 - 300}")
        win.configure(bg="#141210")
        settings_win[0] = win
        tk.Label(win, text="Voz", font=("Arial", 14, "bold"),
                 bg="#141210", fg="#f2ede4").pack(pady=(14, 4))
        lang = tk.StringVar(value=cfg["voice_lang"])
        row = tk.Frame(win, bg="#141210")
        row.pack()
        for code, name in (("es", "Español"), ("en", "English")):
            tk.Radiobutton(row, text=name, variable=lang, value=code,
                           font=("Arial", 13), bg="#141210", fg="#f2ede4",
                           selectcolor="#221c15",
                           activebackground="#141210",
                           activeforeground="#f2ede4").pack(side="left", padx=12)
        tk.Label(win, text="Frases por celda", font=("Arial", 14, "bold"),
                 bg="#141210", fg="#f2ede4").pack(pady=(14, 4))
        entries = {}
        for label, _default in CELLS:
            fr = tk.Frame(win, bg="#141210")
            fr.pack(fill="x", padx=20, pady=2)
            tk.Label(fr, text=label, font=("Arial", 12), width=9,
                     anchor="w", bg="#141210", fg="#a89a86").pack(side="left")
            var = tk.StringVar(value=PHRASE[label])
            tk.Entry(fr, textvariable=var, font=("Arial", 12), width=38,
                     bg="#221c15", fg="#f2ede4",
                     insertbackground="#f2ede4").pack(side="left")
            entries[label] = var

        def save_close():
            phrases = {label: var.get().strip() for label, var in entries.items()
                       if var.get().strip()}
            try:
                save_config(cfg_path, lang.get(), phrases)
            except Exception as e:
                print(f"settings save failed: {e}")
                return
            PHRASE.update(phrases)
            set_language(lang.get())
            cfg["voice_lang"] = lang.get()
            append_event(session, "settings_saved",
                         {"voice_lang": lang.get(), "n_phrases": len(phrases)})
            print(f"settings saved: voice={lang.get()} phrases={len(phrases)}")
            settings_win[0] = None
            win.destroy()

        btns = tk.Frame(win, bg="#141210")
        btns.pack(pady=16)
        tk.Button(btns, text="Guardar", font=("Arial", 13, "bold"),
                  bg="#e8a33d", fg="#141210", width=12,
                  command=save_close).pack(side="left", padx=8)
        tk.Button(btns, text="Cerrar", font=("Arial", 13),
                  bg="#221c15", fg="#f2ede4", width=12,
                  command=lambda: (settings_win.__setitem__(0, None),
                                   win.destroy())).pack(side="left", padx=8)

    canvas.bind("<Button-1>", on_click)
    smooth = {"x": None, "y": None}
    # agree 250px: saccade predicts scatter ~280px on this map, so the
    # default 150px window reset candidacies forever (board-180002: jumps
    # never confirmed, only slow sweeps worked). Board-only: beta keeps 150.
    gate = JumpGate(agree_px=250.0)
    feat_window, kb_history, feat_history = [], [], []
    last_hl = [None]  # frozen across invalid frames (else closure erases it)
    ear_stream = []  # (t, ear or -1): full tape to diagnose hold fates

    def draw(hl, covered, hud):
        canvas.delete("all")
        for k in cells:
            x1, y1, x2, y2 = k["rect"]
            active = k["label"] == hl
            fill = "#ffd54a" if active and covered else \
                "#8a6d1a" if active else "#2e2e2e"
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill,
                                    outline="#666666", width=3)
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=k["label"],
                               fill="#111111" if active else "#eeeeee",
                               font=("Arial", 44, "bold"))
        for k in funcs:
            x1, y1, x2, y2 = k["rect"]
            cactive = k["label"] == hl
            canvas.create_rectangle(x1, y1, x2, y2,
                                    fill="#ffd54a" if cactive else "#4a1f1f",
                                    outline="#666666", width=3)
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=k["label"],
                               fill="#111111" if cactive else "#ffcccc",
                               font=("Arial", 32, "bold"))
        # The bar doubles as the status line: warnings left (priority over
        # the sentence), hold progress or light/distance right.
        x1, y1, x2, y2 = bar_rect
        canvas.create_rectangle(x1, y1, x2, y2, fill="#1e1e1e",
                                outline="#666666", width=2)
        mid = (y1 + y2) // 2
        if state.get("face_msg"):
            left, lfill = state["face_msg"], "#ff8a65"
        elif not covered:
            left, lfill = "gaze outside trusted area", "#ff8a65"
        else:
            left = "  ·  ".join(state["sentence"])
            if len(left) > 60:
                left = "…" + left[-59:]
            lfill = "#9ccc65" if left else "#757575"
            left = left or "mira + hold para hablar…"
        canvas.create_text(x1 + 14, mid, text=left, fill=lfill,
                           font=("Arial", 20), anchor="w")
        if blink[0].holding():
            frac = min(1.0, blink[0].hold_time(time.perf_counter())
                       / blink[0].hold_s)
            right, rfill = f"HOLD {'#' * int(frac * 10):<10}", "#ffd54a"
        elif hud.get("brightness") is not None:
            right = (f"{light_label(hud['brightness'])} "
                     f"{hud['brightness']:.0f} | "
                     f"{hud.get('distance_cm') or 0:.0f}cm")
            rfill = "#9e9e9e"
        else:
            right, rfill = "", "#9e9e9e"
        canvas.create_text(x2 - 14, mid, text=right, fill=rfill,
                           font=("Arial", 18), anchor="e")
        root.update()

    def loop():
        if state["done"]:
            return
        if state.get("calibrating"):
            root.after(100, loop)
            return
        feats, ear, hud, lms = snap()
        now = time.perf_counter()
        # Frontal gate: in profile view the projected eye collapses and EAR
        # fakes a closure (board-115314: looking away read as HOLD). Freeze
        # both channels until the face returns.
        frontal = False
        face_msg = ""
        if lms is not None:
            fw = lms[454][0] - lms[234][0]
            cx = (lms[454][0] + lms[234][0]) / 2.0
            frontal = fw > 0 and abs(lms[1][0] - cx) / fw < 0.35
            if not frontal:
                face_msg = "face the screen"
                feats, ear = None, None
        elif ear is None:
            face_msg = "NO FACE - come back to the camera"
        state["face_msg"] = face_msg
        select_event = blink[0].update(ear, now) == "select"
        ear_stream.append((round(now - state["started"], 3),
                           round(ear, 3) if ear is not None else -1.0))
        hl, covered = None, True
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
            # would be dropped while the detector already fired (here: holds
            # completed on jumping transition frames, 0 selections recorded).
            # Saccades are confirmed, not rejected: 3 agreeing frames snap.
            if smooth["x"] is None:
                smooth["x"], smooth["y"] = px, py
                gate.reset()
            else:
                eyes_open = ear is not None and ear > blink[0].ear_threshold
                verdict = gate.check(px, py, feats, smooth["x"], smooth["y"],
                                     eyes_open=eyes_open)
                if verdict == "drop":
                    if feat_window:
                        feat_window.pop()
                elif verdict == "snap":
                    pts = gate.points
                    smooth["x"] = sum(p[0] for p in pts) / len(pts)
                    smooth["y"] = sum(p[1] for p in pts) / len(pts)
                    del feat_window[:]
                    feat_window.extend(gate.frames)
                    gate.reset()
                else:
                    smooth["x"] = 0.4 * px + 0.6 * smooth["x"]
                    smooth["y"] = 0.4 * py + 0.6 * smooth["y"]
            covered = inside_hull((smooth["x"], smooth["y"]), hull[0],
                                        margin=40.0)
            last_hl[0] = hit_key(cells + funcs, smooth["x"] - mleft,
                                 smooth["y"] - mtop)
        hl = last_hl[0]
        kb_history.append((now, hl))
        while len(kb_history) > 90:
            kb_history.pop(0)
        if now - state.get("last_log", 0) > 0.5:
            state["last_log"] = now
            append_event(session, "trace",
                         {"gaze": [smooth["x"], smooth["y"]], "hl": hl,
                          "ear": ear, "covered": covered,
                          "brightness": hud.get("brightness"),
                          "distance_cm": hud.get("distance_cm"),
                          "holding": blink[0].holding(),
                          "hold_s": round(blink[0].hold_time(now), 2)})
        draw(hl, covered, hud)
        force_quit = shift_q_pressed()
        if select_event or force_quit:
            past = [h for t, h in kb_history if t <= now - 0.45]
            target = "QUIT" if force_quit else (past[-1] if past else hl)
            if select_event and not force_quit:
                append_event(session, "trigger",
                             {"target": target, "hl_now": hl})
            if target == "QUIT":
                do_quit(now)
                return
            if target == "RECAL":
                do_recalibrate()
                state["started"] = time.perf_counter()
            elif target == "SPEAK":
                speak_sentence()
            elif target == "CLEAR":
                state["sentence"] = []
                append_event(session, "clear", {})
            elif target == "SETTINGS":
                open_settings()
            elif target is not None and target in PHRASE:
                fire_cell(target, "gaze", ear, now)
        root.after(33, loop)

    root.after(33, loop)
    root.mainloop()
    cap.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
