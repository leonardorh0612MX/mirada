"""T11 fallback: missing key degrades to None, never raises."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSparkFallback(unittest.TestCase):
    def test_missing_key_returns_none(self):
        env = dict(os.environ)
        os.environ.pop("MODEL_API_KEY", None)
        try:
            from anchors import spark

            self.assertIsNone(spark.propose(b"not-a-png", context="t"))
        finally:
            os.environ.clear()
            os.environ.update(env)


if __name__ == "__main__":
    unittest.main()
