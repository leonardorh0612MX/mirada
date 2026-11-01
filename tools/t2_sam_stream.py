"""T2 streaming probe: SAM 3.1 with the official contract.

Per https://dev.meta.ai/docs/sam/segmenting: concept prompt is a SHORT NOUN
PHRASE (commands/questions return nothing), stream=true, geometry arrives as
special-token text in the output_text lane, one line per frame:
  <Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;...|>,...
Reads .env, never prints the key.
Usage: .\\.venv\\Scripts\\python.exe tools\\t2_sam_stream.py
"""

import base64
import io
import os
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
    W, H = shot.size
    print(f"screenshot size={shot.size} kb={len(buf.getvalue()) // 1024}", flush=True)

    for concept in ["window", "button"]:
        print(f"=== concept: {concept!r} ===", flush=True)
        t0 = time.perf_counter()
        try:
            stream = client.responses.create(
                model="sam-3.1",
                stream=True,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": concept},
                            {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
                        ],
                    }
                ],
            )
            text = ""
            events = 0
            for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    text += event.delta
                    events += 1
            dt = time.perf_counter() - t0
            print(f"secs={dt:.2f} delta_events={events}", flush=True)
            print(f"lane: {text[:800]}")
        except Exception as exc:  # noqa: BLE001
            print(f"error: {type(exc).__name__}: {str(exc)[:500]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
