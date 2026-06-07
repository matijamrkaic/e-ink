"""
panels/health.py
================
Health panel: one column per person in config.PEOPLE. Each column stacks, top to
bottom:

  • name
  • compact metrics line (resting HR · sleep score)
  • ACTIVITY · 30 DAYS — a dot grid (filled = a day with a logged activity) next
    to a count of each activity type
  • STEPS · 7 DAYS — a daily-steps bar chart

The vertical offsets below are tuned for the ~250px health band; tweak them and
re-run `python preview.py` to iterate.
"""

from collections import Counter
from datetime import date

from colors import BLACK, DARK_GRAY
from grid import draw_activity_grid, draw_steps_week

PAD = 16
GRID_W = 150  # width reserved for the dot grid; counts sit to its right
MAX_TYPES = 4  # how many activity types to list

# Y offsets from the top of the health box.
Y_NAME = 4
Y_MET_LABEL = 30  # metric labels (small caption above each value)
Y_MET_VALUE = 46  # metric values (larger)
Y_ACT_LABEL = 90
Y_ACT_TOP = 120
Y_ACT_BOTTOM = 200
Y_STEPS_LABEL = 220
Y_STEPS_TOP = 250


def _num(value):
    return "—" if value is None else str(value)


def _hours(seconds):
    return "—" if not seconds else f"{seconds / 3600:.1f}h"


def _bb(p):
    """Overnight Body Battery change, signed (+38 = recharged 38 points)."""
    v = p.get("bb_overnight")
    if v is None:
        return "—"
    return f"+{v}" if v > 0 else str(v)


# Each metric: (label, value-from-person). Small label is drawn above the value.
METRICS = [
    ("RHR", lambda p: _num(p.get("resting_hr"))),
    ("BB GAIN", _bb),
    ("VO2 MAX", lambda p: _num(p.get("vo2max"))),
    ("INT·7D", lambda p: _num(p.get("intensity_7d"))),
    ("SLEEP·7D", lambda p: _hours(p.get("avg_sleep_7d"))),
]


def draw_health(draw, box, people, fonts):
    """people = list of {name, resting_hr, sleep_score, activities, steps_7d}."""
    x0, y0, x1, y1 = box
    today = date.today()
    n = max(len(people), 1)
    col_w = (x1 - x0) / n

    global_max_steps = max(
        (d["steps"] for p in people for d in (p.get("steps_7d") or [])),
        default=0,
    ) or 1

    for i, person in enumerate(people):
        cx0 = x0 + i * col_w
        cx1 = cx0 + col_w
        ix = cx0 + PAD
        if i > 0:
            draw.line([(cx0, y0 + 12), (cx0, y1 - 12)], fill=DARK_GRAY, width=1)

        # Name
        draw.text(
            (ix, y0 + Y_NAME),
            person["name"].upper(),
            font=fonts("small", "bold"),
            fill=DARK_GRAY,
        )

        # Metrics grid: small light label above larger bold value, one per cell.
        mslot = (col_w - 2 * PAD) / len(METRICS)
        for j, (label, value_of) in enumerate(METRICS):
            mx = ix + j * mslot
            draw.text(
                (mx, y0 + Y_MET_LABEL),
                label,
                font=fonts("tiny", "light"),
                fill=DARK_GRAY,
            )
            draw.text(
                (mx, y0 + Y_MET_VALUE),
                value_of(person),
                font=fonts("medium", "bold"),
                fill=BLACK,
            )

        # ── Activity dot grid + type counts ──────────────────────────────────
        activities = person.get("activities") or []
        active_dates = {a["date"] for a in activities}
        counts = Counter(a["type"] for a in activities)

        draw.text(
            (ix, y0 + Y_ACT_LABEL),
            f"ACTIVITIES · 4 WEEKS · TOTAL {len(activities)}",
            font=fonts("tiny", "light"),
            fill=DARK_GRAY,
        )
        grid_box = (ix, y0 + Y_ACT_TOP, ix + GRID_W, y0 + Y_ACT_BOTTOM)
        draw_activity_grid(draw, grid_box, active_dates, today)

        counts_x = ix + GRID_W + 36
        cy = y0 + Y_ACT_TOP - 2
        if counts:
            for label, cnt in counts.most_common(MAX_TYPES):
                draw.text(
                    (counts_x, cy),
                    f"{cnt}",
                    font=fonts(16, "bold"),
                    fill=BLACK,
                    anchor="ra",
                )
                draw.text(
                    (counts_x + 8, cy), label, font=fonts(16, "light"), fill=BLACK
                )
                cy += 20
        else:
            draw.text(
                (counts_x, cy),
                "No activities",
                font=fonts("tiny", "light"),
                fill=DARK_GRAY,
            )

        # ── 7-day steps bar chart ────────────────────────────────────────────
        steps_7d = person.get("steps_7d") or []
        total = sum(d["steps"] for d in steps_7d)
        steps_label = f"STEPS · 7 DAYS · TOTAL {total:,}"
        draw.text(
            (ix, y0 + Y_STEPS_LABEL),
            steps_label,
            font=fonts("tiny", "light"),
            fill=DARK_GRAY,
        )
        steps_box = (ix, y0 + Y_STEPS_TOP, cx1 - PAD, y1 - 4)
        draw_steps_week(draw, steps_box, steps_7d, fonts, global_max=global_max_steps)
