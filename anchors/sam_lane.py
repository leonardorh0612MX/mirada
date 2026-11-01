"""Parse SAM 3.1 response lanes into geometry. Stdlib only.

Grammar per https://dev.meta.ai/docs/sam/reading-segmentation, single image
frame: <0f>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..[;c=..]|><|mask;...|>,...
This module extracts boxes (anchor-grade geometry). Full mask decode belongs
to the official meta_sam_parser package; see T12.
"""

import re

BOX_RE = re.compile(
    r"<\|box;x1=(?P<x1>\d+);y1=(?P<y1>\d+);x2=(?P<x2>\d+);y2=(?P<y2>\d+);"
    r"w=(?P<w>\d+);h=(?P<h>\d+)(?:;c=(?P<c>[\d.]+))?\|>"
)
RECORD_RE = re.compile(r"(?P<oid>\d+)(?P<box><\|box;[^|]*\|>)")


def parse_lane(lane):
    """Lane text to list of records: {object_id, box, confidence}.

    box is (x1, y1, x2, y2) in lane pixels. confidence is None unless the
    request used include_confidence. Raises ValueError on malformed lanes.
    """
    lane = lane.strip()
    if not lane:
        return []  # zero matches is a normal result, not an error
    if not lane.startswith("<0f>"):
        raise ValueError(f"lane must start with <0f>, got: {lane[:20]!r}")
    body = lane[len("<0f>"):]
    records = []
    for m in RECORD_RE.finditer(body):
        b = BOX_RE.match(m.group("box"))
        if not b:
            raise ValueError(f"unparseable box token: {m.group('box')[:60]!r}")
        records.append({
            "object_id": int(m.group("oid")),
            "box": (int(b.group("x1")), int(b.group("y1")),
                    int(b.group("x2")), int(b.group("y2"))),
            "frame_size": (int(b.group("w")), int(b.group("h"))),
            "confidence": float(b.group("c")) if b.group("c") else None,
        })
    if not records and body.strip():
        raise ValueError(f"no records parsed from lane: {body[:80]!r}")
    return records


def box_centroid(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def to_screen_pixels(point, lane_size, screen_size, screen_offset=(0, 0)):
    """Map a lane-space point back to full-resolution virtual screen pixels.

    D9: every downscale factor travels with the frame. lane_size is the pixel
    size SAM saw; screen_size the source monitor size.
    """
    sx = screen_size[0] / lane_size[0]
    sy = screen_size[1] / lane_size[1]
    return (point[0] * sx + screen_offset[0], point[1] * sy + screen_offset[1])
