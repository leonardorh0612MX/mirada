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


def overlay_rect(mw, mh):
    """Floating-buttons rect, monitor-relative: top-right, over the
    display-only bar so it never covers an interactive cell. Left half
    is MIRADA (back), right half TECLADO. Pure (tested)."""
    return (mw - 476, 16, 440, 210)


def in_rect(x, y, rect):
    """Point-in-rect, monitor-relative pixels. Pure (tested)."""
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


class GazeRing:
    """Transparent click-through gaze cursor (Tk overlay, Win32).

    The WebView2 ring window painted an opaque white square behind the
    ring on the builder's machine despite transparent=True, so the
    cursor is a Tk overlay instead: -transparentcolor punches the real
    window shape and WS_EX_TRANSPARENT lets clicks pass through to the
    app below. Draws the amber ring, the core dot and the dwell fill
    arc (frac 0..1: white arc grows as the click charges).
    Owned end-to-end by the watcher's thread; update() pumps Tk.
    """

    SIZE = 120

    def __init__(self):
        import tkinter as tk

        r = tk.Tk()
        self._root = r
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-transparentcolor", "magenta")
        r.geometry(f"{self.SIZE}x{self.SIZE}+-300+-300")
        r.withdraw()
        self._cv = tk.Canvas(r, width=self.SIZE, height=self.SIZE,
                             bg="magenta", highlightthickness=0, bd=0)
        self._cv.pack()
        try:
            import ctypes

            hwnd = r.winfo_id()
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20,
                                                ex | 0x20 | 0x80000)
        except Exception:
            pass
        self._shown = False

    def draw(self, x, y, frac):
        c, s = self._cv, self.SIZE
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
        self._root.geometry(f"{s}x{s}+{int(x - s / 2)}+{int(y - s / 2)}")
        if not self._shown:
            self._root.deiconify()
            self._shown = True
        self._root.update()

    def hide(self):
        if self._shown:
            try:
                self._root.withdraw()
            except Exception:
                pass
            self._shown = False
        try:
            self._root.update()
        except Exception:
            pass

    def close(self):
        try:
            self._root.destroy()
        except Exception:
            pass


def main():
    set_dpi_aware()
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
    back_win = webview.create_window(
        "Mirada volver", url + "back", width=440, height=210,
        frameless=True, on_top=True, hidden=True, resizable=False,
        transparent=True)
    fs = {"on": False}

    def _set_fs(on):
        if on != fs["on"]:
            try:
                window.toggle_fullscreen()
            except Exception:
                pass
            fs["on"] = on

    def _watch():
        placed = False
        last_launch = [None]
        mon = {"rect": None, "shown": False, "dwell": 0.0}

        def _back_show():
            if mon["rect"] is None or mon["shown"]:
                return
            left, top, mw, mh = mon["rect"]
            rx, ry, _rw, _rh = overlay_rect(mw, mh)
            try:
                back_win.move(left + rx, top + ry)
                back_win.show()
                mon["shown"] = True
            except Exception:
                pass

        ring = {"inst": None}

        def _ring():
            if ring["inst"] is None:
                try:
                    ring["inst"] = GazeRing()
                except Exception as e:
                    print(f"ring overlay unavailable: {e!r}")
                    ring["inst"] = False  # fail once, not 20x/second
                    return None
            return ring["inst"] or None

        def _back_hide():
            if mon["shown"]:
                try:
                    back_win.hide()
                except Exception:
                    pass
                mon["shown"] = False
            if ring["inst"]:
                ring["inst"].hide()
            mon["dwell"] = 0.0

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
            _back_hide()

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
                _back_show()
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
                _back_hide()
                mon["zone"] = None
            elif mon["rect"] is not None:
                # Gaze-dwell on the floating buttons: left = back to
                # phrases, right = open the keyboard. Real elapsed time,
                # with console prints (the first version failed silently
                # in web-20261101 runs; the builder used the mouse).
                gaze = st.get("gaze")
                _l, _t, mw, mh = mon["rect"]
                zone = None
                if gaze:
                    gx, gy = gaze[0] * mw, gaze[1] * mh
                    rx, ry, rw, rh = overlay_rect(mw, mh)
                    if in_rect(gx, gy, (rx, ry, rw, rh)):
                        zone = "back" if gx < rx + rw / 2 else "kb"
                    # Eye-cursor follows the gaze over the app; the white
                    # arc shows the dwell charge before the click lands.
                    ov = _ring()
                    if ov is not None:
                        try:
                            ov.draw(_l + gx, _t + gy,
                                    st.get("dwell_frac") or 0.0)
                        except Exception:
                            pass
                elif ring["inst"]:
                    ring["inst"].hide()
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
            if RETURN_EVENT.is_set() and mon["shown"]:
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
        _back_hide()
        if ring["inst"]:
            ring["inst"].close()

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
