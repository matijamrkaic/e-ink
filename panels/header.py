"""
panels/header.py
================
Header bar: date section | today's weather | forecast days | updated time.
Each section is separated by a thin vertical divider.

data keys expected: weekday, date_fmt, today {icon, high, low},
                    forecast [{day, icon, high, low}, ...]
"""

from colors import BLACK, DARK_GRAY, LIGHT_GRAY, WHITE
from icons import draw_weather_icon

DATE_W = 228  # width of the left date column
PAD = 12  # horizontal padding inside each section

Y_LABEL = 12  # top of small cap label text (relative to y0)
Y_CONTENT = 40  # top of large date / time text (relative to y0)
Y_ICON = 56  # vertical centre of weather icon + inline temp (relative to y0)


def _divider(draw, x, y0, y1):
    draw.line([(x, y0 + 8), (x, y1 - 8)], fill=DARK_GRAY, width=1)


def _weather_col(draw, cx0, y0, label, icon, high, low, fonts, today=False):
    icon_size = 24
    high_font = fonts(18, "bold")
    low_font = fonts(16, "light")

    draw.text((cx0 + PAD, y0 + Y_LABEL), label, font=fonts("tiny", "light"), fill=WHITE)

    icon_cx = cx0 + PAD + icon_size // 2
    icon_cy = y0 + Y_ICON
    if icon is not None:
        draw_weather_icon(draw, icon_cx, icon_cy, icon, icon_size, color=WHITE)

    tx = icon_cx + icon_size // 2 + 10
    ty = y0 + Y_ICON
    high_str = "—" if high is None else f"{high}°"
    high_w = draw.textlength(high_str, font=high_font)
    draw.text((tx, ty), high_str, font=high_font, fill=WHITE, anchor="lm")
    low_str = "—" if low is None else f"/{low}°"
    draw.text((tx + high_w, ty), low_str, font=low_font, fill=WHITE, anchor="lm")


def draw_header(draw, box, data, fonts, now_str):
    """data = weather dict with weekday, date_fmt, today, forecast."""
    x0, y0, x1, y1 = box
    draw.rectangle([(x0, y0), (x1, y1)], fill=BLACK)

    # ── Date section ──────────────────────────────────────────────────────────
    ix = x0 + PAD
    draw.text(
        (ix, y0 + Y_LABEL),
        data["weekday"],
        font=fonts("tiny", "light"),
        fill=WHITE,
    )
    draw.text(
        (DATE_W - PAD - 4, y0 + Y_LABEL),
        now_str,
        font=fonts("tiny", "light"),
        fill=LIGHT_GRAY,
        anchor="ra",
    )
    draw.text(
        (ix, y0 + Y_CONTENT), data["date_fmt"], font=fonts(24, "bold"), fill=WHITE
    )

    # ── Weather columns (today + up to 3 forecast days) ──────────────────────
    forecast = data["forecast"][:3]
    n_cols = 1 + len(forecast)
    col_x0 = x0 + DATE_W
    col_x1 = x1
    col_w = (col_x1 - col_x0) / n_cols

    for i in range(n_cols):
        cx = col_x0 + i * col_w
        _divider(draw, cx, y0, y1)
        if i == 0:
            d = data["today"]
            _weather_col(
                draw, cx, y0, "TODAY", d["icon"], d["high"], d["low"], fonts, today=True
            )
        else:
            d = forecast[i - 1]
            _weather_col(
                draw, cx, y0, d["day"].upper(), d["icon"], d["high"], d["low"], fonts
            )
