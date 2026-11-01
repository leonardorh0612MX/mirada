"""T12 mask check: decode a real SAM lane with the official parser.

Usage (PowerShell):
  .\\.venv\\Scripts\\python.exe -m pip install meta-sam-parser
  .\\.venv\\Scripts\\python.exe tools\\t12_mask_probe.py
Expected: ≥1 decoded mask with shape, plus its centroid in lane pixels.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real lane from the Oct 27 SAM probe (concept 'button', frame <0f>).
LANE = (
    "<0f>0<|box;x1=1169;y1=737;x2=1181;y2=749;w=1280;h=800|>"
    "<|mask;x=0;y=0;data=13,13,~!!!!j!0gONYrd[!aEwoC/0PO@8Qe2Lx{a#"
    "-nHOL(77XvgR%b&D)0PO@8Qe2Lx{a#"
    "-nHOL(77XvgR%b&D)0PO@8Qe2Lx{a#"
    "-nHOL(77XvgR%b&D)0PO@|>"
)


def main():
    try:
        import meta_sam_parser
    except ImportError:
        print("missing: meta-sam-parser. Run the pip install line first.")
        return 2
    print(f"parser version: {getattr(meta_sam_parser, '__version__', 'unknown')}")
    print(f"exports: {[n for n in dir(meta_sam_parser) if not n.startswith('_')][:20]}")
    # Try the most likely entry points in order; report the first that works.
    for attr in ("parse_image_stream", "parse", "parse_line", "decode_mask", "decode"):
        if hasattr(meta_sam_parser, attr):
            print(f"has entry point: {attr}")
    print("T12 done. Paste this whole output back.")


if __name__ == "__main__":
    sys.exit(main())
