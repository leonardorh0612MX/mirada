"""Generate one image with muse-image-1.0 and save it locally.

Reads MODEL_API_KEY and META_MODEL_BASE_URL from .env. Handles either
b64_json or url payloads; prints the response shape for diagnosis.
Usage: .\\.venv\\Scripts\\python.exe tools/gen_image.py "prompt" site/hero.png
"""

import base64
import os
import sys
import urllib.request

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
    if len(sys.argv) < 3:
        print('usage: gen_image.py "prompt" out.png')
        return 1
    prompt, out = sys.argv[1], sys.argv[2]
    env = load_dotenv(os.path.join(REPO, ".env"))
    key = env.get("MODEL_API_KEY", "")
    base = env.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1")
    if not key or "placeholder" in key.lower():
        print("missing_key: set a real MODEL_API_KEY in .env")
        return 1
    from openai import OpenAI

    client = OpenAI(base_url=base, api_key=key)
    try:
        resp = client.images.generate(model="muse-image-1.0", prompt=prompt)
    except Exception as exc:  # noqa: BLE001 - probe must report, not crash
        print(f"gen_failed: {type(exc).__name__}: {exc}")
        return 1
    item = resp.data[0]
    print(f"response keys: {sorted(vars(item).keys())}")
    if getattr(item, "b64_json", None):
        raw = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        print(f"fetching url ({len(item.url)} chars)")
        with urllib.request.urlopen(item.url) as fh:
            raw = fh.read()
    else:
        print("no_image_payload: neither b64_json nor url present")
        return 1
    dest = out if os.path.isabs(out) else os.path.join(REPO, out)
    with open(dest, "wb") as fh:
        fh.write(raw)
    print(f"saved: {dest} kb={len(raw) // 1024}")
    usage = getattr(resp, "usage", None)
    if usage is not None:
        print(f"usage: {usage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
