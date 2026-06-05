"""
icons.py
========
Weather icons drawn as vector primitives, not emoji. The CI runner's DejaVu font
can't render color weather emoji (they'd come out as empty boxes), and crisp
shapes look better on a 1-bit e-ink panel anyway.

Only three kinds, matching the simplified forecast: "sun", "cloud", "rain".
`color` lets the same icon render dark on a white panel or white on the black
header.
"""

from math import cos, pi, sin


def draw_weather_icon(draw, cx, cy, kind, size, color=0):
    """
    Draw a weather icon centered at (cx, cy), fitting roughly within `size` px,
    stroked in `color` (0 = black default, 255 = white for the dark header).
    """
    r = size / 2
    if kind == "sun":
        _sun(draw, cx, cy, r, color)
    elif kind == "rain":
        _cloud(draw, cx, cy - r * 0.15, r, color)
        _rain(draw, cx, cy + r * 0.55, r, color)
    else:  # "cloud" and any unknown bucket
        _cloud(draw, cx, cy, r, color)


def _sun(draw, cx, cy, r, color):
    # Filled disc + rays. Filling avoids thin-outline artifacts at small sizes.
    core = r * 0.55
    for i in range(8):
        a = i * pi / 4
        x0 = cx + cos(a) * core * 1.3
        y0 = cy + sin(a) * core * 1.3
        x1 = cx + cos(a) * r
        y1 = cy + sin(a) * r
        draw.line([(x0, y0), (x1, y1)], fill=color, width=2)
    draw.ellipse([cx - core, cy - core, cx + core, cy + core], fill=color)


def _cloud(draw, cx, cy, r, color):
    # Overlapping FILLED lobes merge into one shape — no internal seams, so it
    # stays clean even at ~20px.
    small = r * 0.5
    big = r * 0.7
    draw.ellipse([cx - r, cy - small * 0.6, cx - r + small * 2, cy + small], fill=color)
    draw.ellipse([cx + r - small * 2, cy - small * 0.6, cx + r, cy + small], fill=color)
    draw.ellipse([cx - big, cy - big, cx + big, cy + big * 0.7], fill=color)
    draw.rectangle([cx - r + small * 0.4, cy, cx + r - small * 0.4, cy + small], fill=color)


def _rain(draw, cx, cy, r, color):
    for dx in (-r * 0.45, 0, r * 0.45):
        x = cx + dx
        draw.line([(x, cy), (x - r * 0.18, cy + r * 0.45)], fill=color, width=2)
