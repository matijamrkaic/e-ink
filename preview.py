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

import random
import sys
from datetime import date, timedelta

import config
from dashboard import build_image
from sources.quote import get_quote


def _mock_activities(seed):
    """~4 weeks of logged activities (some days off, some doubled) for the grid."""
    rng = random.Random(seed)
    today = date.today()
    types = ["Run", "Gym", "Boxing", "Swim", "Walk"]
    out = []
    for i in range(28):
        d = today - timedelta(days=27 - i)
        if rng.random() < 0.5:
            out.append({"date": d, "type": rng.choice(types)})
            if rng.random() < 0.2:  # occasional second session
                out.append({"date": d, "type": rng.choice(types)})
    return out


def _mock_steps_week(seed):
    """7 days of step counts, oldest→newest."""
    rng = random.Random(seed)
    today = date.today()
    return [{"date": today - timedelta(days=6 - i), "steps": rng.randint(3000, 16000)} for i in range(7)]

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
    {
        "name": "Matija", "resting_hr": 52, "bb_overnight": 47,
        "avg_kcal_7d": 2840, "intensity_7d": 320, "avg_sleep_7d": 7.3 * 3600,
        "activities": _mock_activities(1), "steps_7d": _mock_steps_week(1),
    },
    {
        "name": "Vanja", "resting_hr": 58, "bb_overnight": 39,
        "avg_kcal_7d": None, "intensity_7d": 210, "avg_sleep_7d": 6.9 * 3600,
        "activities": _mock_activities(7), "steps_7d": _mock_steps_week(7),
    },
]


def main():
    if "--debug" in sys.argv:
        config.DEBUG_BOXES = True

    img = build_image(WEATHER, PEOPLE, get_quote())
    img.save(config.OUTPUT_FILE)
    print(f"\n✓ Saved {config.OUTPUT_FILE} (fixture data — no network)\n")


if __name__ == "__main__":
    main()
