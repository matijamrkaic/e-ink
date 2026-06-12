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

from colors import BLACK, DARK_GRAY, LIGHT_GRAY
from grid import draw_activity_grid, draw_steps_week

PAD = 16
GRID_W = 110  # width reserved for the dot grid; counts sit to its right
MAX_TYPES = 5  # how many activity types to list

# Y offsets from the top of the health box.
Y_NAME = 4
Y_MET_LABEL = 30  # metric labels (small caption above each value)
Y_MET_VALUE = 46  # metric values (larger)
Y_ACT_LABEL = 90
Y_ACT_TOP = 120
Y_ACT_BOTTOM = 200
Y_STEPS_LABEL = 215
Y_STEPS_TOP = 240


def _draw_value(draw, pos, text, font, fill, gap=2, anchor="la"):
    """Draw a metric value, rendering any '.' as a small baseline dot in a
    narrow gap instead of the full-width monospace period cell (which leaves a
    lot of white space around the point in values like '2.8k'). anchor="ma"
    centers the value horizontally on the given x — a trailing minutes mark (')
    hangs to the right and is excluded from that centering, so the number itself
    stays aligned under the label."""
    x, y = pos
    suffix = ""
    if text.endswith("'"):
        text, suffix = text[:-1], "'"

    dot_r = max(1.0, font.size / 20)
    sep_w = gap * 2 + dot_r * 2
    head, _, tail = text.partition(".")
    head_w = draw.textlength(head, font=font)
    core_w = head_w + (sep_w + draw.textlength(tail, font=font) if tail else 0)

    if anchor == "ma":  # center the number on x, counting only half the suffix
        x -= (core_w + draw.textlength(suffix, font=font) * 0.5) / 2

    draw.text((x, y), head, font=font, fill=fill)
    x += head_w
    if tail:
        baseline = font.getbbox("0")[3]  # digits sit on the baseline (no descender)
        cx, cy = x + gap + 2, y + baseline - dot_r - 1
        draw.rectangle([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=fill)
        x += sep_w
        draw.text((x, y), tail, font=font, fill=fill)
        x += draw.textlength(tail, font=font)
    if suffix:
        draw.text((x, y), suffix, font=font, fill=fill)


def _num(value):
    return "—" if value is None else str(value)


def _hours(seconds):
    """Duration as hours + minutes: 27000s -> \"7h30'\"."""
    if not seconds:
        return "—"
    h, m = divmod(round(seconds / 60), 60)
    return f"{h}h{m:02d}'"


def _kcal(value):
    """Daily calories, rounded to the nearest hundred: 2514 -> '2500'."""
    return "—" if not value else str(round(value / 100) * 100)


def _mins(value):
    """Intensity minutes: 320 -> \"320'\"."""
    return "—" if value is None else f"{value}'"


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
    ("SLEEP•AVG", lambda p: _hours(p.get("avg_sleep_7d"))),
    ("KCAL•AVG", lambda p: _kcal(p.get("avg_kcal_7d"))),
    ("INT•7D", lambda p: _mins(p.get("intensity_7d"))),
]


def draw_health(draw, box, people, fonts):
    """people = list of {name, resting_hr, sleep_score, activities, steps_7d}."""
    x0, y0, x1, y1 = box
    today = date.today()
    n = max(len(people), 1)
    col_w = (x1 - x0) / n

    global_max_steps = (
        max(
            (d["steps"] for p in people for d in (p.get("steps_7d") or [])),
            default=0,
        )
        or 1
    )

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
        # Each column is as wide as its label, and the leftover horizontal space
        # is split into equal gaps between columns (so columns are dynamic, not
        # evenly slotted, but the whitespace between them is uniform).
        label_font = fonts("tiny", "light")
        label_ws = [draw.textlength(label, font=label_font) for label, _ in METRICS]
        avail = col_w - 2 * PAD
        gap = (avail - sum(label_ws)) / (len(METRICS) - 1) if len(METRICS) > 1 else 0
        mx = ix
        for j, (label, value_of) in enumerate(METRICS):
            # Light dividers in the gaps before SLEEP•AVG and before INT•7D,
            # grouping daily metrics | 7-day averages | intensity.
            if j in (2, 4):
                div_x = mx - gap / 2
                draw.line(
                    [(div_x, y0 + Y_MET_LABEL), (div_x, y0 + Y_MET_VALUE + 28)],
                    fill=LIGHT_GRAY,
                    width=1,
                )
            center = mx + label_ws[j] / 2
            draw.text(
                (center, y0 + Y_MET_LABEL),
                label,
                font=label_font,
                fill=DARK_GRAY,
                anchor="ma",
            )
            _draw_value(
                draw,
                (center, y0 + Y_MET_VALUE),
                value_of(person),
                fonts(26, "bold"),
                BLACK,
                anchor="ma",
            )
            mx += label_ws[j] + gap

        # ── Activity dot grid + type counts ──────────────────────────────────
        activities = person.get("activities") or []
        active_dates = {a["date"] for a in activities}
        counts = Counter(a["type"] for a in activities)
        durations = {}
        for a in activities:
            durations[a["type"]] = durations.get(a["type"], 0) + a.get("duration", 0)

        act_prefix = "ACTIVITIES · 5 WEEKS · "
        act_total = f"TOTAL {len(activities)}"
        draw.text(
            (ix, y0 + Y_ACT_LABEL),
            act_prefix,
            font=fonts("tiny", "light"),
            fill=DARK_GRAY,
        )
        prefix_w = draw.textlength(act_prefix, font=fonts("tiny", "light"))
        draw.text(
            (ix + prefix_w, y0 + Y_ACT_LABEL),
            act_total,
            font=fonts("tiny", "bold"),
            fill=BLACK,
        )
        grid_box = (ix, y0 + Y_ACT_TOP, ix + GRID_W, y0 + Y_ACT_BOTTOM)
        draw_activity_grid(draw, grid_box, active_dates, today)

        counts_x = ix + GRID_W + 36
        cy = y0 + Y_ACT_TOP - 2
        if counts:
            sorted_types = sorted(
                counts, key=lambda l: (counts[l], durations.get(l, 0)), reverse=True
            )
            for label in sorted_types[:MAX_TYPES]:
                cnt = counts[label]
                secs = durations.get(label, 0)
                hh = secs // 3600
                mm = (secs % 3600) // 60
                time_str = f"[{hh:02d}:{mm:02d}]"
                draw.text(
                    (counts_x, cy),
                    f"{cnt}",
                    font=fonts(13, "bold"),
                    fill=BLACK,
                    anchor="ra",
                )
                draw.text(
                    (counts_x + 8, cy),
                    f"{time_str} {label}",
                    font=fonts(13, "light"),
                    fill=BLACK,
                )
                cy += 16
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
        steps_prefix = "STEPS · 7 DAYS · "
        steps_total = f"TOTAL {total:,}"
        draw.text(
            (ix, y0 + Y_STEPS_LABEL),
            steps_prefix,
            font=fonts("tiny", "light"),
            fill=DARK_GRAY,
        )
        steps_prefix_w = draw.textlength(steps_prefix, font=fonts("tiny", "light"))
        draw.text(
            (ix + steps_prefix_w, y0 + Y_STEPS_LABEL),
            steps_total,
            font=fonts("tiny", "bold"),
            fill=BLACK,
        )
        steps_box = (ix, y0 + Y_STEPS_TOP, cx1 - PAD, y1 - 4)
        draw_steps_week(draw, steps_box, steps_7d, fonts, global_max=global_max_steps)
