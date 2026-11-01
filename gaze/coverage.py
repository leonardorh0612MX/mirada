"""Coverage gate: trust gaze only inside the enrollment hull. Stdlib only.

Online-EYE (Hou et al. 2025) showed implicit calibration matches explicit
calibration inside the convex hull of the anchor region and loses outside
it. The gate is the convex hull of the enrollment target points, shrunk by
an optional margin: predictions outside are flagged low-confidence.
"""

import math


def convex_hull(points):
    """Monotone chain. Returns hull vertices counter-clockwise, no dupes."""
    pts = sorted(set(points))
    if len(pts) <= 1:
        return list(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _point_in_convex(pt, hull):
    if len(hull) < 3:
        return True
    x, y = pt
    sign = 0
    for i in range(len(hull)):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % len(hull)]
        c = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        if c != 0:
            s = 1 if c > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
    return True


def inside_hull(pt, hull, margin=0.0):
    """Point inside hull shrunk toward its centroid by margin px."""
    if margin <= 0 or len(hull) < 3:
        return _point_in_convex(pt, hull)
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    shrunk = []
    for x, y in hull:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        k = max(0.0, (d - margin) / d)
        shrunk.append((cx + dx * k, cy + dy * k))
    return _point_in_convex(pt, shrunk)
