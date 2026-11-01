"""T14 report: error-over-time figure (dependency-free SVG) plus summary table.

Input: dot-anchored error series per strategy: {name: [(t, err_px), ...]}.
Output: figure.svg and table.md in the given directory. Returns summary dict.
"""

import os

COLORS = {"A": "#d62728", "B": "#ff7f0e", "C": "#2ca02c", "D": "#1f77b4"}
W, H, PAD = 640, 360, 48


def _scale(series_dict):
    tmax = max((t for s in series_dict.values() for t, _ in s), default=1.0)
    emax = max((e for s in series_dict.values() for _, e in s), default=1.0)
    tmax = tmax or 1.0
    emax = emax or 1.0
    return tmax, emax


def _poly(points, color):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>'


def write_figure(series_dict, path):
    tmax, emax = _scale(series_dict)
    iw, ih = W - 2 * PAD, H - 2 * PAD

    def xy(t, e):
        return (PAD + iw * t / tmax, H - PAD - ih * e / emax)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">']
    parts.append(f'<line x1="{PAD}" y1="{H - PAD}" x2="{W - PAD}" y2="{H - PAD}" stroke="#333"/>')
    parts.append(f'<line x1="{PAD}" y1="{PAD}" x2="{PAD}" y2="{H - PAD}" stroke="#333"/>')
    parts.append(f'<text x="{W - PAD}" y="{H - 10}" font-size="12" text-anchor="end">time (s)</text>')
    parts.append(f'<text x="10" y="{PAD - 8}" font-size="12">error (px)</text>')
    legend_y = PAD
    for name in sorted(series_dict):
        series = series_dict[name]
        if series:
            parts.append(_poly([xy(t, e) for t, e in series], COLORS.get(name, "#000")))
        parts.append(f'<circle cx="{W - 130}" cy="{legend_y}" r="4" fill="{COLORS.get(name, "#000")}"/>')
        parts.append(f'<text x="{W - 122}" y="{legend_y + 4}" font-size="12">{name}</text>')
        legend_y += 18
    parts.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return path


def summarize_all(series_dict):
    out = {}
    for name, series in series_dict.items():
        if not series:
            out[name] = {"n": 0, "mean_px": float("nan"), "slope_px_s": 0.0}
            continue
        n = len(series)
        mean = sum(e for _, e in series) / n
        sx = sum(t for t, _ in series)
        sy = sum(e for _, e in series)
        sxx = sum(t * t for t, _ in series)
        sxy = sum(t * e for t, e in series)
        denom = n * sxx - sx * sx
        slope = (n * sxy - sx * sy) / denom if abs(denom) > 1e-12 else 0.0
        out[name] = {"n": n, "mean_px": mean, "slope_px_s": slope}
    return out


def write_table(summary, path):
    lines = ["| strategy | n | mean err (px) | drift slope (px/s) |",
             "| --- | --- | --- | --- |"]
    for name in sorted(summary):
        s = summary[name]
        lines.append(f"| {name} | {s['n']} | {s['mean_px']:.1f} | {s['slope_px_s']:.4f} |")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def write_report(series_dict, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    summary = summarize_all(series_dict)
    fig = write_figure(series_dict, os.path.join(out_dir, "figure.svg"))
    tab = write_table(summary, os.path.join(out_dir, "table.md"))
    return {"summary": summary, "figure": fig, "table": tab}
