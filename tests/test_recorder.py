"""T7: record-replay round trip. Stdlib only."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recorder.session import append_event, new_session, read_events


class TestRecorder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_round_trip(self):
        sp = new_session(self.tmp, "s1", meta={"screen": [1920, 1080]})
        append_event(sp, "gaze", {"x": 1.0}, t_mono=1.0)
        append_event(sp, "anchor", {"x": 2.0}, t_mono=2.0)
        append_event(sp, "dot", {"x": 3.0}, t_mono=2.0)  # equal stamps allowed
        events = read_events(sp)
        self.assertEqual(len(events), 3)
        self.assertEqual([e["kind"] for e in events], ["gaze", "anchor", "dot"])
        self.assertEqual(events[0]["payload"], {"x": 1.0})

    def test_backwards_rejected(self):
        sp = new_session(self.tmp, "s2")
        append_event(sp, "gaze", {}, t_mono=5.0)
        append_event(sp, "gaze", {}, t_mono=4.0)
        with self.assertRaises(ValueError):
            read_events(sp)


if __name__ == "__main__":
    unittest.main()
