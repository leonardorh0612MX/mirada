"""One board at a time: the webcam is exclusive access, and a second
copy fights the first frame-by-frame (flicker, loading icon, dead
camera). The claim is an OS byte-range lock, so a crash can never
wedge the next launch - the lock dies with the holder handle. Windows
only. Stdlib only.
"""
import msvcrt
import os

LOCK_NAME = "mirada-single.lock"


def claim_lock(path):
    """Hold the single-instance lock for this process lifetime.

    Returns the open handle (the caller must keep it alive). The
    second copy prints a message and raises SystemExit(0) - call
    this before any heavy import so the twin exits before touching
    a device. Pure side effect on the OS lock table (tested).
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fh = open(path, "w+b")
    try:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        fh.close()
        print("mirada is already running - this copy exits "
              "(the webcam is exclusive).")
        raise SystemExit(0)
    fh.write(b"m")
    fh.flush()
    return fh
