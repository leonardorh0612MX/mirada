"""Verify the Baseten backend: key, model, then one vision call.

Usage: .\\.venv\\Scripts\\python.exe tools\\baseten_probe.py
Needs BASETEN_API_KEY in .env. Never prints the key. Burns two tiny calls.
"""
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors import spark  # noqa: E402


def load_dotenv(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(repo, ".env"))
    os.environ["ANCHOR_BACKEND"] = "baseten"
    key = os.environ.get("BASETEN_API_KEY", "")
    print(f"backend: {spark.backend()} key_len={len(key)}")
    if not key:
        print("missing_key: set BASETEN_API_KEY in .env")
        return 2
    # 1) Text-only call: key + model id valid?
    try:
        client = spark._baseten_client()
        t0 = time.perf_counter()
        r = client.chat.completions.create(
            model=os.environ.get("BASETEN_MODEL", spark.BASETEN_DEFAULT_MODEL),
            # Reasoning models burn max_tokens on thought: a tiny budget
            # returns empty content instead of truncated content.
            max_tokens=500,
            messages=[{"role": "user", "content": "Reply with the word ok."}],
        )
        msg = r.choices[0].message
        content = msg.content
        thought = getattr(msg, "reasoning_content", None)
        if content is None:
            print(f"text NO-CONTENT secs={time.perf_counter() - t0:.1f}")
            print(f"finish: {r.choices[0].finish_reason} "
                  f"usage: {r.usage}")
            print(f"reasoning_content: {(thought or '')[:300]!r}")
        else:
            print(f"text ok secs={time.perf_counter() - t0:.1f} "
                  f"reply={content.strip()!r}")
    except Exception as e:
        print(f"text FAILED: {type(e).__name__}: {e}")
        return 1
    # 2) One vision proposal on a live screenshot.
    from PIL import ImageGrab

    im = ImageGrab.grab()
    im.thumbnail((640, 640))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    t0 = time.perf_counter()
    prop = spark.propose(buf.getvalue(), context="user looking at the screen")
    print(f"vision secs={time.perf_counter() - t0:.1f} proposal={prop}")
    if prop is None:
        print("vision FAILED: None (key ok, but the model refused the image "
              "path or the JSON contract - paste this output back)")
        return 1
    print("baseten probe done. gen_anchors.py --backend baseten is safe to run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
