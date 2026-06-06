"""
preview.py
==========
Fast, offline layout iteration — no Garmin login, no weather API. Renders the
dashboard from fixture data so you can tweak panels/layout and re-run instantly.

  python preview.py            # render dashboard.png from fixtures
  python preview.py --debug    # same, with the LAYOUT region grid overlaid

The fixtures deliberately exercise edge cases: all three weather icons, a missing
sleep score (renders as "—"), and a real (possibly long, multi-line) quote from
quotes.txt. For pixel-perfect work, keep dashboard.png open in Preview — it
reloads automatically when the file changes.
"""

import sys

import config
from dashboard import build_image
from sources.quote import get_quote

WEATHER = {
    "today": {"icon": "sun", "high": 28, "low": 16},
    "forecast": [
        {"day": "Tue", "icon": "sun", "high": 27, "low": 15},
        {"day": "Wed", "icon": "cloud", "high": 19, "low": 13},
        {"day": "Thu", "icon": "rain", "high": 18, "low": 12},
        {"day": "Fri", "icon": "sun", "high": 24, "low": 14},
    ],
}

PEOPLE = [
    {"name": "Matija", "resting_hr": 52, "sleep_score": 84},
    {"name": "Vanja", "resting_hr": 58, "sleep_score": None},  # tests the "—" case
]


def main():
    if "--debug" in sys.argv:
        config.DEBUG_BOXES = True

    img = build_image(WEATHER, PEOPLE, get_quote())
    img.save(config.OUTPUT_FILE)
    print(f"\n✓ Saved {config.OUTPUT_FILE} (fixture data — no network)\n")


if __name__ == "__main__":
    main()
