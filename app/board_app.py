"""Mirada board as a native app window (D15).

Same engine and same verified web UI as app/board_web.py, hosted in a
native pywebview window (Edge WebView2 on Windows 11) instead of a
browser tab. Starts windowed (title bar, app icon, draggable); when the
user picks a monitor it moves the window onto that monitor and goes
fullscreen there, because calibration is only pixel-true when the page
covers exactly the chosen screen. F11 toggles fullscreen; when the
session ends it returns to a window the user can close normally.
app/board_web.py (browser) and app/board.py (Tk) stay as fallbacks.

Usage: .\\.venv\\Scripts\\python.exe app\\board_app.py
QUIT: gaze QUIT cell, Shift+Q, or the window close button.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import webview
except ImportError:
    print("pywebview missing. Install: "
          ".\\.venv\\Scripts\\python.exe -m pip install pywebview")
    raise SystemExit(2)

from app.board_web import (FS_EVENT, KB_EVENT, RETURN_EVENT, SETUP,  # noqa: E402
                           Handler, Server, engine, state_get)
from tools.record_session import list_monitors, set_dpi_aware  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON = os.path.join(REPO, "site", "mirada.ico")


def monitor_rect(monitors, idx):
    """Clamp a chosen monitor index to a real rect. Pure (tested)."""
    if not monitors:
        return (0, 0, 1280, 800)
    return monitors[max(0, min(idx, len(monitors) - 1))]


TILE_W, TILE_H, TILE_GAP, DOCK_MARGIN = 200, 124, 12, 16


def overlay_rect(mw, mh):
    """Floating-dock bounding box, monitor-relative: top-right, over the
    display-only bar so it never covers an interactive cell. Pure (tested)."""
    return (mw - DOCK_MARGIN - (TILE_W * 2 + TILE_GAP), DOCK_MARGIN,
            TILE_W * 2 + TILE_GAP, TILE_H)


def tile_rects(mw, mh):
    """(back, kb) tile rects inside overlay_rect. The left tile returns
    to the board, the right tile opens the keyboard. Each tile is its
    own window so the gap between them stays clickable. Pure (tested)."""
    rx, ry, _rw, _rh = overlay_rect(mw, mh)
    return [(rx, ry, TILE_W, TILE_H),
            (rx + TILE_W + TILE_GAP, ry, TILE_W, TILE_H)]


def in_rect(x, y, rect):
    """Point-in-rect, monitor-relative pixels. Pure (tested)."""
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def render_tile(main, sub, mark=""):
    """Glass dock tile as an RGBA image (TILE_W x TILE_H). Pure (tested).

    Rounded dark gradient, top gloss, letterspaced caps, transparent
    corners - rendered at 2x and downscaled for crisp text. Shown on a
    -transparentcolor window, so zero rectangle bleeds onto the app.
    """
    from PIL import Image, ImageDraw, ImageFont

    S = 2
    W, H = TILE_W * S, TILE_H * S
    rgb = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(rgb)
    top, bot = (64, 64, 68), (14, 14, 16)
    for y in range(H):
        f = y / max(H - 1, 1)
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * f)
                          for i in range(3)))
    d.rounded_rectangle([2, 2, W - 3, H - 3], radius=56,
                        outline=(255, 255, 255, 40), width=3)
    d.line([(44, 18), (W - 44, 18)], fill=(255, 255, 255, 36), width=7)

    def _font(name, size):
        try:
            return ImageFont.truetype(name, size * S), True
        except Exception:
            return ImageFont.load_default(), False

    f_main, ttf = _font("segoeuib.ttf", 21)
    f_sub, _ = _font("segoeui.ttf", 11)
    if mark and not ttf:
        mark = ""  # fallback font lacks the glyph; plain caps instead

    def _tracked(cy, text, font, tracking, fill):
        widths = [d.textlength(ch, font=font) for ch in text]
        x = (W - (sum(widths) + tracking * max(len(text) - 1, 0))) / 2
        for ch, wch in zip(text, widths):
            d.text((x, cy), ch, font=font, fill=fill)
            x += wch + tracking

    _tracked(H * 0.30, (mark + " " + main).strip(), f_main, 7 * S,
             (245, 245, 247))
    _tracked(H * 0.62, sub, f_sub, 9 * S, (176, 176, 181))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1],
                                           radius=60, fill=255)
    img = rgb.convert("RGBA")
    img.putalpha(mask)
    return img.resize((TILE_W, TILE_H), Image.LANCZOS)


class Overlay:
    """Ring cursor + floating dock as Tk transparent overlays (Win32).

    WebView2 windows painted opaque white rectangles behind both the
    ring and the dock despite transparent=True, so all floating chrome
    lives here: -transparentcolor punches the real window shapes. The
    ring is click-through; each dock tile is its own small window
    (clicks land on tiles, the gap stays interactive) with mouse
    bindings for the caregiver and gaze zones from tile_rects. Tiles
    fade to ghost alpha until the gaze comes near, so they sit over
    the app without covering it. Callbacks fire on mouse click.
    Owned end-to-end by the watcher's thread.
    """

    RING = 120
    GHOST, SOLID = 0.45, 1.0

    def __init__(self, on_back, on_kb):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        self._root = root
        self._ring = self._float(root, self.RING, self.RING,
                                 click_through=True)
        self._cv = tk.Canvas(self._ring, width=self.RING,
                             height=self.RING, bg="magenta",
                             highlightthickness=0, bd=0)
        self._cv.pack()
        self._ring_shown = False
        self._tiles, self._photos = [], []
        for cb in (on_back, on_kb):
            t = self._float(root, TILE_W, TILE_H, click_through=False)
            lab = tk.Label(t, bg="magenta", bd=0, highlightthickness=0)
            lab.pack()
            lab.bind("<Button-1>", lambda _e, f=cb: f())
            self._tiles.append((t, lab))
        self._dock_shown = False
        self._alpha = None

    @staticmethod
    def _float(root, w, h, click_through):
        import tkinter as tk

        t = tk.Toplevel(root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.attributes("-transparentcolor", "magenta")
        t.configure(bg="magenta")
        t.geometry(f"{w}x{h}+-400+-400")
        t.withdraw()
        t.update_idletasks()
        if click_through:
            try:
                import ctypes

                hwnd = t.winfo_id()
                ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20,
                                                    ex | 0x20 | 0x80000)
            except Exception:
                pass
        return t

    def ring_draw(self, x, y, frac):
        c, s = self._cv, self.RING
        cx = cy = s / 2
        rr = 42
        c.delete("all")
        c.create_oval(cx - rr - 5, cy - rr - 5, cx + rr + 5, cy + rr + 5,
                      outline="#1c1c1e", width=9)
        c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                      outline="#ffd60a", width=4)
        if frac > 0.01:
            c.create_arc(cx - rr, cy - rr, cx + rr, cy + rr, start=90,
                         extent=-360.0 * min(1.0, frac), outline="#ffffff",
                         width=7, style="arc")
        c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6,
                      fill="#ffffff", outline="#ffd60a", width=2)
        self._ring.geometry(f"{s}x{s}+{int(x - s / 2)}+{int(y - s / 2)}")
        if not self._ring_shown:
            self._ring.deiconify()
            self._ring_shown = True
        self._ring.update()

    def ring_hide(self):
        if self._ring_shown:
            try:
                self._ring.withdraw()
            except Exception:
                pass
            self._ring_shown = False

    def dock_show(self, rects_abs, tiles):
        """rects_abs: [(x, y, w, h)]; tiles: [(main, sub, mark)]."""
        import tkinter as tk

        self._photos = []
        for (t, lab), (rx, ry, _rw, _rh), (main, sub, mark) in zip(
                self._tiles, rects_abs, tiles):
            photo = tk.PhotoImage(master=self._root,
                                  data=self._png(render_tile(main, sub,
                                                             mark)))
            self._photos.append(photo)  # else Tk garbage-collects it
            lab.configure(image=photo)
            t.geometry(f"{TILE_W}x{TILE_H}+{int(rx)}+{int(ry)}")
            t.deiconify()
        self._dock_shown = True
        self.dock_alpha(self.GHOST)

    @staticmethod
    def _png(img):
        import base64
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue())

    def dock_alpha(self, a):
        if a != self._alpha:
            for t, _lab in self._tiles:
                try:
                    t.attributes("-alpha", a)
                except Exception:
                    pass
            self._alpha = a
        self._root.update()

    def dock_hide(self):
        if self._dock_shown:
            for t, _lab in self._tiles:
                try:
                    t.withdraw()
                except Exception:
                    pass
            self._dock_shown = False

    @property
    def dock_shown(self):
        return self._dock_shown

    def close(self):
        try:
            self._root.destroy()
        except Exception:
            pass


def main():
    set_dpi_aware()
    print("Mirada - look + hold to speak. No headset, no eye tracker,")
    print("just a webcam. Fully offline: nothing leaves this machine.")
    print("  1) Pick screen, camera and language in the window.")
    print("  2) Get comfortable, follow the dots with head AND eyes.")
    print("  3) Look at a cell, close your eyes ~0.4 s: it speaks.")
    print("Caregiver mouse always works. Shift+Q quits anywhere.")
    server = Server(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    print(f"mirada app window: {url}")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    done = threading.Event()

    def _run():
        try:
            engine(done.set)
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()
    win_kw = {"width": 1400, "height": 900, "min_size": (900, 600)}
    window = webview.create_window("Mirada", url, **win_kw)
    fs = {"on": False}

    def _set_fs(on):
        if on != fs["on"]:
            try:
                window.toggle_fullscreen()
            except Exception:
                pass
            fs["on"] = on

    def _watch():
        from app.i18n import s as _s

        placed = False
        last_launch = [None]
        mon = {"rect": None, "zone": None, "since": 0.0}
        ov = {"inst": None}

        def _overlay():
            if ov["inst"] is None:
                try:
                    ov["inst"] = Overlay(
                        on_back=RETURN_EVENT.set, on_kb=KB_EVENT.set)
                except Exception as e:
                    print(f"overlay unavailable: {e!r}")
                    ov["inst"] = False  # fail once, not 20x/second
                    return None
            return ov["inst"] or None

        def _dock_show(lang):
            if mon["rect"] is None:
                return
            o = _overlay()
            if o is None or o.dock_shown:
                return
            left, top, mw, mh = mon["rect"]
            rects = [(left + rx, top + ry, rw, rh)
                     for rx, ry, rw, rh in tile_rects(mw, mh)]
            o.dock_show(rects, [("MIRADA", _s(lang, "back_sub"), "\u2190"),
                                (_s(lang, "kb_main"), _s(lang, "kb_sub"),
                                 "")])

        def _dock_hide():
            if ov["inst"]:
                ov["inst"].dock_hide()
                ov["inst"].ring_hide()

        def _restore():
            RETURN_EVENT.set()
            for name in ("restore", "show"):
                try:
                    getattr(window, name)()
                    print(f"window {name} ok")
                    break
                except Exception as e:
                    print(f"window {name} failed: {e!r}")
            _set_fs(True)
            _dock_hide()

        while not done.is_set():
            st = state_get()
            launched = st.get("launched")
            if launched and launched != last_launch[0]:
                last_launch[0] = launched
                _set_fs(False)
                try:
                    window.minimize()  # get out of the launched app's way
                except Exception:
                    pass
                _dock_show(st.get("lang", "en"))
            if not launched:
                if last_launch[0] is not None:
                    # Engine accepted the return: unminimize fullscreen.
                    last_launch[0] = None
                    for name in ("restore", "show"):
                        try:
                            getattr(window, name)()
                            break
                        except Exception as e:
                            print(f"window {name} failed: {e!r}")
                    _set_fs(True)
                _dock_hide()
                mon["zone"] = None
            elif mon["rect"] is not None:
                # Gaze-dwell on the floating tiles: left = back to
                # phrases, right = open the keyboard. Real elapsed time,
                # with console prints (the first version failed silently
                # in web-20261101 runs; the builder used the mouse).
                # Tiles rest at ghost alpha and solidify as gaze nears.
                gaze = st.get("gaze")
                _l, _t, mw, mh = mon["rect"]
                zone = None
                o = _overlay()
                if gaze:
                    gx, gy = gaze[0] * mw, gaze[1] * mh
                    (brect, krect) = tile_rects(mw, mh)
                    if in_rect(gx, gy, brect):
                        zone = "back"
                    elif in_rect(gx, gy, krect):
                        zone = "kb"
                    if o is not None:
                        try:
                            o.ring_draw(_l + gx, _t + gy,
                                        st.get("dwell_frac") or 0.0)
                            rx, ry, rw, rh = overlay_rect(mw, mh)
                            near = (gx > rx - 260 and gy < ry + rh + 260)
                            o.dock_alpha(o.SOLID if near else o.GHOST)
                        except Exception:
                            pass
                elif o is not None:
                    try:
                        o.ring_hide()
                        o.dock_alpha(o.GHOST)
                    except Exception:
                        pass
                now_m = time.monotonic()
                if zone is None:
                    mon["zone"] = None
                elif mon["zone"] != zone:
                    mon["zone"] = zone
                    mon["since"] = now_m
                    print(f"dwell {zone} started gaze={gaze}")
                elif now_m - mon["since"] >= 0.8:
                    print(f"dwell {zone} fired")
                    if zone == "kb":
                        KB_EVENT.set()
                    _restore()
                    mon["zone"] = None
            if RETURN_EVENT.is_set() and ov["inst"] and ov["inst"].dock_shown:
                _restore()
            if not placed and SETUP["choice"] is not None:
                _cam, mon_idx, _lang = SETUP["choice"]
                left, top, mw, mh = monitor_rect(list_monitors(), mon_idx)
                mon["rect"] = (left, top, mw, mh)
                try:
                    window.move(left, top)
                    window.resize(mw, mh)
                except Exception:
                    pass
                _set_fs(True)  # calibration needs the exact screen
                placed = True
            if FS_EVENT.is_set():
                FS_EVENT.clear()
                _set_fs(not fs["on"])
            time.sleep(0.05)  # 20 Hz: the ring must track, not hop
        _set_fs(False)  # back to a closable window on the done screen
        _dock_hide()
        if ov["inst"]:
            ov["inst"].close()

    threading.Thread(target=_watch, daemon=True).start()
    try:
        if os.path.exists(ICON):
            webview.start(icon=ICON)
        else:
            webview.start()
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
