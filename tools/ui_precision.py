"""UI-content anchor precision: fixate known labeled boxes, score Spark/SAM.

Tkinter grid of 9 labeled boxes on the working monitor. Fixate the
highlighted box, SPACE. The tool screenshots, asks Spark for the point,
SAM for refinement, and scores distance to the known box center.
Usage (needs network + .env):
  .\\.venv\\Scripts\\python.exe tools\\ui_precision.py [--monitor 1]
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
from tools.record_session import list_monitors, new_key_state, press_key, release_key

LABELS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Kappa"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
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
    from openai import OpenAI

    monitor = list_monitors()[args.monitor]
    left, top, mw, mh = monitor
    client = OpenAI(
        base_url=os.environ.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/"),
        api_key=os.environ["MODEL_API_KEY"],
        timeout=float(os.environ.get("MODEL_API_TIMEOUT_S", "90")),
    )

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.geometry(f"{mw}x{mh}+{left}+{top}")
    canvas = tk.Canvas(root, width=mw, height=mh, bg="#202020", highlightthickness=0)
    canvas.pack()

    boxes = []
    for j in range(3):
        for i in range(3):
            x1 = left + mw * (0.08 + 0.28 * i)
            y1 = top + mh * (0.12 + 0.26 * j)
            x2, y2 = x1 + mw * 0.2, y1 + mh * 0.16
            boxes.append((x1, y1, x2, y2))

    state = new_key_state()

    def on_press(key):
        press_key(state, key, keyboard)

    def on_release(key):
        release_key(state, key, keyboard)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    def draw(active):
        canvas.delete("all")
        for k, (x1, y1, x2, y2) in enumerate(boxes):
            fill = "#ffd54a" if k == active else "#3a3a3a"
            canvas.create_rectangle(x1 - left, y1 - top, x2 - left, y2 - top,
                                    fill=fill, outline="#888888", width=2)
            canvas.create_text((x1 + x2) / 2 - left, (y1 + y2) / 2 - top,
                               text=LABELS[k], font=("Arial", 28),
                               fill="#111111" if k == active else "#e0e0e0")
        instr = "Fixate the YELLOW box, SPACE. Shift+Q quits."
        canvas.create_text(mw // 2, 24, text=instr, font=("Arial", 16), fill="#ffffff")
        root.update()

    errs_c, errs_d, matched = [], [], 0
    try:
        for k, (x1, y1, x2, y2) in enumerate(boxes):
            gx, gy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            draw(k)
            state["space"] = False
            while not state["space"] and not state["quit"]:
                root.update()
                time.sleep(0.05)
            if state["quit"]:
                break
            root.update()
            time.sleep(0.15)
            shot = ImageGrab.grab(all_screens=True).crop((left, top, left + mw, top + mh))
            thumb = shot.copy()
            thumb.thumbnail((1280, 1280))
            buf = io.BytesIO()
            thumb.save(buf, format="PNG")
            png = buf.getvalue()
            sx = shot.size[0] / thumb.size[0]
            prop = spark.propose(
                png, context=f"user fixating the yellow highlighted box labeled {LABELS[k]}")
            if prop is None:
                print(f"{LABELS[k]}: spark none")
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
                matched += 1
                cx, cy = box_centroid(recs[0]["box"])
                dx, dy = left + cx * sx, top + cy * sx
                ed = ((dx - gx) ** 2 + (dy - gy) ** 2) ** 0.5
                errs_d.append(ed)
                print(f"{LABELS[k]}: C err={ec:.0f}px D err={ed:.0f}px ({concept!r})")
            else:
                print(f"{LABELS[k]}: C err={ec:.0f}px D: no matches ({concept!r})")
    finally:
        root.destroy()
        listener.stop()
    if errs_c:
        print(f"C: n={len(errs_c)} median={statistics.median(errs_c):.0f}px "
              f"mean={statistics.mean(errs_c):.0f}px")
    print(f"D: {matched}/{len(errs_c)} matched" +
          (f" median={statistics.median(errs_d):.0f}px" if errs_d else ""))
    print("UI precision done. Paste this whole output back.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\naborted by user.")
        sys.exit(130)
