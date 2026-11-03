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

    def test_baseten_backend_selected_by_env(self):
        env = dict(os.environ)
        os.environ["ANCHOR_BACKEND"] = "baseten"
        os.environ.pop("BASETEN_API_KEY", None)
        try:
            from anchors import spark

            self.assertEqual(spark.backend(), "baseten")
            # Missing Baseten key degrades to None, never raises,
            # and never touches the network.
            self.assertIsNone(spark.propose(b"not-a-png", context="t"))
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_meta_is_default_backend(self):
        env = dict(os.environ)
        os.environ.pop("ANCHOR_BACKEND", None)
        try:
            from anchors import spark

            self.assertEqual(spark.backend(), "meta")
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_baseten_rescales_normalized_coords(self):
        # Spark Open answers in 0-1000 space: (500, 250) on a 200x100
        # image must come back as pixels (100, 25). Mocked client,
        # no network.
        import io
        from unittest import mock

        from PIL import Image

        from anchors import spark

        buf = io.BytesIO()
        Image.new("RGB", (200, 100)).save(buf, format="PNG")
        msg = mock.Mock(content='{"concept": "x", "confidence": 0.9, '
                                '"reason": "r", "x": 500, "y": 250}')
        choice = mock.Mock(message=msg)
        resp = mock.Mock(choices=[choice])
        client = mock.Mock()
        client.chat.completions.create.return_value = resp
        with mock.patch.object(spark, "_baseten_client",
                               return_value=client):
            prop = spark._propose_baseten(buf.getvalue(), "", None, 2000)
        self.assertEqual(prop[:3], ("x", 0.9, "r"))
        self.assertAlmostEqual(prop[3], 100.0)
        self.assertAlmostEqual(prop[4], 25.0)


if __name__ == "__main__":
    unittest.main()
