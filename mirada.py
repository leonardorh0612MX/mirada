"""Mirada: the one entry point. Runs the gaze communication board.

Usage: .\\.venv\\Scripts\\python.exe mirada.py
Screens, camera and language are picked inside the window; no flags needed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.board_app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
