"""Mirada: the one entry point. Runs the gaze communication board.

Usage: .\\.venv\\Scripts\\python.exe mirada.py
Screens, camera and language are picked inside the window; no flags needed.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.singleinstance import LOCK_NAME, claim_lock  # noqa: E402

_LOCK = claim_lock(os.path.join(tempfile.gettempdir(), LOCK_NAME))

from app.board_app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
