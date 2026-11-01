"""Desktop-demo key plumbing. Pure functions, no GUI, no OS calls.

The floating keyboard reuses app.keyboard_layout geometry placed on a
screen sub-region, plus a suggestion bar and an OS-key row. Selection
resolves to (tokens_to_inject, new_typed_buffer) via label_to_tokens.
"""

from app.words import apply_suggestion, current_prefix

OSKEYS = ["WIN", "ENTER", "BKSP", "ESC"]


def place(keys, ox, oy):
    """Offset layout rects (computed for a box) to canvas coordinates."""
    out = []
    for k in keys:
        x1, y1, x2, y2 = k["rect"]
        out.append({"label": k["label"],
                    "rect": (x1 + ox, y1 + oy, x2 + ox, y2 + oy)})
    return out


def grid_keys(labels, rows, cols, x, y, w, h, gap=12):
    """Grid of equal keys, row-major, as layout-style dicts."""
    unit_w = (w - gap * (cols - 1)) / cols
    unit_h = (h - gap * (rows - 1)) / rows
    keys = []
    for i, label in enumerate(labels):
        r, c = divmod(i, cols)
        x1 = x + c * (unit_w + gap)
        y1 = y + r * (unit_h + gap)
        keys.append({"label": label, "rect": (x1, y1, x1 + unit_w, y1 + unit_h)})
    return keys


def bar_keys(labels, x, y, w, h, gap=12):
    """Row of equal keys (suggestions, OS keys) as layout-style dicts."""
    n = len(labels)
    if n == 0:
        return []
    unit = (w - gap * (n - 1)) / n
    keys = []
    cx = float(x)
    for label in labels:
        keys.append({"label": label, "rect": (cx, y, cx + unit, y + h)})
        cx += unit + gap
    return keys


def label_to_tokens(label, typed):
    """Key label plus typed buffer to (inject_string, new_typed).

    inject_string uses app.inject token syntax ({ENTER}, {BKSP}...).
    Multi-char labels outside the known sets are word suggestions.
    """
    if label == "SPACE":
        return " ", typed + " "
    if label == "DELETE":
        return "{BKSP}", typed[:-1]
    if label in OSKEYS:
        return "{" + label + "}", typed
    if len(label) == 1:
        return label, typed + label
    prefix = current_prefix(typed)
    new_typed = apply_suggestion(typed, label)
    return "{BKSP}" * len(prefix) + label + " ", new_typed
