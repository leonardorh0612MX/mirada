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


ROWS_ES = ["QWERTYUIOP", "ASDFGHJKLÑ", "ZXCVBNM"]


def board_keyboard(w, y0, h, margin=16, gap=10):
    """Spanish gaze keyboard for the board's phrase band. Pure.

    Three letter rows (with Ñ) plus a SPACE/DELETE row, all inside
    (0, y0, w, y0+h). Keys stay ~170 px wide at 1920: the regime our
    accuracy owns. Suggestion words are placed by the caller above.
    """
    keys = []
    row_h = h / 4.0
    y = float(y0)
    for row in ROWS_ES:
        n = len(row)
        unit = (w - 2 * margin - gap * (n - 1)) / n
        x = float(margin)
        for ch in row:
            keys.append({"label": ch,
                         "rect": (x, y, x + unit, y + row_h - gap)})
            x += unit + gap
        y += row_h
    unit = (w - 2 * margin - gap) / 3.0
    keys.append({"label": "SPACE",
                 "rect": (margin, y, margin + 2 * unit, y + row_h - gap)})
    keys.append({"label": "DELETE",
                 "rect": (margin + 2 * unit + gap, y, w - margin,
                          y + row_h - gap)})
    return keys


def type_text(typed, label):
    """One board-key press on the typed buffer. Pure.

    Letters append lowercase (suggestions carry their own casing via
    app.words.apply_suggestion, handled by the caller).
    """
    if label == "SPACE":
        return typed + " "
    if label == "DELETE":
        return typed[:-1]
    if len(label) == 1:
        return typed + label.lower()
    return typed
