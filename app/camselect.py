"""Device pickers: cameras and monitors, click to choose.

--camera N / --monitor N keep working untouched. When omitted, devices are
probed: exactly one is used silently, several show a styled window with
live camera previews (wave to tell them apart) or monitor screenshots,
click selects. A closed window cancels with a clean message.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BG, CARD, INK, MUTED, ACCENT = "#141210", "#221c15", "#f2ede4", "#a89a86", "#e8a33d"


def try_open_camera(idx, warmup_frames=3):
    """Open one camera index, validated by streaming frames. Cap or None.

    One good frame is not enough: some DSHOW devices answer the first
    read and then never stream, which used to add a card stuck on its
    skeleton forever (setup hot-plug, Nov 2). Require warmup_frames
    consecutive frames; a slow starter simply appears on a later scan.
    """
    import cv2

    try:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    except Exception:
        return None
    if not cap.isOpened():
        return None
    for _ in range(max(warmup_frames, 1)):
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            return None
    return cap


def available_cameras(max_n=5):
    """Open each index, keep the ones yielding a frame. Returns [(idx, cap)]."""
    found = []
    for i in range(max_n):
        cap = try_open_camera(i)
        if cap is not None:
            found.append((i, cap))
    return found


def sync_probe_caps(caps, opener, n=5, skip=frozenset()):
    """Add newly-plugged cameras to a probe dict. Returns sorted indices.

    caps: {idx: (cap, lock, cache)} mutated in place; opener(idx) is
    try_open_camera in production, a fake in tests. Additive only:
    never closes anything, so a slow rescan can't steal the live feed.
    skip holds indices to ignore this round.
    """
    import threading

    for i in range(n):
        if i in caps or i in skip:
            continue
        cap = opener(i)
        if cap is not None:
            caps[i] = (cap, threading.Lock(), {"t": 0.0, "jpg": None})
    return sorted(caps)


def prune_dead_caps(caps, tries=3):
    """Drop cameras that stopped streaming. Returns sorted removed indices.

    Manual-rescan helper (setup screen): for each known index, read under
    its lock up to `tries` times; a single good frame keeps it. DSHOW
    devices stutter when siblings open, so one failure means nothing -
    only sustained unreadability drops the card (regression: the old
    auto-drop ate a working Logitech on 4 transient failures, Nov 3).
    Removed caps are released. Mutates caps in place.
    """
    removed = []
    for idx in sorted(caps):
        cap, lock, _cache = caps[idx]
        alive = False
        with lock:
            for _ in range(max(tries, 1)):
                try:
                    ok, frame = cap.read()
                except Exception:
                    ok, frame = False, None
                if ok and frame is not None:
                    alive = True
                    break
        if not alive:
            try:
                cap.release()
            except Exception:
                pass
            del caps[idx]
            removed.append(idx)
    return removed


def available_monitors():
    """[(idx, rect, thumbnail)]. Screenshots need set_dpi_aware() first."""
    from PIL import ImageGrab

    from tools.record_session import list_monitors

    out = []
    for i, (l, t, w, h) in enumerate(list_monitors()):
        try:
            shot = ImageGrab.grab(bbox=(l, t, l + w, t + h), all_screens=True)
        except Exception:
            continue
        shot.thumbnail((480, 240))
        out.append((i, (l, t, w, h), shot))
    return out


def _choice_window(title, subtitle, cards, live_ms=0):
    """cards: [{key, caption, sub, image() -> PIL}]. Returns key or None."""
    import tkinter as tk

    from PIL import ImageTk

    choice = {"key": None}
    root = tk.Tk()
    root.title(title)
    root.configure(bg=BG)
    tk.Label(root, text=title, font=("Arial", 20, "bold"),
             bg=BG, fg=INK, pady=14).pack()
    tk.Label(root, text=subtitle, font=("Arial", 13),
             bg=BG, fg=MUTED).pack(pady=(0, 12))
    row = tk.Frame(root, bg=BG, padx=18, pady=6)
    row.pack()
    widgets = []
    for c in cards:
        frame = tk.Frame(row, bg=CARD, highlightthickness=2,
                         highlightbackground="#3a3128", padx=10, pady=10)
        frame.pack(side="left", padx=10)
        photo = ImageTk.PhotoImage(c["image"]())
        img = tk.Label(frame, image=photo, bg=CARD, cursor="hand2")
        img.image = photo
        img.pack()
        tk.Label(frame, text=c["caption"], font=("Arial", 16, "bold"),
                 bg=CARD, fg=INK).pack(pady=(8, 0))
        tk.Label(frame, text=c["sub"], font=("Arial", 12),
                 bg=CARD, fg=MUTED).pack()
        for w in (frame, img):
            w.bind("<Button-1>",
                   lambda _e, k=c["key"]: (choice.update(key=k), root.destroy()))
            w.bind("<Enter>", lambda _e, f=frame: f.configure(highlightbackground=ACCENT))
            w.bind("<Leave>", lambda _e, f=frame: f.configure(highlightbackground="#3a3128"))
        widgets.append((c, img))

    def tick():
        if choice["key"] is not None or not root.winfo_exists():
            return
        try:
            for c, img in widgets:
                photo = ImageTk.PhotoImage(c["image"]())
                img.configure(image=photo)
                img.image = photo
            root.after(live_ms, tick)
        except tk.TclError:
            pass

    if live_ms:
        root.after(live_ms, tick)
    root.mainloop()
    return choice["key"]


def _cam_cards(found, thumb_w=320):
    import cv2
    from PIL import Image

    cards = []
    for idx, cap in found:
        def make_image(cap=cap):
            ok, frame = cap.read()
            h, w = frame.shape[:2] if ok and frame is not None else (240, 320)
            if not ok or frame is None:
                return Image.new("RGB", (thumb_w, 180), (20, 20, 20))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            im.thumbnail((thumb_w, 240))
            return im

        cards.append({"key": idx, "caption": f"CÁMARA {idx}",
                      "sub": "click para usar esta", "image": make_image})
    return cards


def resolve_camera(preferred, probe=available_cameras):
    """preferred int wins; None probes (silent if 1, GUI if several)."""
    if preferred is not None:
        return preferred
    found = probe()
    if not found:
        print("no_camera: no webcam opened on indices 0..4.")
        return None
    if len(found) == 1:
        idx, cap = found[0]
        cap.release()
        print(f"camera {idx}: only one found, using it.")
        return idx
    print(f"cameras {[i for i, _ in found]}: choose in the window...")
    idx = _choice_window("Elige tu cámara", "Muévete para distinguirlas. Click para elegir.",
                         _cam_cards(found), live_ms=150)
    for _, cap in found:
        cap.release()
    if idx is None:
        print("camera selection cancelled.")
        return None
    return idx


def resolve_monitor(preferred, probe=available_monitors):
    """preferred int wins; None probes (silent if 1, GUI if several)."""
    if preferred is not None:
        return preferred
    found = probe()
    if not found:
        print("no_monitor: no screens detected.")
        return None
    if len(found) == 1:
        print(f"monitor {found[0][0]}: only one found, using it.")
        return found[0][0]
    cards = [{"key": i, "caption": f"MONITOR {i}",
              "sub": f"{w}x{h}  ({'principal' if i == 0 else 'extendido'})",
              "image": (lambda shot: lambda: shot)(shot)}
             for i, (_l, _t, w, h), shot in found]
    print(f"monitors {[i for i, _, _ in found]}: choose in the window...")
    idx = _choice_window("Elige tu monitor", "Usarás este para la prueba. Click para elegir.",
                         cards)
    if idx is None:
        print("monitor selection cancelled.")
        return None
    return idx
