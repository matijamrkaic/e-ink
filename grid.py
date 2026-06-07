"""
grid.py
=======
Small activity visualizations for the health panel:

  draw_activity_grid — a GitHub-style grid over a date window, with a filled
                       square on each day that had a logged activity (run, gym, …)
                       and a faint empty square on days that didn't.
  draw_steps_week    — a compact daily-steps bar chart (one bar per day) with the
                       step count above each bar and the weekday below.

Both draw inside the box (x0, y0, x1, y1) they're given.
"""

from datetime import timedelta

from colors import BLACK, DARK_GRAY, LIGHT_GRAY


def draw_activity_grid(draw, box, active_dates, end_date, weeks=4):
    """
    active_dates = set of date objects that had >= 1 logged activity.
    Renders a horizontal calendar anchored to whole weeks: weekday columns (Mon
    left → Sun right, 7 wide) and one row per week (oldest top). Always exactly
    `weeks` clean rows ending with the week that contains end_date; days later in
    the current week than end_date just render as empty squares.
    """
    x0, y0, x1, y1 = box
    this_monday = end_date - timedelta(days=end_date.weekday())
    start_monday = this_monday - timedelta(weeks=weeks - 1)

    gap = 3
    cell = min((x1 - x0 - (7 - 1) * gap) / 7, (y1 - y0 - (weeks - 1) * gap) / weeks)
    cell = max(int(cell), 3)
    step = cell + gap

    for offset in range(weeks * 7):
        d = start_monday + timedelta(days=offset)
        col = d.weekday()
        row = offset // 7
        cx = x0 + col * step
        cy = y0 + row * step
        if d in active_dates:
            draw.rectangle([cx, cy, cx + cell, cy + cell], fill=BLACK)
        else:
            draw.rectangle([cx, cy, cx + cell, cy + cell], outline=LIGHT_GRAY, width=1)


def _steps_label(steps):
    """Compact step count: 8400 -> '8.4k', 950 -> '950'."""
    if steps >= 1000:
        return f"{steps / 1000:.1f}k"
    return str(steps)


def draw_steps_week(draw, box, steps_7d, fonts):
    """steps_7d = [{date, steps}] oldest→newest. One bar per day."""
    x0, y0, x1, y1 = box
    if not steps_7d:
        return

    label_h = 16  # weekday labels along the bottom
    count_h = 16  # count text above the tallest bar
    base = y1 - label_h
    top = y0 + count_h
    max_steps = max((d["steps"] for d in steps_7d), default=0) or 1

    n = len(steps_7d)
    slot = (x1 - x0) / n
    bar_w = slot * 0.5

    for i, d in enumerate(steps_7d):
        cx = x0 + slot * i + slot / 2
        bh = (base - top) * (d["steps"] / max_steps)
        y_top = base - bh
        draw.rectangle([cx - bar_w / 1.5, y_top, cx + bar_w / 1.5, base], fill=BLACK)
        draw.text(
            (cx, y_top - 3),
            _steps_label(d["steps"]),
            font=fonts("tiny", "bold"),
            fill=BLACK,
            anchor="mb",
        )
        draw.text(
            (cx, base + 4),
            d["date"].strftime("%a"),
            font=fonts("tiny", "light"),
            fill=DARK_GRAY,
            anchor="mt",
        )
