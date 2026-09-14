"""
charts/label_utils.py

Overlap-free text-label placement for scatter charts.

px.scatter's fixed textposition ("top center") makes labels collide
whenever points cluster — e.g. Board Size vs Performance, where half
the boards sit around 40-50% pass. This helper converts every point to
pixel space (using the chart's explicit axis ranges), then greedily
assigns each label the first of 8 candidate positions (above, below,
left, right, 4 diagonals) whose label box does not overlap any label
already placed or any other point's dot. Crowded points claim space
first (smallest nearest-neighbour distance). If every candidate
collides, the least-overlapping one wins — overlap is minimized, never
accepted by default.

Charts must set EXPLICIT axis ranges matching the ones passed here, so
the pixel math matches what Plotly renders.
"""

import math

import plotly.graph_objects as go

_CANDIDATES = (
    "top center", "bottom center",
    "middle right", "middle left",
    "top right", "top left", "bottom right", "bottom left",
)


def _box_for(pos: str, cx: float, cy: float, w: float, h: float, gap: float):
    """Label box (x0, y0, x1, y1) in px, y pointing DOWN, for a given
    plotly textposition relative to the point at (cx, cy)."""
    if pos == "top center":
        return (cx - w / 2, cy - gap - h, cx + w / 2, cy - gap)
    if pos == "bottom center":
        return (cx - w / 2, cy + gap, cx + w / 2, cy + gap + h)
    if pos == "middle right":
        return (cx + gap, cy - h / 2, cx + gap + w, cy + h / 2)
    if pos == "middle left":
        return (cx - gap - w, cy - h / 2, cx - gap, cy + h / 2)
    if pos == "top right":
        return (cx + gap, cy - gap - h, cx + gap + w, cy - gap)
    if pos == "top left":
        return (cx - gap - w, cy - gap - h, cx - gap, cy - gap)
    if pos == "bottom right":
        return (cx + gap, cy + gap, cx + gap + w, cy + gap + h)
    return (cx - gap - w, cy + gap, cx - gap, cy + gap + h)  # bottom left


def _overlap_area(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if (w > 0 and h > 0) else 0.0


def assign_scatter_label_positions(
    labels,
    xs,
    ys,
    x_range,
    y_range,
    plot_width: float = 560.0,
    plot_height: float = 330.0,
    font_size: float = 9.0,
    point_radius: float = 8.0,
    return_boxes: bool = False,
):
    """Returns {(rounded_x, rounded_y, label): plotly_textposition} for
    every point. Pass the SAME label/x/y series the scatter traces are
    built from, plus the exact axis ranges set on the figure.

    Candidates: 8 directions × increasing stand-off distances, so dense
    clusters push their labels progressively further out instead of
    overlapping. Only if literally every candidate collides does the
    least-overlapping one win."""
    x0, x1 = x_range
    y0, y1 = y_range
    span_x = (x1 - x0) or 1.0
    span_y = (y1 - y0) or 1.0

    def _px(x: float) -> float:
        return (x - x0) / span_x * plot_width

    def _py(y: float) -> float:
        return plot_height - (y - y0) / span_y * plot_height

    char_w = font_size * 0.62
    box_h = font_size * 1.35
    distances = (4.0, 9.0, 16.0, 25.0, 38.0)

    pts = [(_px(float(x)), _py(float(y)), str(lab),
            (round(float(x), 8), round(float(y), 8), str(lab)))
           for lab, x, y in zip(labels, xs, ys)]
    if not pts:
        return {}

    def _crowding(i: int) -> float:
        best = float("inf")
        for j, (x, y, _, _) in enumerate(pts):
            if j != i:
                best = min(best, math.hypot(pts[i][0] - x, pts[i][1] - y))
        return best

    # Crowded points first — they claim clear space before isolated,
    # easily-placed labels take it.
    order = sorted(range(len(pts)), key=_crowding)

    dot_boxes = [(x - point_radius, y - point_radius, x + point_radius, y + point_radius)
                 for x, y, _, _ in pts]
    placed = []
    out = {}
    boxes = {}

    for i in order:
        cx, cy, lab, key = pts[i]
        w = max(24.0, len(lab) * char_w)
        best = None
        for dist in distances:
            for pos in _CANDIDATES:
                box = _box_for(pos, cx, cy, w, box_h, dist)
                # keep the label fully inside the plot area
                if box[0] < 0 or box[1] < 0 or box[2] > plot_width or box[3] > plot_height:
                    continue
                clash = 0.0
                for b in placed:
                    clash = max(clash, _overlap_area(box, b))
                for k, db in enumerate(dot_boxes):
                    if k != i:
                        clash = max(clash, _overlap_area(box, db))
                if best is None or clash < best[0]:
                    best = (clash, pos, box)
                if clash == 0.0:
                    break
            if best is not None and best[0] == 0.0:
                break
        clash, pos, box = best
        placed.append(box)
        out[key] = pos
        boxes[key] = box
    return (out, boxes) if return_boxes else out


def apply_positions(fig: go.Figure, pos_map: dict) -> None:
    """Applies a position map to every text-labelled trace of a scatter
    figure (traces without text — e.g. reference lines — are skipped)."""
    for tr in fig.data:
        if tr.text is None:
            continue
        tr.textposition = [
            pos_map[(round(float(x), 8), round(float(y), 8), str(t))]
            for x, y, t in zip(tr.x, tr.y, tr.text)
        ]