"""T2 last probe: does hosted sam-3.1 emit ANY text, and where do boxes live?

Two single calls. Reads .env, never prints the key.
Usage: .\\.venv\\Scripts\\python.exe tools\\t2_sam_textprobe.py
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

    print("=== A: sam-3.1 descriptive prompt (does it emit text at all?) ===")
    try:
        r = client.responses.create(
            model="sam-3.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "What is the most prominent UI element in this image? Answer in five words."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
                    ],
                }
            ],
        )
        print("output_text:", repr(r.output_text))
        print("n_items:", len(r.output))
        for item in r.output:
            print(json.dumps(item.model_dump(), indent=1)[:1500])
    except Exception as exc:  # noqa: BLE001
        print(f"error: {type(exc).__name__}: {str(exc)[:500]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
