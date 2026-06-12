"""
sources/garmin.py
=================
Per-person Garmin Connect fetch + parse. Parameterized by a person dict from
config.PEOPLE so the same code serves husband and wife. Returns:

    {"name": "Matija", "resting_hr": 52, "sleep_score": 84}

Either value may be None (rendered as "—" by the panel) when Garmin has no data
yet for today — e.g. before sleep has synced.

Auth mirrors garminconnect's own login(tokenstore), which self-heals across:
  • a serialized token string in the *_TOKENS env var (CI, headless)
  • a cached token path on disk (local repeat runs)
  • a fresh email+password login (first local run), persisted to the path
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from garminconnect import Garmin, GarminConnectAuthenticationError

# Window for the activity grid + type counts: 5 rows (4 complete past weeks +
# current partial week). Fetch 35 days back to always cover the oldest row.
ACTIVITY_DAYS = 35
# Window for the daily-steps bar chart.
STEPS_DAYS = 7

# Garmin shuffles where it nests values (VO2 max, body battery, …) between API
# versions, so we search responses by key rather than hard-coding a single path.

# Garmin's activityType.typeKey → short, grouped label for the counts list.
_ACTIVITY_LABELS = {
    "running": "Run", "treadmill_running": "Run", "trail_running": "Run", "track_running": "Run",
    "cycling": "Bike", "road_biking": "Bike", "mountain_biking": "Bike",
    "indoor_cycling": "Bike", "virtual_ride": "Bike",
    "strength_training": "Gym", "indoor_cardio": "Gym", "fitness_equipment": "Gym", "elliptical": "Gym",
    "boxing": "Boxing", "mixed_martial_art": "Boxing",
    "swimming": "Swim", "lap_swimming": "Swim", "open_water_swimming": "Swim",
    "walking": "Walk", "casual_walking": "Walk", "speed_walking": "Walk",
    "hiking": "Hike", "yoga": "Yoga", "pilates": "Pilates",
}


def _activity_label(type_key):
    """Map a Garmin typeKey to a short label, title-casing anything unmapped."""
    if not type_key:
        return "Other"
    return _ACTIVITY_LABELS.get(type_key, type_key.replace("_", " ").title())


def _deep_find(obj, key):
    """First value for `key` anywhere in a nested dict/list, else None."""
    if isinstance(obj, dict):
        if key in obj and obj[key] is not None:
            return obj[key]
        for v in obj.values():
            found = _deep_find(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _deep_find(v, key)
            if found is not None:
                return found
    return None




def _login(person):
    """Log a single person in, re-using cached tokens when possible."""
    email = os.environ.get(person["email_env"])
    password = os.environ.get(person["password_env"])
    tokens = os.environ.get(person["tokens_env"])
    store = person["token_store"]

    if not tokens and not os.path.exists(store) and not (email and password):
        raise SystemExit(
            f"✗ {person['name']}: missing credentials. Set {person['tokens_env']} "
            f"(CI) or {person['email_env']} + {person['password_env']}."
        )

    api = Garmin(email=email, password=password)
    try:
        api.login(tokens or store)  # string blob or path; login() handles both
    except (GarminConnectAuthenticationError, FileNotFoundError) as err:
        raise SystemExit(f"✗ {person['name']}: Garmin auth failed: {err}")

    # Verify we're authenticated as the expected person; catches mismatched CI secrets.
    try:
        logged_in_as = api.get_full_name()
    except Exception:
        logged_in_as = "unknown"
    print(f"  ✓ Logged in as: {logged_in_as} (expected: {person['name']})")

    # On local runs, print the token blob so it can be pasted into the CI secret.
    if not tokens:
        print(f"\n── {person['name']} {person['tokens_env']} (store as a GitHub secret) ──")
        print(api.client.dumps())
        print("─" * 60)
    return api


def _activities(api, today):
    """Logged activities in the last ACTIVITY_DAYS as [{date, type}]."""
    start = (today - timedelta(days=ACTIVITY_DAYS - 1)).isoformat()
    raw = api.get_activities_by_date(start, today.isoformat()) or []
    out = []
    for a in raw:
        ts = a.get("startTimeLocal") or ""
        if len(ts) < 10:
            continue
        try:
            day = datetime.strptime(ts[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        type_key = (a.get("activityType") or {}).get("typeKey")
        duration = int(a.get("duration") or 0)
        out.append({"date": day, "type": _activity_label(type_key), "duration": duration})
    return out


def _steps_week(api, today):
    """Daily steps for the last STEPS_DAYS as [{date, steps}], oldest→newest."""
    start = today - timedelta(days=STEPS_DAYS - 1)
    raw = api.get_daily_steps(start.isoformat(), today.isoformat()) or []
    by_date = {}
    for entry in raw:
        day_str = entry.get("calendarDate")
        if day_str:
            by_date[datetime.strptime(day_str, "%Y-%m-%d").date()] = int(entry.get("totalSteps") or 0)
    return [
        {"date": start + timedelta(days=i), "steps": by_date.get(start + timedelta(days=i), 0)}
        for i in range(STEPS_DAYS)
    ]


def _week_stats(api, today):
    """
    One pass over the last 7 days. Returns:
      resting_hr     — most recent day's resting HR
      bb_overnight   — most recent night's Body Battery change (overnight recharge)
      intensity_7d   — Σ moderate + 2×vigorous intensity minutes
      avg_sleep_7d   — mean sleep seconds over days that have data (or None)
      avg_kcal_7d    — mean daily total calories over days that have data (or None)
    Walking newest→oldest and keeping the first value found makes "current" tolerant
    of today not having synced yet.
    """
    resting_hr = bb_overnight = None
    intensity_7d = 0
    sleep_seconds = []
    kcals = []
    for i in range(7):
        iso = (today - timedelta(days=i)).isoformat()
        st = api.get_stats(iso) or {}
        sl = api.get_sleep_data(iso) or {}
        if resting_hr is None:
            resting_hr = st.get("restingHeartRate")
        if bb_overnight is None:
            bb = _deep_find(sl, "bodyBatteryChange")
            if isinstance(bb, (int, float)):
                bb_overnight = round(bb)
        intensity_7d += (st.get("moderateIntensityMinutes") or 0) + (
            st.get("vigorousIntensityMinutes") or 0
        ) * 2
        secs = _deep_find(sl, "sleepTimeSeconds") or 0
        if secs:
            sleep_seconds.append(secs)
        kcal = st.get("totalKilocalories")
        if kcal:
            kcals.append(kcal)
    avg_sleep_7d = sum(sleep_seconds) / len(sleep_seconds) if sleep_seconds else None
    avg_kcal_7d = sum(kcals) / len(kcals) if kcals else None
    return resting_hr, bb_overnight, intensity_7d, avg_sleep_7d, avg_kcal_7d


def get_person(person):
    """Fetch the health metrics, 5-week activities, and 7-day steps for a person."""
    print(f"→ Fetching Garmin for {person['name']}...")
    api = _login(person)
    today = date.today()

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_week = ex.submit(_week_stats, api, today)
        f_acts = ex.submit(_activities, api, today)
        f_steps = ex.submit(_steps_week, api, today)
    resting_hr, bb_overnight, intensity_7d, avg_sleep_7d, avg_kcal_7d = f_week.result()
    activities = f_acts.result()
    steps_7d = f_steps.result()

    print(
        f"  ✓ {person['name']}: HR={resting_hr} bb_overnight={bb_overnight} "
        f"kcal7d={avg_kcal_7d} int7d={intensity_7d} activities={len(activities)}"
    )
    return {
        "name": person["name"],
        "resting_hr": resting_hr,
        "bb_overnight": bb_overnight,
        "avg_kcal_7d": avg_kcal_7d,
        "intensity_7d": intensity_7d,
        "avg_sleep_7d": avg_sleep_7d,
        "activities": activities,
        "steps_7d": steps_7d,
    }


def get_all():
    """Fetch every person in config.PEOPLE."""
    import config

    return [get_person(p) for p in config.PEOPLE]
