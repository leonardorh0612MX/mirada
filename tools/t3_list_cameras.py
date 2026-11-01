"""Identify which physical camera is which index.

Grabs one frame from indices 0-3 and saves data/cam_<i>.png so you can SEE
which is the Logitech and which is the laptop. Prints resolution per index.
Usage: .\\.venv\\Scripts\\python.exe tools\\t3_list_cameras.py
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    import cv2

    os.makedirs(os.path.join(REPO, "data"), exist_ok=True)
    for i in range(4):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print(f"index {i}: not available")
            continue
        ok = False
        frame = None
        for _ in range(10):
            ok, frame = cap.read()
            if ok and frame is not None:
                break
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if ok and frame is not None:
            path = os.path.join(REPO, "data", f"cam_{i}.png")
            cv2.imwrite(path, frame)
            print(f"index {i}: {w}x{h} saved to data/cam_{i}.png")
        else:
            print(f"index {i}: opened but no frames")
    print("Open data/cam_*.png to see which is which.")


if __name__ == "__main__":
    sys.exit(main() or 0)
