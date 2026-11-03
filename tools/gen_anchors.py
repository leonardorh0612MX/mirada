"""Offline semantic anchors from recorded screenshots (strategies C/D).

Pipeline per screenshot: Spark proposes concept + point (Responses API).
C anchor: the Spark point, scaled to virtual screen pixels.
D anchor: SAM-refined centroid when the concept segments, else absent.
(V2 note, Oct 27: SAM matches natural objects, not UI text. On productivity
screens D is sparse by design; C carries the strategy.)
Output: anchors_offline.json: {"C": [...], "D": [...]} lists of
[t_mono, x, y, confidence, source].
Usage (needs network + .env):
  .\\.venv\\Scripts\\python.exe tools\\gen_anchors.py data\\sess-XXXX [--backend meta|baseten]
Baseten spends Baseten credits (Muse Spark Open) instead of Meta credits
for the C proposals; D stays empty (no SAM on Baseten).
"""

import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors import spark
from anchors.sam_lane import box_centroid, parse_lane


def load_dotenv(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def mean_brightness(png_path):
    from PIL import Image

    im = Image.open(png_path).convert("L")
    im.thumbnail((160, 160))
    px = list(im.get_flattened_data())
    return sum(px) / max(len(px), 1)


def sam_lane(concept, png_bytes):
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/"),
        api_key=os.environ["MODEL_API_KEY"],
        timeout=float(os.environ.get("MODEL_API_TIMEOUT_S", "90")),
    )
    b64 = base64.b64encode(png_bytes).decode()
    stream = client.responses.create(
        model="sam-3.1",
        stream=True,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": concept},
            {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
        ]}],
    )
    text = ""
    for event in stream:
        if getattr(event, "type", "") == "response.output_text.delta":
            text += event.delta
    return text


def main():
    argv = sys.argv[1:]
    backend, spath, skip_next = "meta", None, False
    for i, a in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if a.startswith("--backend="):
            backend = a.split("=", 1)[1].strip().lower()
        elif a == "--backend" and i + 1 < len(argv):
            backend = argv[i + 1].strip().lower()
            skip_next = True
        elif not a.startswith("--") and spath is None:
            spath = a
    if spath is None:
        print("usage: gen_anchors.py <session_dir> [--backend meta|baseten]")
        return 2
    if backend not in ("meta", "baseten"):
        print(f"unknown backend {backend!r}: use meta or baseten")
        return 2
    if backend == "baseten":
        os.environ["ANCHOR_BACKEND"] = "baseten"
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(repo, ".env"))
    print(f"backend: {spark.backend()}")

    shots, monitor_rect = [], (0, 0)
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e["kind"] == "monitor":
                r = e["payload"]["rect"]
                monitor_rect = (r[0], r[1])
            elif e["kind"] == "screenshot" and e["payload"].get("file"):
                shots.append(e)
    print(f"screenshots with files: {len(shots)}")
    if not shots:
        return 0

    out = {"C": [], "D": []}
    for e in shots:
        fpath = os.path.join(spath, "shots", e["payload"]["file"])
        if mean_brightness(fpath) < 5.0:
            print(f"t={e['t_mono']:.0f} skipped: black frame (no API call)")
            continue
        with open(fpath, "rb") as fh:
            png = fh.read()
        size = e["payload"]["size"]
        thumb = e["payload"]["thumb_size"]
        sx, sy = size[0] / thumb[0], size[1] / thumb[1]

        def to_virtual(px, py):
            return (px * sx + monitor_rect[0], py * sy + monitor_rect[1])

        t0 = time.perf_counter()
        prop = spark.propose(png, context="user studying: reading, writing, watching video")
        if prop is None:
            print(f"t={e['t_mono']:.0f} spark: none")
            continue
        concept, conf, _, px, py = prop
        ax, ay = to_virtual(px, py)
        out["C"].append([e["t_mono"], ax, ay, conf, "spark"])
        if spark.backend() == "baseten":
            print(f"t={e['t_mono']:.0f} {concept!r} conf={conf:.2f} "
                  f"C=({ax:.0f},{ay:.0f}) D: skipped (no SAM on baseten) "
                  f"secs={time.perf_counter() - t0:.1f}")
            continue
        try:
            lane = sam_lane(concept, png)
            records = parse_lane(lane)
        except Exception as exc:
            print(f"t={e['t_mono']:.0f} C=({ax:.0f},{ay:.0f}) sam error {exc}")
            continue
        if records:
            cx, cy = box_centroid(records[0]["box"])
            dx, dy = to_virtual(cx, cy)
            out["D"].append([e["t_mono"], dx, dy, conf, "sam"])
            tag = f"D=({dx:.0f},{dy:.0f})"
        else:
            tag = "D: no matches"
        print(f"t={e['t_mono']:.0f} {concept!r} conf={conf:.2f} "
              f"C=({ax:.0f},{ay:.0f}) {tag} secs={time.perf_counter() - t0:.1f}")

    path = os.path.join(spath, "anchors_offline.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"wrote {len(out['C'])} C + {len(out['D'])} D anchors to {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\naborted by user. Partial anchors were not saved.")
        sys.exit(130)
