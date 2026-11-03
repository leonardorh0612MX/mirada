"""Web board (D11): same engine as app/board.py, browser front-end.

Splash, pickers, ceremony and board are site/board.html served by a stdlib
server on localhost; gaze state streams over SSE (~30 fps), mouse clicks
POST back. The Tkinter board stays as the verified fallback.
Usage: .\\.venv\\Scripts\\python.exe app\\board_web.py
Quit: QUIT cell/button or Shift+Q.
"""

import argparse
import base64
import io
import json
import math
import os
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.board import (PHRASE, enrollment_plan,  # noqa: E402
                       guide_reference, natural_block_indices, phrase_area,
                       pose_inside, strip_layout)
from app.board_config import load_config, save_config  # noqa: E402
from app.i18n import (cells_for_lang, funcs_for_lang, norm_lang,  # noqa: E402
                      s)
from corrector.fusion import (PostureGuard, SelectionCooldown,  # noqa: E402
                              enrollment_spread)
from app.camselect import available_cameras, available_monitors  # noqa: E402
from app.deskkeys import grid_keys  # noqa: E402
from app.inject import click_at, send_text, shift_q_pressed  # noqa: E402
from app.keyboard_layout import board_keyboard, hit_key, type_text  # noqa: E402
from app.words import apply_suggestion, current_prefix, load_words, suggest  # noqa: E402
from app.apps import open_app  # noqa: E402
from app.speak import set_language, speak, voice_status  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = threading.Lock()
STATE = {
    "phase": "setup", "gaze": None, "hl": None, "holding": False,
    "hold_frac": 0.0, "covered": True, "face_msg": "", "bright": None,
    "dist": None, "sentence": [], "busy": False, "open_settings": False,
    "voice_lang": "en", "phrases": {}, "page": "frases", "launched": None,
    "dwell_frac": 0.0, "lang": "en",
    "armed": None, "typed": "", "kb_v": 0,
    "calib": {"n": 0, "total": 32, "dot": None, "captured": False},
    "guide": None, "said": 0,
}
class AppDwell:
    """Stable-gaze click for app mode. Pure timing logic.

    Blink-hold clicks fired all over Discord in web-20261101-230023
    (11 clicks while just looking around). A click needs the gaze to
    rest within radius_px for dwell_s, then a refractory window.
    Jitter never sits still, so samples accumulate around a running
    centroid and the click lands on that centroid - not on the live
    (wandering) point. progress() drives the ring's fill arc.
    """

    def __init__(self, radius_px=130.0, dwell_s=1.0, refractory_s=2.0):
        self.radius_px = radius_px
        self.dwell_s = dwell_s
        self.refractory_s = refractory_s
        self._sx = 0.0
        self._sy = 0.0
        self._n = 0
        self._t0 = 0.0
        self._until = 0.0

    def reset(self):
        self._n = 0

    @property
    def centroid(self):
        if not self._n:
            return None
        return (self._sx / self._n, self._sy / self._n)

    def progress(self, now):
        if not self._n or now < self._until:
            return 0.0
        return min(1.0, (now - self._t0) / self.dwell_s)

    def update(self, x, y, now):
        if now < self._until:
            self._n = 0
            return False
        if not self._n:
            self._sx, self._sy, self._n, self._t0 = x, y, 1, now
            return False
        cx, cy = self.centroid
        if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 > self.radius_px:
            self._sx, self._sy, self._n, self._t0 = x, y, 1, now
            return False
        self._sx += x
        self._sy += y
        self._n += 1
        if now - self._t0 >= self.dwell_s:
            self._until = now + self.refractory_s
            return True
        return False


CMDQ = queue.Queue()
SETUP = {"choice": None}
FS_EVENT = threading.Event()  # page asks the native window to toggle fullscreen
RETURN_EVENT = threading.Event()  # overlay asks to bring the board back
KB_EVENT = threading.Event()  # overlay asks for the keyboard page
PROBE_CAPS = {}


def state_set(**kw):
    with LOCK:
        STATE.update(kw)


def state_get():
    with LOCK:
        return dict(STATE)


class Server(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            path = os.path.join(REPO, "site", "board.html")
            with open(path, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/icon-m.svg", "/bust.png"):
            name = self.path.lstrip("/")
            path = os.path.join(REPO, "site", name)
            if not os.path.exists(path):
                self.send_response(404)
                self.end_headers()
                return
            with open(path, "rb") as fh:
                body = fh.read()
            ctype = "image/png" if name.endswith(".png") else "image/svg+xml"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/icon.svg":
            path = os.path.join(REPO, "site", "icon.svg")
            with open(path, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    payload = json.dumps(state_get())
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(1 / 30)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
        elif self.path == "/monitors":
            out = []
            for i, (_l, _t, w, h), shot in available_monitors():
                buf = io.BytesIO()
                shot.save(buf, "JPEG", quality=70)
                out.append({"idx": i, "w": w, "h": h,
                            "img": base64.b64encode(buf.getvalue()).decode()})
            self._json(out)
        elif self.path == "/cameras":
            self._json([{"idx": i} for i in sorted(PROBE_CAPS)])
        elif self.path.startswith("/cam/"):
            idx = int(self.path.split("/")[2].split(".")[0])
            entry = PROBE_CAPS.get(idx)
            if entry is None:
                self.send_response(404)
                self.end_headers()
                return
            cap, lock, cache = entry
            import cv2

            now = time.monotonic()
            if cache["jpg"] is not None and now - cache["t"] < 0.25:
                body = cache["jpg"]
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            with lock:
                ok, frame = cap.read()
            if not ok or frame is None:
                self.send_response(204)
                self.end_headers()
                return
            ok, enc = cv2.imencode(".jpg", frame,
                                   [cv2.IMWRITE_JPEG_QUALITY, 72])
            body = enc.tobytes()
            cache.update(t=now, jpg=body)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        kind = body.get("kind")
        if kind == "setup":
            SETUP["choice"] = (int(body["camera"]), int(body["monitor"]),
                               body.get("lang") if body.get("lang") in
                               ("en", "es") else "en")
            self._json({"ok": True})
        elif kind == "quit":
            CMDQ.put(("quit", None))
            self._json({"ok": True})
        elif kind == "click":
            CMDQ.put(("click", body.get("label")))
            self._json({"ok": True})
        elif kind == "settings":
            CMDQ.put(("settings", body))
            self._json({"ok": True})
        elif kind == "settings_close":
            CMDQ.put(("settings_close", None))
            self._json({"ok": True})
        elif kind == "fullscreen":
            FS_EVENT.set()
            self._json({"ok": True})
        elif kind == "back":
            RETURN_EVENT.set()
            self._json({"ok": True})
        elif kind == "keyboard":
            KB_EVENT.set()
            self._json({"ok": True})
        else:
            self._json({"ok": False}, 400)


def engine(notify_done):
    import cv2
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    import mediapipe as mp

    from corrector.corrector import BiasCorrector
    from gaze.blink import LongBlink, mean_ear
    from gaze.calibration import fit_calibration
    from gaze.clock import MonoClock
    from gaze.coverage import convex_hull, inside_hull
    from gaze.features import extract_features, map_to_screen
    from gaze.saccade import JumpGate
    from recorder.session import append_event, new_session
    from tools.env_check import estimate_distance_cm, light_label
    from tools.record_session import (FixationBuffer, list_monitors,
                                      set_dpi_aware)

    set_dpi_aware()
    monitors = list_monitors()
    session = new_session(os.path.join(REPO, "data"),
                          time.strftime("web-%Y%m%d-%H%M%S"), meta={})
    print(f"session: {session}")
    cfg_path = os.path.join(REPO, "data", "board_config.json")

    # Probe cameras for the picker (released once setup is chosen).
    for idx, cap in available_cameras():
        PROBE_CAPS[idx] = (cap, threading.Lock(), {"t": 0.0, "jpg": None})
    print(f"cameras: {sorted(PROBE_CAPS)}")

    while SETUP["choice"] is None:
        if shift_q_pressed():
            notify_done()
            return
        time.sleep(0.1)
    # Language is chosen on the setup screen (default English): it drives
    # cells, funcs, default apps, phrases, TTS voice and calib cues.
    cam_idx, mon_idx, lang = SETUP["choice"]
    lang = norm_lang(lang)
    for idx, (cap, _lk, _cache) in list(PROBE_CAPS.items()):
        cap.release()
    PROBE_CAPS.clear()
    lang_cells = cells_for_lang(lang)
    cfg = load_config(cfg_path, [c[0] for c in lang_cells], lang)
    PHRASE.clear()
    PHRASE.update(dict(lang_cells))
    PHRASE.update(cfg["phrases"])
    set_language(lang)
    cfg["voice_lang"] = lang
    print(f"voices: {voice_status()}")
    state_set(phrases=dict(PHRASE), voice_lang=lang, lang=lang)
    if mon_idx >= len(monitors):
        mon_idx = 0
    mleft, mtop, mw, mh = monitors[mon_idx]
    append_event(session, "setup", {"camera": cam_idx, "monitor": mon_idx,
                                    "rect": [mleft, mtop, mw, mh],
                                    "lang": lang})
    _py0, _py1 = phrase_area(mh)
    cells = grid_keys([c[0] for c in lang_cells], 2, 4, 16, _py0, mw - 32,
                      _py1 - _py0)
    app_entries = cfg["apps"]
    apps_cells = grid_keys([a["label"] for a in app_entries], 2, 4, 16,
                           _py0, mw - 32, _py1 - _py0)
    _f5, bar_rect = strip_layout(mw, mh)
    _fy = _f5[0]["rect"][1]
    _fh = _f5[0]["rect"][3] - _f5[0]["rect"][1]

    def _func_row(row):
        pairs = funcs_for_lang(lang, row)
        keys = grid_keys([label for _fid, label in pairs], 1, len(pairs),
                         16, _fy, mw - 32, _fh)
        for k, (fid, _label) in zip(keys, pairs):
            k["key"] = fid
        return keys

    funcs_main = _func_row("main")
    funcs_apps = _func_row("apps")
    funcs_kb = _func_row("kb")
    func_ids = {}
    for _row in (funcs_main, funcs_apps, funcs_kb):
        for _k in _row:
            func_ids[_k["label"]] = _k["key"]
    send_label = next(label for label, fid in func_ids.items()
                      if fid == "send")
    kb_keys = board_keyboard(mw, _py0 + 64, _py1 - _py0 - 64)
    words_list = load_words(lang=lang)
    typed = {"text": ""}
    sug = {"keys": []}
    page = {"cur": "frases"}

    def active_cells():
        if page["cur"] == "apps":
            return apps_cells
        if page["cur"] == "teclado":
            return kb_keys + sug["keys"]
        return cells

    def active_funcs():
        if page["cur"] == "apps":
            return funcs_apps
        if page["cur"] == "teclado":
            return funcs_kb
        return funcs_main

    def frac_rect(r):
        return [r[0] / mw, r[1] / mh, (r[2] - r[0]) / mw, (r[3] - r[1]) / mh]

    def _pack(keys):
        return [{"label": c["label"], "rect": frac_rect(c["rect"])}
                for c in keys]

    layout_state = {"cells": _pack(cells), "apps": _pack(apps_cells),
                    "funcs_main": _pack(funcs_main),
                    "funcs_apps": _pack(funcs_apps),
                    "funcs_kb": _pack(funcs_kb), "kb": _pack(kb_keys),
                    "kb_sug": [], "bar": frac_rect(bar_rect)}
    state_set(layout=layout_state, page="frases", launched=None)

    def refresh_kb():
        words_now = suggest(current_prefix(typed["text"]), words_list, 3)
        sug["keys"] = grid_keys(words_now, 1, max(1, len(words_now)), 16,
                                _py0, mw - 32, 56) if words_now else []
        layout_state["kb_sug"] = _pack(sug["keys"])
        state_set(typed=typed["text"],
                  kb_v=state_get()["kb_v"] + 1,
                  layout=dict(layout_state))

    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"no_camera: index {cam_idx} did not open.")
        notify_done()
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    base = mp_python.BaseOptions(
        model_asset_path=os.path.join(REPO, "data", "face_landmarker.task"))
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base, running_mode=mp_vision.RunningMode.VIDEO, num_faces=1)
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    clock = MonoClock()
    ear_gate = [None]
    state = {"done": False, "said": [], "sentence": [], "started": None}

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

    calib, ear_open = [], []
    corrector, blink, hull = [None], [None], [None]
    guard, frozen = [None], [False]
    cooldown = SelectionCooldown(2.5)

    def calibrate():
        del calib[:], ear_open[:]
        ear_gate[0] = None  # stale gate stalls dots (beta-093037 lesson)
        # Head guide: learn the comfortable pose (1.6 s), then hold it.
        # "Centered" is relative to that reference, never frame center.
        state_set(phase="guide")

        def ratios(lms):
            return (((lms[234][0] + lms[454][0]) / 2) / 1280.0,
                    ((lms[10][1] + lms[152][1]) / 2) / 720.0,
                    (lms[454][0] - lms[234][0]) / 1280.0)

        samples = []
        t_s = time.perf_counter()
        while time.perf_counter() - t_s < 1.6:
            _f, _e, _hud, lms = snap()
            state_set(bright=(_hud or {}).get("brightness"),
                      dist=(_hud or {}).get("distance_cm"))
            if lms is not None:
                fx, fy, fw = ratios(lms)
                samples.append((fx, fy, fw))
                state_set(guide={"fx": fx, "fy": fy, "fw": fw,
                                 "ref": None, "inside": False,
                                 "stage": "sit"})
            else:
                state_set(guide=None)
        ref = guide_reference(samples)
        state_set(guide_ref=list(ref))
        t0, stable, last = time.perf_counter(), 0.0, time.perf_counter()
        while True:
            _f, _e, _hud, lms = snap()
            state_set(bright=(_hud or {}).get("brightness"),
                      dist=(_hud or {}).get("distance_cm"))
            now = time.perf_counter()
            if lms is not None:
                fx, fy, fw = ratios(lms)
                inside = pose_inside(fx, fy, fw, ref)
                state_set(guide={"fx": fx, "fy": fy, "fw": fw,
                                 "ref": list(ref),
                                 "inside": bool(inside), "stage": "hold"})
                stable = stable + (now - last) if inside else 0.0
            else:
                state_set(guide=None)
                stable = 0.0
            last = now
            if stable >= 1.2 or now - t0 > 6.0:
                break
        state_set(phase="calib", guide=None)
        plan = [(mleft + mw * fx, mtop + mh * fy, msg)
                for fx, fy, msg in enrollment_plan(lang)]
        for n, (gx, gy, msg) in enumerate(plan, 1):
            fb = FixationBuffer(min_frames=12)
            state_set(calib={"n": n, "total": len(plan),
                             "dot": [(gx - mleft) / mw, (gy - mtop) / mh],
                             "captured": False, "msg": msg})
            while not fb.ready():
                feats, ear, _, _ = snap()
                fb.add(feats)
                if ear is not None:
                    ear_open.append(ear)
            state_set(calib={"n": n, "total": len(plan),
                             "dot": [(gx - mleft) / mw, (gy - mtop) / mh],
                             "captured": True, "msg": msg})
            calib.append((fb.average(), gx, gy))
            append_event(session, "calib",
                         {"features": fb.average(), "target": [gx, gy]})
            time.sleep(0.16)

    def refit():
        calibrate()
        if len(calib) < 16:
            raise ValueError(f"calibration interrupted ({len(calib)})")
        samples = [(f, x, y) for f, x, y in calib]
        matrix = fit_calibration(samples)
        append_event(session, "calibration_matrix", {"matrix": matrix})
        means = [sum(s[0][j] for s in samples) / len(samples) for j in range(7)]
        return matrix, means, samples

    def refit_all():
        matrix, means, samples = refit()
        errs = []
        for feats, gx, gy in samples:
            px, py = map_to_screen(feats, matrix)
            errs.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
        err = sum(errs) / len(errs)
        nat = natural_block_indices(len(errs))
        err_nat = sum(errs[i] for i in nat) / len(nat)
        print(f"calibration resub={err:.0f}px (natural {err_nat:.0f}px)")
        append_event(session, "calibration_quality",
                     {"resub_px": err, "resub_natural_px": err_nat})
        if corrector[0] is not None and err_nat > 350:
            print("recalibration REJECTED - keeping old map")
            return
        if corrector[0] is None and err_nat > 300 and not state.get("_retried"):
            state["_retried"] = True
            print("initial fit weak - hold still, enrolling again...")
            refit_all()
            return
        corrector[0] = BiasCorrector(lambda f: map_to_screen(f, matrix),
                                     means, certain_bias_only=True,
                                     trust_px=15.0)
        guard[0] = PostureGuard(enrollment_spread(samples, means))
        frozen[0] = False
        print(f"posture spread={guard[0].limit / 3.0:.4f} "
              f"freeze>{guard[0].limit:.4f}")
        hull[0] = convex_hull([(gx, gy) for _, gx, gy in samples])
        ear_open.sort()
        med = ear_open[len(ear_open) // 2] if ear_open else 0.30
        # Downgaze (SPACE row, bottom cells) narrows open eyes: factor
        # 0.52 keeps shut (minEAR ~0.07-0.11 measured) well separated from
        # downgaze-open (~0.24), where 0.6 straddled holds.
        blink[0] = LongBlink(ear_threshold=min(0.25, max(0.12, med * 0.52)),
                             hold_s=0.4)
        ear_gate[0] = blink[0].ear_threshold
        print(f"EAR: open_median={med:.3f} threshold={blink[0].ear_threshold:.3f}")

    state_set(busy=True)
    refit_all()
    state_set(busy=False, phase="board")
    state["started"] = time.perf_counter()
    smooth = {"x": None, "y": None}
    app_dwell = AppDwell()
    gate = JumpGate(agree_px=250.0)
    feat_window, feat_history, kb_history, ear_stream = [], [], [], []
    last_hl = [None]

    def speak_sentence():
        text = ". ".join(state["sentence"])
        if text:
            speak(text)
            append_event(session, "speak_all", {"text": text})

    def do_quit(now):
        state["done"] = True
        with open(os.path.join(session, "ear_stream.json"), "w") as fh:
            json.dump(ear_stream, fh)
        print(f"done: said={state['said']} "
              f"secs={now - state['started']:.0f}")
        state_set(phase="done")

    def do_recalibrate(now):
        nonlocal smooth, gate
        state_set(busy=True, phase="calib")
        append_event(session, "recalibrate", {})
        print("recalibrating...")
        old_gate = ear_gate[0]
        try:
            smooth = {"x": None, "y": None}
            gate = JumpGate(agree_px=250.0)
            feat_window.clear()
            refit_all()
        except Exception as e:
            ear_gate[0] = old_gate
            print(f"recalibrate aborted: {e}")
        state_set(busy=False, phase="board")
        state["started"] = time.perf_counter()

    def apply_anchor(label, rects, now):
        """Confirmed selection = coarse anchor (tile centre + size)."""
        if frozen[0]:
            return "frozen"  # posture left the regime: don't learn here
        if not cooldown.allow(label, now):
            return "cooldown"  # stuck repeat: speak, but don't teach
        pre = [f for t, f in feat_history if t <= now - 0.7]
        if not pre:
            return "no_anchor"
        for k in rects:
            if k["label"] == label:
                x1, y1, x2, y2 = k["rect"]
                sigma = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 2.0
                stt, info = corrector[0].update(
                    pre[-1], ((x1 + x2) / 2 + mleft, (y1 + y2) / 2 + mtop),
                    certain=True, sigma_px=sigma)
                return f"{stt}:{info.get('residual', 0):.0f}"
        return "no_anchor"

    def fire_cell(target, source, ear, now):
        phrase = PHRASE[target]
        speak(phrase)
        state["said"].append(target)
        state["sentence"].append(phrase)
        state_set(sentence=list(state["sentence"]), said=len(state["said"]))
        verdict = (apply_anchor(target, cells, now)
                   if source == "gaze" else "no_anchor")
        append_event(session, "selection",
                     {"key": target, "phrase": phrase, "ear": ear,
                      "anchor": verdict, "source": source})

    armed = {"label": None, "until": 0.0}

    def fire_app(label, source, now):
        entry = next((a for a in app_entries if a["label"] == label), None)
        if entry is None:
            return
        # Launching is consequential: gaze needs a second confirming hold
        # (a passing gaze fired CORREO/YOUTUBE in web-20261101-122657).
        # The caregiver's mouse click is explicit and fires at once.
        if source == "gaze":
            if armed["label"] != label or now > armed["until"]:
                armed.update(label=label, until=now + 5.0)
                state_set(armed=label)
                append_event(session, "app_arm", {"label": label})
                return
        armed.update(label=None, until=0.0)
        ok, detail = open_app(entry)
        print(f"app launch {label}: ok={ok} ({detail})")
        if source == "gaze":
            apply_anchor(label, apps_cells, now)
        page["cur"] = "frases"
        state_set(launched=label, armed=None, page="frases")
        append_event(session, "app_launch",
                     {"label": label, "ok": ok, "detail": detail,
                      "source": source})

    def fire_kb(label, source, now):
        if any(k["label"] == label for k in sug["keys"]):
            typed["text"] = apply_suggestion(typed["text"], label)
        else:
            typed["text"] = type_text(typed["text"], label)
        if source == "gaze":
            apply_anchor(label, kb_keys + sug["keys"], now)
        refresh_kb()
        append_event(session, "kb_key",
                     {"label": label, "typed": typed["text"],
                      "source": source})

    def do_send(now):
        text = typed["text"].strip()
        if not text:
            return
        typed["text"] = ""
        refresh_kb()
        state_set(launched=send_label)
        append_event(session, "send_text", {"text": text})

        def _inject():
            time.sleep(0.8)  # let the app window take focus first
            try:
                send_text(text + "{ENTER}")
                print(f"sent to app: {text!r}")
            except Exception as e:
                print(f"send failed: {e}")
            time.sleep(5.0)  # browser fallback: auto-return window
            if state_get().get("launched") == send_label:
                state_set(launched=None)

        threading.Thread(target=_inject, daemon=True).start()

    def fire_target(target, source, ear, now):
        # Func dispatch matches stable ids, never display labels: EN and
        # ES rows spell them differently (KEYBOARD/TECLADO, SEND/ENVIAR).
        fid = func_ids.get(target)
        if fid == "quit":
            do_quit(now)
        elif fid == "recal":
            do_recalibrate(now)
        elif fid == "speak":
            if page["cur"] == "teclado":
                if typed["text"].strip():
                    speak(typed["text"].strip())
            else:
                speak_sentence()
        elif fid == "clear":
            state["sentence"] = []
            state_set(sentence=[])
            append_event(session, "clear", {})
        elif fid == "settings":
            state_set(open_settings=True)
        elif fid == "apps":
            page["cur"] = "apps"
            state_set(page="apps")
        elif fid == "phrases":
            page["cur"] = "frases"
            state_set(page="frases")
        elif fid == "keyboard":
            page["cur"] = "teclado"
            state_set(page="teclado")
            refresh_kb()
        elif fid == "send":
            do_send(now)
        elif (page["cur"] == "teclado" and target is not None
              and any(k["label"] == target
                      for k in kb_keys + sug["keys"])):
            fire_kb(target, source, now)
        elif target is not None and any(a["label"] == target
                                        for a in app_entries):
            fire_app(target, source, now)
        elif target is not None and target in PHRASE:
            fire_cell(target, source, ear, now)

    while not state["done"]:
        if RETURN_EVENT.is_set():
            RETURN_EVENT.clear()
            state_set(launched=None)
            append_event(session, "returned", {})
            print("returned to board")
        if KB_EVENT.is_set():
            KB_EVENT.clear()
            page["cur"] = "teclado"
            state_set(launched=None, page="teclado")
            refresh_kb()
            append_event(session, "kb_open", {})
            print("keyboard opened from app")
        # Drain commands first (mouse must never wait on the gaze loop).
        try:
            while True:
                kind, payload = CMDQ.get_nowait()
                if kind == "quit":
                    do_quit(time.perf_counter())
                elif kind == "settings_close":
                    state_set(open_settings=False)
                elif kind == "click":
                    fire_target(payload, "mouse", None, time.perf_counter())
                elif kind == "settings":
                    phrases = payload.get("phrases") or {}
                    known = {c[0] for c in lang_cells}
                    phrases = {k: v.strip() for k, v in phrases.items()
                               if k in known and isinstance(v, str) and v.strip()}
                    # Caregiver may switch the TTS voice only; the session
                    # language (cells, cues) stays as chosen at setup.
                    vlang = payload.get("voice_lang", "en")
                    try:
                        save_config(cfg_path, vlang, phrases, cfg["apps"])
                    except Exception as e:
                        print(f"settings save failed: {e}")
                        continue
                    PHRASE.update(phrases)
                    set_language(vlang)
                    cfg["voice_lang"] = vlang
                    state_set(open_settings=False, phrases=dict(PHRASE),
                              voice_lang=vlang)
                    append_event(session, "settings_saved",
                                 {"voice_lang": vlang,
                                  "n_phrases": len(phrases)})
                    print(f"settings saved: voice={vlang} "
                          f"active={voice_status().get('active')} "
                          f"phrases={len(phrases)}")
        except queue.Empty:
            pass
        if state["done"]:
            break
        if shift_q_pressed():
            do_quit(time.perf_counter())
            break
        if state_get().get("busy"):
            time.sleep(0.05)
            continue
        feats, ear, hud, lms = snap()
        now = time.perf_counter()
        frontal = False
        face_msg = ""
        if lms is not None:
            fw = lms[454][0] - lms[234][0]
            cx = (lms[454][0] + lms[234][0]) / 2.0
            frontal = fw > 0 and abs(lms[1][0] - cx) / fw < 0.35
            if not frontal:
                face_msg = s(lang, "face_turn")
                feats, ear = None, None
        elif ear is None:
            face_msg = s(lang, "face_gone")
        select_event = blink[0].update(ear, now) == "select"
        ear_stream.append((round(now - state["started"], 3),
                           round(ear, 3) if ear is not None else -1.0))
        covered = True
        if feats is not None:
            feat_history.append((now, feats))
            while len(feat_history) > 120:
                feat_history.pop(0)
            feat_window.append(feats)
            while len(feat_window) > 7:
                feat_window.pop(0)
            avg = [sorted(f[j] for f in feat_window)[len(feat_window) // 2]
                   for j in range(len(feats))]
            if guard[0] is not None:
                d = math.dist(avg, corrector[0].means)
                was = frozen[0]
                frozen[0] = guard[0].update(d, now)
                if frozen[0] and not was:
                    print(f"posture drifted (dist={d:.4f}) - "
                          f"learning frozen, press R")
                    append_event(session, "posture_freeze", {"dist": d})
                elif was and not frozen[0]:
                    print("posture recovered - learning resumed")
            px, py = corrector[0].predict(avg)
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
                    # App targets are small and jitter never rests: heavy
                    # smoothing in app mode, responsive on the board.
                    a = 0.15 if state_get().get("launched") else 0.4
                    smooth["x"] = a * px + (1 - a) * smooth["x"]
                    smooth["y"] = a * py + (1 - a) * smooth["y"]
            covered = inside_hull((smooth["x"], smooth["y"]), hull[0],
                                  margin=40.0)
            last_hl[0] = hit_key(active_cells() + active_funcs(),
                                 smooth["x"] - mleft,
                                 smooth["y"] - mtop)
        if frozen[0] and not face_msg:
            face_msg = s(lang, "recal_prompt")
        hl = last_hl[0]
        kb_history.append((now, hl))
        while len(kb_history) > 90:
            kb_history.pop(0)
        gaze_frac = None
        if smooth["x"] is not None:
            gaze_frac = [(smooth["x"] - mleft) / mw, (smooth["y"] - mtop) / mh]
        dwell_frac = 0.0
        if state_get().get("launched"):
            # Eye-mouse inside the opened app: a RESTING gaze clicks
            # (AppDwell), never a blink - blinking while reading fired
            # everywhere. Board cells never fire here (122657 extras).
            if smooth["x"] is not None:
                rel_x = smooth["x"] - mleft
                rel_y = smooth["y"] - mtop
                # Floating dock: two 200x124 tiles at top-right
                # (bbox mw-428..mw, 16..140; see tile_rects). The watcher
                # owns that corner, with a 20 px margin.
                if rel_x > mw - 448 and rel_y < 140:
                    app_dwell.reset()
                elif app_dwell.update(smooth["x"], smooth["y"], now):
                    cx, cy = app_dwell.centroid
                    click_at(cx, cy)
                    append_event(session, "app_click",
                                 {"x": round(cx), "y": round(cy)})
                    print(f"app click at ({cx:.0f},{cy:.0f})")
                    app_dwell.reset()
                else:
                    dwell_frac = app_dwell.progress(now)
        elif select_event:
            past = [h for t, h in kb_history if t <= now - 0.45]
            target = past[-1] if past else hl
            append_event(session, "trigger",
                         {"target": target, "hl_now": hl})
            fire_target(target, "gaze", ear, now)
        state_set(
            gaze=gaze_frac, hl=hl, covered=bool(covered), face_msg=face_msg,
            bright=(hud or {}).get("brightness"),
            dist=(hud or {}).get("distance_cm"),
            holding=blink[0].holding(),
            hold_frac=(min(1.0, blink[0].hold_time(now) / blink[0].hold_s)
                       if blink[0] else 0.0),
            dwell_frac=dwell_frac,
        )
        time.sleep(1 / 60)

    cap.release()
    notify_done()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-open", action="store_true",
                    help="do not auto-open the browser")
    args = ap.parse_args()
    server = Server(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    print(f"mirada web board: {url}")
    done = threading.Event()

    def _run():
        try:
            engine(done.set)
        finally:
            done.set()

    eng = threading.Thread(target=_run, daemon=True)
    eng.start()
    threading.Thread(target=lambda: (done.wait(), server.shutdown()),
                     daemon=True).start()
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
