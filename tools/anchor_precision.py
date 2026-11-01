"""T22 anchor-precision probe: ground truth independent of gaze.

Shows N known targets on the working monitor. You fixate each and press
SPACE. The tool screenshots, asks Spark for the point, SAM for refinement,
and scores distance to the known position. No gaze involved.
Usage (needs network + .env):
  .\\.venv\\Scripts\\python.exe tools\\anchor_precision.py [--monitor 1] [--points 9]
"""

import argparse
import base64
import io
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors import spark
from anchors.sam_lane import box_centroid, parse_lane
from tools.record_session import grid_points, list_monitors, new_key_state, press_key, release_key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--points", type=int, default=9)
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(repo, ".env"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    from pynput import keyboard
    from PIL import ImageGrab
    import tkinter as tk

    monitors = list_monitors()
    monitor = monitors[args.monitor]
    left, top, mw, mh = monitor
    targets = grid_points(monitor)[:args.points]

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    size = 90
    canvas = tk.Canvas(root, width=size, height=size, bg="black", highlightthickness=0)
    canvas.pack()
    canvas.create_oval(8, 8, size - 8, size - 8, fill="white")
    root.withdraw()

    state = new_key_state()

    def on_press(key):
        press_key(state, key, keyboard)

    def on_release(key):
        release_key(state, key, keyboard)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/"),
        api_key=os.environ["MODEL_API_KEY"],
    )
    errs_c, errs_d = [], []
    try:
        for gx, gy in targets:
            root.geometry(f"{size}x{size}+{int(gx - size / 2)}+{int(gy - size / 2)}")
            root.deiconify()
            root.update()
            state["space"] = False
            print(f"fixate ({gx:.0f},{gy:.0f}), SPACE...", flush=True)
            while not state["space"] and not state["quit"]:
                root.update()
                time.sleep(0.05)
            if state["quit"]:
                break
            root.update()
            time.sleep(0.15)  # let the dot paint before capture
            shot = ImageGrab.grab(all_screens=True).crop((left, top, left + mw, top + mh))
            root.withdraw()
            thumb = shot.copy()
            thumb.thumbnail((1280, 1280))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            png = buf.getvalue()
            sx = shot.size[0] / thumb.size[0]
            prop = spark.propose(png, context="user fixating the white dot")
            if prop is None:
                print("spark: none")
                continue
            concept, conf, _, px, py = prop
            ax, ay = left + px * sx, top + py * sx
            ec = ((ax - gx) ** 2 + (ay - gy) ** 2) ** 0.5
            errs_c.append(ec)
            stream = client.responses.create(
                model="sam-3.1", stream=True,
                input=[{"role": "user", "content": [
                    {"type": "input_text", "text": concept},
                    {"type": "input_image",
                     "image_url": f"data:image/png;base64,{base64.b64encode(png).decode()}"},
                ]}],
            )
            lane = "".join(e.delta for e in stream
                            if getattr(e, "type", "") == "response.output_text.delta")
            try:
                recs = parse_lane(lane)
            except ValueError:
                recs = []
            if recs:
                cx, cy = box_centroid(recs[0]["box"])
                dx, dy = left + cx * sx, top + cy * sx
                ed = ((dx - gx) ** 2 + (dy - gy) ** 2) ** 0.5
                errs_d.append(ed)
                print(f"C err={ec:.0f}px D err={ed:.0f}px ({concept!r})")
            else:
                print(f"C err={ec:.0f}px D: no matches ({concept!r})")
    finally:
        root.destroy()
        listener.stop()
    if errs_c:
        print(f"C: n={len(errs_c)} median={statistics.median(errs_c):.0f}px "
              f"mean={statistics.mean(errs_c):.0f}px")
    if errs_d:
        print(f"D: n={len(errs_d)} median={statistics.median(errs_d):.0f}px")
    print("T22 done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\naborted by user.")
        sys.exit(130)
