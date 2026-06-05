"""
config.py
=========
Single source of truth for everything you'll tweak while iterating: display
size, who the people are, where to look up weather, file paths, and — most
importantly — the LAYOUT.

LAYOUT is the whole point of this project's structure. Every panel is just a
rectangle on the 800x480 canvas, named here. To move or resize a panel you edit
one tuple below; no drawing code changes. Set DEBUG_BOXES = True to render the
outlines + labels of every region so you can eyeball the grid before filling it.
"""

import os

# Load a local .env (gitignored) so credentials don't have to be re-exported in
# every shell. CI sets real env vars instead, so a missing .env is fine.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ── E-ink display resolution. Don't change — matches the 7.5" Waveshare. ──────
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

OUTPUT_FILE = "dashboard.png"

# ── People (two Garmin accounts) ──────────────────────────────────────────────
# Each person reads its own credentials from env vars so husband + wife never
# collide. For CI, set the *_TOKENS secret (headless); locally, *_EMAIL/*_PASSWORD
# is enough and a token blob gets printed for you to copy into the secret.
PEOPLE = [
    {
        "name": "Matija",
        "email_env": "GARMIN_EMAIL_H",
        "password_env": "GARMIN_PASSWORD_H",
        "tokens_env": "GARMINTOKENS_H",
        "token_store": os.path.expanduser("~/.garminconnect_h"),
    },
    {
        "name": "Vanja",
        "email_env": "GARMIN_EMAIL_W",
        "password_env": "GARMIN_PASSWORD_W",
        "tokens_env": "GARMINTOKENS_W",
        "token_store": os.path.expanduser("~/.garminconnect_w"),
    },
]

# ── Weather location (Belgrade default; find yours at latlong.net) ────────────
LATITUDE = 44.8125
LONGITUDE = 20.4612
TIMEZONE = "Europe/Belgrade"
FORECAST_DAYS = 5  # today + next 4 shown in the header strip

# ── Quotes ────────────────────────────────────────────────────────────────────
# Plain text file, entries separated by a blank line. One random entry per run.
QUOTES_FILE = "quotes.txt"

# ── Layout ────────────────────────────────────────────────────────────────────
# Each region is (x0, y0, x1, y1) on the canvas. Edit these to rearrange.
LAYOUT = {
    "header": (0, 0, DISPLAY_WIDTH, 130),
    "quote": (0, 130, 400, DISPLAY_HEIGHT),
    "health": (400, 130, DISPLAY_WIDTH, DISPLAY_HEIGHT),
}

# Flip to True to draw each region's outline + name. Great for layout iteration.
DEBUG_BOXES = False
