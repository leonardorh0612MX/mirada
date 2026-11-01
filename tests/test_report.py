"""T14 report on synthetic data. Stdlib only, no matplotlib needed."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.replay import error_over_time as eot_a, replay_a
from eval.report import write_report
from eval.strategies import error_over_time, run_strategy
from eval.synthetic import make_anchors, make_session


class TestReport(unittest.TestCase):
    def test_report_files(self):
        matrix, events, dots = make_session(duration_s=600.0, drift_px_s=0.05)
        series = {
            "A": eot_a(replay_a(events, matrix), dots),
            "C": error_over_time(run_strategy(events, dots, matrix, make_anchors())[0], dots),
        }
        tmp = tempfile.mkdtemp()
        try:
            out = write_report(series, tmp)
            self.assertTrue(os.path.exists(out["figure"]))
            self.assertTrue(os.path.exists(out["table"]))
            with open(out["table"], encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn("| A |", body)
            self.assertIn("| C |", body)
            with open(out["figure"], encoding="utf-8") as fh:
                svg = fh.read()
            self.assertIn("<svg", svg)
            self.assertIn("polyline", svg)
            self.assertLess(out["summary"]["C"]["mean_px"], out["summary"]["A"]["mean_px"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
