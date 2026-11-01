"""T2 follow-up: probe sam-3.1 through the Responses API.

The Chat Completions endpoint 404s for sam-3.1 with "Use /v1/responses".
This script tries the Responses shape and reports the exact result.
Usage: .\\.venv\\Scripts\\python.exe tools\\t2_sam_responses.py
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


def main():
    env = load_dotenv(os.path.join(REPO, ".env"))
    key = env.get("MODEL_API_KEY", "")
    base = env.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    if not key:
        print("missing_key")
        return 2

    from openai import OpenAI

    client = OpenAI(base_url=base, api_key=key)

    from PIL import ImageGrab

    shot = ImageGrab.grab()
    shot.thumbnail((1280, 1280))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"screenshot size={shot.size} kb={len(buf.getvalue()) // 1024}", flush=True)

    lat = []
    for i in range(5):
        t0 = time.perf_counter()
        try:
            r = client.responses.create(
                model="sam-3.1",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Segment the most prominent UI element. Return its bounding box.",
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{b64}",
                            },
                        ],
                    }
                ],
            )
            out = r.output_text if hasattr(r, "output_text") else str(r)[:400]
            usage = getattr(r, "usage", None)
            print(f"sam_resp try={i + 1} ok=True secs={time.perf_counter() - t0:.2f}", flush=True)
            print(f"output: {str(out)[:500]}")
            print(f"usage: {usage}")
            lat.append(time.perf_counter() - t0)
        except Exception as exc:  # noqa: BLE001 - probe must report, not crash
            print(f"sam_resp try={i + 1} ok=False secs={time.perf_counter() - t0:.2f}", flush=True)
            print(f"error: {type(exc).__name__}: {str(exc)[:600]}")
            break
    if lat:
        s = sorted(lat)
        print(f"sam_resp n={len(s)} median={statistics.median(s):.2f}s max={s[-1]:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
