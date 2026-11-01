"""Big QWERTY keyboard geometry. Pure layout math, GUI-free.

Rows produce (key, x1, y1, x2, y2) in canvas pixels for a (w, h) surface.
Keys are deliberately large: at ~1920 px wide, a letter key is ~150 px.
"""

ROWS = [
    "QWERTYUIOP",
    "ASDFGHJKL",
    "ZXCVBNM",
]
SPECIALS = [("SPACE", 5.0), ("DELETE", 2.0)]


def layout(w, h, margin=24, gap=12):
    """All keys as dicts with label and rect. Covers the full surface."""
    usable_w = w - 2 * margin
    usable_h = h - 2 * margin
    row_h = usable_h / (len(ROWS) + 1)
    keys = []
    y = float(margin)
    for row in ROWS:
        n = len(row)
        unit = (usable_w - gap * (n - 1)) / n
        x = float(margin)
        for ch in row:
            keys.append({"label": ch, "rect": (x, y, x + unit, y + row_h - gap)})
            x += unit + gap
        y += row_h
    total_units = sum(u for _, u in SPECIALS)
    x = float(margin)
    for label, units in SPECIALS:
        unit_w = usable_w * units / total_units
        keys.append({"label": label,
                     "rect": (x, y, x + unit_w - (gap if label != "DELETE" else 0),
                              y + row_h - gap)})
        x += unit_w
    return keys


def hit_key(keys, x, y):
    """Key under a point, or None."""
    for k in keys:
        x1, y1, x2, y2 = k["rect"]
        if x1 <= x <= x2 and y1 <= y <= y2:
            return k["label"]
    return None
