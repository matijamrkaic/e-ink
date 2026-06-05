"""
ga.py
==================
A Garmin Connect daily-stats dashboard that generates an 800x480 image — the
exact size of a 7.5" Waveshare e-ink display. Mirrors the structure of
weather.py: fetch → parse → draw → save/preview.

Learning goals in this file:
  1. Authenticating against Garmin Connect (with token caching)
  2. Pulling daily stats + a 7-day history
  3. Drawing a mixed dashboard: big stat, detail rows, bar chart
  4. Re-using the same e-ink layout discipline from weather.py

Requirements (install once):
  pip install garminconnect Pillow

Credentials (set once in your shell):
  export GARMIN_EMAIL="you@example.com"
  export GARMIN_PASSWORD="your-password"

Run:
  python ga.py
"""

# ── Imports ──────────────────────────────────────────────────────────────────
import json
import os
import sys
from datetime import date, datetime, timedelta

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from PIL import Image, ImageDraw, ImageFont

# ── Configuration ─────────────────────────────────────────────────────────────
GARMIN_EMAIL = os.environ.get("GARMIN_EMAIL")
GARMIN_PASSWORD = os.environ.get("GARMIN_PASSWORD")

# Headless auth for CI: garminconnect natively reads a serialized token string
# from the GARMINTOKENS env var (login() loads it when it's longer than a path).
# Set it as a GitHub Actions secret so the workflow never needs the password.
GARMIN_TOKENS = os.environ.get("GARMINTOKENS")

# Where to cache the token store on disk so we don't log in fresh every run.
TOKEN_STORE = os.path.expanduser("~/.garminconnect")

# How many days of history to include in the trend chart (including today).
HISTORY_DAYS = 7

# E-ink display resolution. Don't change this — matches the 7.5" Waveshare.
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

OUTPUT_FILE = "garmin_preview.png"


# ── Step 1: Fetch Garmin data ────────────────────────────────────────────────
def _print_token_blob(api):
    """
    Print the current session as a one-line token string. Copy it into a GitHub
    Actions secret named GARMINTOKENS so CI can authenticate headlessly —
    login() reads that env var natively and loads the string (no password, no
    MFA on the runner).
    """
    blob = api.client.dumps()
    print("\n" + "─" * 70)
    print("GARMINTOKENS (store this as a GitHub Actions secret):")
    print("─" * 70)
    print(blob)
    print("─" * 70 + "\n")


def _login():
    """
    Log into Garmin Connect, re-using cached tokens when possible.

    garminconnect's own login(tokenstore) handles all three cases for us:
      • tokenstore is a serialized token string (CI, via GARMINTOKENS) → load it
      • tokenstore is a path with cached tokens (local repeat run)     → resume
      • no/invalid tokens but email+password set                        → log in
        fresh and persist to the path
    So we just hand it the right tokenstore and let it self-heal.
    """
    have_cache = os.path.exists(TOKEN_STORE)
    if not GARMIN_TOKENS and not have_cache and not (GARMIN_EMAIL and GARMIN_PASSWORD):
        sys.exit(
            "✗ Missing credentials. Set GARMINTOKENS (preferred for CI) or "
            "GARMIN_EMAIL + GARMIN_PASSWORD and try again."
        )

    api = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)

    # Prefer the serialized token string from the env (CI); otherwise use the
    # on-disk cache path, which login() also writes back to after a fresh login.
    tokenstore = GARMIN_TOKENS or TOKEN_STORE

    try:
        api.login(tokenstore)
        print("  ✓ Garmin session ready")
    except (GarminConnectAuthenticationError, FileNotFoundError) as err:
        sys.exit(f"✗ Garmin authentication failed: {err}")

    # On local runs, surface the token string so it can be pasted into the CI
    # secret. Skip when GARMINTOKENS is already set (i.e. we're on the runner).
    if not GARMIN_TOKENS:
        _print_token_blob(api)

    return api


def fetch_garmin():
    """
    Pull today's stats plus a HISTORY_DAYS step history.
    Returns the raw dicts; parsing happens in the next step.
    """
    print("→ Fetching Garmin Connect data...")

    api = _login()

    today = date.today()
    today_iso = today.isoformat()

    try:
        stats = api.get_stats(today_iso)
        sleep = api.get_sleep_data(today_iso)
        user_summary = api.get_user_summary(today_iso)

        # 7-day step history — one call returns a list of dicts
        start = (today - timedelta(days=HISTORY_DAYS - 1)).isoformat()
        steps_history = api.get_daily_steps(start, today_iso)
    except (
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    ) as err:
        sys.exit(f"✗ Garmin API error: {err}")

    print(f"  ✓ Got daily stats for {today_iso}")
    return {
        "stats": stats,
        "sleep": sleep,
        "user_summary": user_summary,
        "steps_history": steps_history,
        "today": today,
    }


# ── Step 2: Parse into clean variables ────────────────────────────────────────
def _safe(d, *keys, default=None):
    """Dive into nested dicts without KeyError/TypeError."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur or cur[k] is None:
            return default
        cur = cur[k]
    return cur


def _fmt_duration(seconds):
    """Turn a seconds value into 'Hh Mm'."""
    if not seconds:
        return "—"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"


def parse_garmin(raw):
    """Extract just what the dashboard needs into a flat dict."""
    stats = raw["stats"] or {}
    sleep = raw["sleep"] or {}
    today = raw["today"]

    steps = stats.get("totalSteps") or 0
    step_goal = stats.get("dailyStepGoal") or 10000
    distance_m = stats.get("totalDistanceMeters") or 0
    calories = stats.get("totalKilocalories") or 0
    active_cal = stats.get("activeKilocalories") or 0
    resting_hr = stats.get("restingHeartRate")
    active_minutes = (stats.get("moderateIntensityMinutes") or 0) + (
        stats.get("vigorousIntensityMinutes") or 0
    ) * 2  # Garmin's standard "intensity minutes" weighting
    floors = stats.get("floorsAscended") or 0
    body_battery = stats.get("bodyBatteryMostRecentValue")
    stress = stats.get("averageStressLevel")

    sleep_seconds = _safe(sleep, "dailySleepDTO", "sleepTimeSeconds", default=0)

    # Build the steps history list as (label, steps) tuples, oldest first.
    history = []
    for entry in raw["steps_history"] or []:
        day_str = entry.get("calendarDate")
        if not day_str:
            continue
        day_dt = datetime.strptime(day_str, "%Y-%m-%d").date()
        history.append(
            {
                "day": day_dt.strftime("%a"),
                "is_today": day_dt == today,
                "steps": int(entry.get("totalSteps") or 0),
                "goal": int(entry.get("stepGoal") or step_goal),
            }
        )

    # Sort oldest → newest just in case the API returns them differently
    history.sort(key=lambda h: h["day"])  # weak sort; fine since we passed range

    return {
        "date": today.strftime("%A, %d %B %Y"),
        "time": datetime.now().strftime("%H:%M"),
        "steps": steps,
        "step_goal": step_goal,
        "step_pct": min(1.0, steps / step_goal) if step_goal else 0,
        "distance_km": distance_m / 1000.0,
        "calories": calories,
        "active_calories": active_cal,
        "resting_hr": resting_hr,
        "active_minutes": active_minutes,
        "floors": floors,
        "body_battery": body_battery,
        "stress": stress,
        "sleep_str": _fmt_duration(sleep_seconds),
        "history": history,
    }


# ── Step 3: Load fonts ────────────────────────────────────────────────────────
def load_fonts():
    """Same approach as weather.py — try a few system fonts, fall back gracefully."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    found_path = next((p for p in font_paths if os.path.exists(p)), None)
    if found_path:
        print(f"  ✓ Using font: {found_path}")
    else:
        print("  ⚠ No TTF font found, using PIL default (less pretty)")

    def make_font(size):
        if found_path:
            try:
                return ImageFont.truetype(found_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    return {
        "tiny": make_font(14),
        "small": make_font(20),
        "medium": make_font(28),
        "large": make_font(44),
        "huge": make_font(96),
    }


# ── Step 4: Draw the image ────────────────────────────────────────────────────
def draw_image(g):
    """
    Layout:
    ┌─────────────────────────────────────────────────────────┐
    │ GARMIN — Date · Time                                    │  header
    ├──────────────────────────────┬──────────────────────────┤
    │  STEPS  12,438 / 10,000      │  RESTING HR   54         │
    │  ████████████████░░░░  124%  │  SLEEP        7h 32m     │
    │                              │  CALORIES     2,310      │
    │  Distance · Active mins ...  │  STRESS       28         │
    ├──────────────────────────────┴──────────────────────────┤
    │  7-day steps bar chart                                   │
    └─────────────────────────────────────────────────────────┘
    """
    print("→ Drawing image...")
    fonts = load_fonts()

    img = Image.new("L", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=255)
    draw = ImageDraw.Draw(img)

    BLACK = 0
    WHITE = 255
    GRAY = 180
    LIGHT = 230

    HEADER_H = 60
    CHART_H = 150
    MID_TOP = HEADER_H
    MID_BOTTOM = DISPLAY_HEIGHT - CHART_H
    LEFT_W = 470

    # ── Header bar ────────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (DISPLAY_WIDTH, HEADER_H)], fill=BLACK)
    draw.text((20, 10), "GARMIN", font=fonts["large"], fill=WHITE)
    draw.text(
        (DISPLAY_WIDTH - 20, 8),
        g["date"],
        font=fonts["small"],
        fill=WHITE,
        anchor="ra",
    )
    draw.text(
        (DISPLAY_WIDTH - 20, 34),
        f"Updated {g['time']}",
        font=fonts["tiny"],
        fill=GRAY,
        anchor="ra",
    )

    # ── Left panel: big steps + progress bar ──────────────────────────────────
    draw.text((20, MID_TOP + 10), "STEPS", font=fonts["tiny"], fill=GRAY)
    draw.text(
        (20, MID_TOP + 22),
        f"{g['steps']:,}",
        font=fonts["huge"],
        fill=BLACK,
    )
    draw.text(
        (20, MID_TOP + 130),
        f"of {g['step_goal']:,} goal · {int(g['step_pct'] * 100)}%",
        font=fonts["small"],
        fill=GRAY,
    )

    # Progress bar
    bar_x, bar_y = 20, MID_TOP + 165
    bar_w, bar_h = LEFT_W - 40, 18
    draw.rectangle(
        [(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], outline=BLACK, width=2
    )
    fill_w = int(bar_w * g["step_pct"])
    if fill_w > 0:
        draw.rectangle(
            [
                (bar_x + 2, bar_y + 2),
                (bar_x + 2 + max(0, fill_w - 4), bar_y + bar_h - 2),
            ],
            fill=BLACK,
        )

    # Secondary stats under the bar
    def mini_stat(x, y, label, value):
        draw.text((x, y), label, font=fonts["tiny"], fill=GRAY)
        draw.text((x, y + 16), value, font=fonts["medium"], fill=BLACK)

    row_y = MID_TOP + 200
    mini_stat(20, row_y, "DISTANCE", f"{g['distance_km']:.2f} km")
    mini_stat(170, row_y, "ACTIVE MIN", f"{g['active_minutes']}")
    mini_stat(320, row_y, "FLOORS", f"{g['floors']}")

    # ── Vertical divider ──────────────────────────────────────────────────────
    draw.line(
        [(LEFT_W, MID_TOP + 10), (LEFT_W, MID_BOTTOM - 10)],
        fill=GRAY,
        width=1,
    )

    # ── Right panel: detail rows ──────────────────────────────────────────────
    details = [
        ("RESTING HR", f"{g['resting_hr']} bpm" if g["resting_hr"] else "—"),
        ("SLEEP", g["sleep_str"]),
        ("CALORIES", f"{int(g['calories']):,}"),
        ("ACTIVE CAL", f"{int(g['active_calories']):,}"),
        ("STRESS", f"{g['stress']}" if g["stress"] is not None else "—"),
        (
            "BODY BATTERY",
            f"{g['body_battery']}" if g["body_battery"] is not None else "—",
        ),
    ]

    detail_x = LEFT_W + 25
    detail_y = MID_TOP + 15
    # Lay them out in a 2-column grid: 3 rows of 2.
    col_w = (DISPLAY_WIDTH - detail_x - 15) // 2
    row_h = (MID_BOTTOM - MID_TOP - 30) // 3
    for i, (label, value) in enumerate(details):
        col = i % 2
        row = i // 2
        x = detail_x + col * col_w
        y = detail_y + row * row_h
        draw.text((x, y), label, font=fonts["tiny"], fill=GRAY)
        draw.text((x, y + 18), value, font=fonts["medium"], fill=BLACK)

    # ── Horizontal divider above chart ────────────────────────────────────────
    draw.line(
        [(0, MID_BOTTOM), (DISPLAY_WIDTH, MID_BOTTOM)],
        fill=BLACK,
        width=2,
    )

    # ── Bottom panel: 7-day step bar chart ────────────────────────────────────
    chart_top = MID_BOTTOM + 30
    chart_bottom = DISPLAY_HEIGHT - 30
    chart_left = 30
    chart_right = DISPLAY_WIDTH - 30
    chart_height = chart_bottom - chart_top

    draw.text(
        (chart_left, MID_BOTTOM + 6),
        f"LAST {len(g['history'])} DAYS · STEPS",
        font=fonts["tiny"],
        fill=GRAY,
    )

    history = g["history"]
    if history:
        max_steps = max((h["steps"] for h in history), default=0)
        # Make the goal line visible even when all days fell short
        scale_max = max(max_steps, g["step_goal"]) or 1

        slot_w = (chart_right - chart_left) / len(history)
        bar_w = int(slot_w * 0.6)

        # Goal reference line
        goal_y = chart_bottom - int(chart_height * (g["step_goal"] / scale_max))
        for x in range(chart_left, chart_right, 6):
            draw.line([(x, goal_y), (x + 3, goal_y)], fill=GRAY, width=1)
        draw.text(
            (chart_right + 2, goal_y - 8),
            "goal",
            font=fonts["tiny"],
            fill=GRAY,
            anchor="rt",
        )

        for i, h in enumerate(history):
            cx = int(chart_left + slot_w * i + slot_w / 2)
            bar_h = int(chart_height * (h["steps"] / scale_max)) if scale_max else 0
            x0 = cx - bar_w // 2
            x1 = cx + bar_w // 2
            y0 = chart_bottom - bar_h
            y1 = chart_bottom

            if h["is_today"]:
                draw.rectangle([(x0, y0), (x1, y1)], fill=BLACK)
            else:
                draw.rectangle([(x0, y0), (x1, y1)], fill=LIGHT, outline=BLACK, width=1)

            # Day label
            draw.text(
                (cx, chart_bottom + 4),
                h["day"],
                font=fonts["tiny"],
                fill=BLACK,
                anchor="mt",
            )

    print("  ✓ Image drawn")
    return img


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n╔══════════════════════════════════╗")
    print("║   E-Ink Garmin Daily Stats       ║")
    print("╚══════════════════════════════════╝\n")

    raw = fetch_garmin()
    g = parse_garmin(raw)

    print("\n→ Parsed stats:")
    print(json.dumps(g, indent=2, default=str))

    print()
    img = draw_image(g)

    print()
    img.save(OUTPUT_FILE)

    print("\n✓ Done!\n")


if __name__ == "__main__":
    main()
