"""Single-instance lock: the board twins itself ~144 ms after startup
(Nov 4) and twins fight over the exclusive camera. The second copy must
exit 0 fast, before touching any device. The OS releases the byte lock
when a holder dies, so a crash can never wedge the next launch. Windows
only, like the rest of the app. Stdlib only.

NOTE: the tests never claim-then-close in a polling loop - the CRT
lock does not tolerate lock/close cycles from one process (the product
claims once and holds forever, so it never cycles). Children announce
their held lock through a ready file instead.
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest

from app.singleinstance import claim_lock


class TestSingleInstance(unittest.TestCase):
    def _holder(self, path, ready):
        """Spawn a child that holds the lock, then touches ready."""
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return subprocess.Popen(
            [sys.executable, "-c",
             "from app.singleinstance import claim_lock;"
             f" fh = claim_lock({path!r});"
             f" open({ready!r}, 'w').close();"
             " import time; time.sleep(20)"],
            cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _wait_ready(self, ready, timeout=15):
        deadline = time.time() + timeout
        while not os.path.exists(ready):
            if time.time() > deadline:
                self.fail("child never took the lock")
            time.sleep(0.2)

    def test_first_claim_holds(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "mirada-single.lock")
            fh = claim_lock(path)  # must not raise
            self.assertTrue(os.path.exists(path))
            fh.close()

    def test_second_claim_exits_zero(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "mirada-single.lock")
            ready = os.path.join(d, "ready")
            kid = self._holder(path, ready)
            try:
                self._wait_ready(ready)  # child provably holds it
                with self.assertRaises(SystemExit) as cm:
                    claim_lock(path)
                self.assertEqual(cm.exception.code, 0)
            finally:
                kid.terminate()
                kid.wait(timeout=10)

    def test_dead_holder_releases(self):
        # A crash must never wedge the next launch: the OS drops the
        # byte lock with the dead handle.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path = os.path.join(d, "mirada-single.lock")
            ready = os.path.join(d, "ready")
            kid = self._holder(path, ready)
            self._wait_ready(ready)
            kid.kill()
            kid.wait(timeout=10)
            deadline = time.time() + 10
            while True:
                try:
                    fh = claim_lock(path)
                except SystemExit:
                    if time.time() > deadline:
                        self.fail("lock survived its dead holder")
                    time.sleep(0.2)
                    continue
                fh.close()
                return


if __name__ == "__main__":
    unittest.main()
