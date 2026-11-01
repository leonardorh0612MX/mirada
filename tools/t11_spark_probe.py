"""T11 live check: one Spark proposal on the current screen. User runs this.

Usage (PowerShell, .env must hold a real key):
  .\\.venv\\Scripts\\python.exe tools\\t11_spark_probe.py
Expected: a (concept, confidence, reason) triple, or None with no traceback.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_dotenv(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    from PIL import ImageGrab
    from anchors import spark

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(repo, ".env"))
    shot = ImageGrab.grab()
    shot.thumbnail((1280, 1280))
    buf = io.BytesIO()
    shot.save(buf, format="PNG")
    print(f"screenshot size={shot.size} kb={len(buf.getvalue()) // 1024}", flush=True)
    out = spark.propose(buf.getvalue(), context="user just pressed a key in a text field")
    print(f"proposal: {out}")
    print("T11 done. Paste this output back.")


if __name__ == "__main__":
    main()
