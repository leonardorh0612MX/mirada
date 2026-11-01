"""T2 smoke test: timed Spark + SAM calls on one real screenshot.

Reads MODEL_API_KEY and META_MODEL_BASE_URL from .env. Never prints the key.
Usage: .\\.venv\\Scripts\\python.exe tools/t2_smoke.py
"""

import base64
import io
import os
import statistics
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_dotenv(path):
    values = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip()
    return values


def timed(label, fn, n=10):
    lat = []
    last = None
    for i in range(n):
        t0 = time.perf_counter()
        try:
            last = fn()
            ok = True
        except Exception as exc:  # noqa: BLE001 - probe must report, not crash
            last = f"{type(exc).__name__}: {exc}"
            ok = False
        dt = time.perf_counter() - t0
        lat.append(dt)
        print(f"{label} try={i + 1} ok={ok} secs={dt:.2f}", flush=True)
        if not ok:
            break
    lat_sorted = sorted(lat)
    print(
        f"{label} n={len(lat)} median={statistics.median(lat_sorted):.2f}s "
        f"p95={lat_sorted[max(0, int(len(lat_sorted) * 0.95) - 1)]:.2f}s "
        f"min={lat_sorted[0]:.2f}s max={lat_sorted[-1]:.2f}s",
        flush=True,
    )
    return last


def main():
    env = load_dotenv(os.path.join(REPO, ".env"))
    key = env.get("MODEL_API_KEY", "")
    base = env.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    if not key or key == "tu-key-aqui":
        print("missing_key: set a real MODEL_API_KEY in .env")
        return 2
    print(f"base_url={base} key_len={len(key)}")

    from openai import OpenAI

    client = OpenAI(base_url=base, api_key=key)

    print("--- A: spark text-only ---")

    def spark_text():
        r = client.chat.completions.create(
            model="muse-spark-1.3",
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=10,
        )
        return r.choices[0].message.content

    out = timed("spark_text", spark_text)
    print(f"spark_text sample: {str(out)[:120]}")

    print("--- B: screenshot ---")
    from PIL import ImageGrab

    shot = ImageGrab.grab()
    shot.thumbnail((1280, 1280))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"screenshot size={shot.size} kb={len(buf.getvalue()) // 1024}")
    os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
    with open(os.path.join(REPO, "data", "t2-screenshot.png"), "wb") as fh:
        fh.write(buf.getvalue())

    print("--- C: spark screenshot + text ---")

    def spark_vision():
        r = client.chat.completions.create(
            model="muse-spark-1.3",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Describe in one short phrase the most prominent UI element in this screenshot.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=60,
        )
        return r.choices[0].message.content

    out = timed("spark_vision", spark_vision)
    print(f"spark_vision sample: {str(out)[:200]}")

    print("--- D: sam-3.1 screenshot + text prompt ---")

    def sam_call():
        r = client.chat.completions.create(
            model="sam-3.1",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Segment the most prominent UI element. Return its bounding box.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=200,
        )
        return r.choices[0].message.content

    out = timed("sam_call", sam_call)
    print(f"sam_call sample: {str(out)[:400]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
