"""
panels/header.py
================
Top bar. Row 1: today's date + today's weather inline (icon + high/low) on the
left, "Updated HH:MM" on the right. Row 2: a strip of the next few days, each as
a small "Day  icon  hi°/lo°" box separated by thin dividers.

Like every panel, it only draws inside its `box` = (x0, y0, x1, y1).
"""

from icons import draw_weather_icon

BLACK = 0
WHITE = 255
GRAY = 180


def draw_header(draw, box, data, fonts, now_str):
    """data = weather dict {today, forecast}; now_str = 'HH:MM' update time."""
    x0, y0, x1, y1 = box
    draw.rectangle([(x0, y0), (x1, y1)], fill=BLACK)

    # ── Row 1: date + today's weather ─────────────────────────────────────────
    pad = 20
    draw.text((x0 + pad, y0 + 12), data["date"], font=fonts["medium"], fill=WHITE)

    # Date width → place the today icon just after it.
    date_w = draw.textlength(data["date"], font=fonts["medium"])
    icon_cx = x0 + pad + date_w + 35
    icon_cy = y0 + 28
    today = data["today"]
    draw_weather_icon(draw, icon_cx, icon_cy, today["icon"], 34, color=WHITE)
    draw.text(
        (icon_cx + 28, y0 + 12),
        f"{today['high']}°/{today['low']}°",
        font=fonts["medium"],
        fill=WHITE,
    )

    draw.text(
        (x1 - pad, y0 + 16),
        f"Updated {now_str}",
        font=fonts["tiny"],
        fill=GRAY,
        anchor="ra",
    )

    # ── Row 2: forecast strip ─────────────────────────────────────────────────
    strip_y = y0 + 62
    forecast = data["forecast"]
    if not forecast:
        return
    slot_w = (x1 - x0 - 2 * pad) / len(forecast)
    for i, day in enumerate(forecast):
        sx = x0 + pad + i * slot_w
        draw.text((sx, strip_y + 6), day["day"], font=fonts["small"], fill=WHITE)
        day_w = draw.textlength(day["day"], font=fonts["small"])
        draw_weather_icon(draw, sx + day_w + 18, strip_y + 16, day["icon"], 22, color=WHITE)
        draw.text(
            (sx + day_w + 34, strip_y + 6),
            f"{day['high']}°/{day['low']}°",
            font=fonts["small"],
            fill=WHITE,
        )
        if i > 0:
            draw.line([(sx - 8, strip_y), (sx - 8, strip_y + 34)], fill=GRAY, width=1)
