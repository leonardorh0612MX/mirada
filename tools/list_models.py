"""List available Meta Model API model IDs (find the image model).

Reads MODEL_API_KEY and META_MODEL_BASE_URL from .env. Never prints the key.
Usage: .\\.venv\\Scripts\\python.exe tools/list_models.py
"""

import os

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
    base = env.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1")
    if not key or "placeholder" in key.lower():
        print("missing_key: set a real MODEL_API_KEY in .env")
        return 1
    from openai import OpenAI

    client = OpenAI(base_url=base, api_key=key)
    try:
        models = client.models.list()
    except Exception as exc:  # noqa: BLE001 - probe must report, not crash
        print(f"list_failed: {type(exc).__name__}: {exc}")
        return 1
    for m in models.data:
        print(m.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
