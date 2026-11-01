"""T2 structure probe: ONE call per model, dump full response shape.

Goal: learn where Spark text and SAM masks actually live in the payload.
Reads .env, never prints the key.
Usage: .\\.venv\\Scripts\\python.exe tools\\t2_dump_shapes.py
"""

import base64
import io
import json
import os
import sys

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
    shot.thumbnail((640, 640))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(f"screenshot size={shot.size} kb={len(buf.getvalue()) // 1024}", flush=True)

    print("=== 1: spark chat completions, larger budget, raw dump ===")
    try:
        r = client.chat.completions.create(
            model="muse-spark-1.3",
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=100,
        )
        print(json.dumps(r.model_dump(), indent=1)[:3000])
    except Exception as exc:  # noqa: BLE001
        print(f"error: {type(exc).__name__}: {str(exc)[:500]}")

    print("=== 2: spark responses API, raw dump ===")
    try:
        r = client.responses.create(
            model="muse-spark-1.3",
            input=[{"role": "user", "content": [{"type": "input_text", "text": "Reply with exactly: ok"}]}],
        )
        print(json.dumps(r.model_dump(), indent=1)[:3000])
    except Exception as exc:  # noqa: BLE001
        print(f"error: {type(exc).__name__}: {str(exc)[:500]}")

    print("=== 3: sam responses API, raw dump ===")
    try:
        r = client.responses.create(
            model="sam-3.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Segment the largest window. Return its bounding box."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
                    ],
                }
            ],
        )
        print(json.dumps(r.model_dump(), indent=1)[:4000])
    except Exception as exc:  # noqa: BLE001
        print(f"error: {type(exc).__name__}: {str(exc)[:500]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
