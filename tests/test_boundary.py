"""Unit boundary: the reusable core must never import the application."""

import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIRS = ["gaze", "corrector", "anchors", "recorder", "eval"]


def offending_files():
    bad = []
    for d in CORE_DIRS:
        for name in os.listdir(os.path.join(REPO, d)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(REPO, d, name)
            with open(path, encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    s = line.strip()
                    if s.startswith(("import app", "from app")):
                        bad.append(f"{d}/{name}:{line_no}: {s}")
    return bad


class TestBoundary(unittest.TestCase):
    def test_core_does_not_import_app(self):
        self.assertEqual(offending_files(), [])


if __name__ == "__main__":
    unittest.main()
