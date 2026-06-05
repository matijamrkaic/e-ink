"""
panels/health.py
================
Right-hand health panel. Stacks the people from config.PEOPLE vertically; each
gets a name and a row of metrics. For now: resting HR + sleep score. Adding a
metric later is a one-line change to METRICS below.

A metric is (label, key, suffix). Missing values render as "—".
"""

BLACK = 0
GRAY = 180

METRICS = [
    ("RESTING HR", "resting_hr", " bpm"),
    ("SLEEP SCORE", "sleep_score", ""),
]


def draw_health(draw, box, people, fonts):
    """people = list of {name, resting_hr, sleep_score} dicts."""
    x0, y0, x1, y1 = box
    pad = 22
    n = max(len(people), 1)
    row_h = (y1 - y0) / n

    for i, person in enumerate(people):
        ry = y0 + i * row_h
        if i > 0:
            draw.line([(x0 + pad, ry), (x1 - pad, ry)], fill=GRAY, width=1)

        draw.text((x0 + pad, ry + 14), person["name"].upper(), font=fonts["small"], fill=GRAY)

        # Metrics laid out left-to-right across the row.
        metric_y = ry + 48
        col_w = (x1 - x0 - 2 * pad) / len(METRICS)
        for j, (label, key, suffix) in enumerate(METRICS):
            mx = x0 + pad + j * col_w
            value = person.get(key)
            text = "—" if value is None else f"{value}{suffix}"
            draw.text((mx, metric_y), text, font=fonts["large"], fill=BLACK)
            draw.text((mx + 2, metric_y + 52), label, font=fonts["tiny"], fill=GRAY)
