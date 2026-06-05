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
from datetime import date

from garminconnect import Garmin, GarminConnectAuthenticationError

# Common locations Garmin stashes the 0-100 sleep score, newest API first.
_SLEEP_SCORE_PATHS = [
    ("dailySleepDTO", "sleepScores", "overall", "value"),
    ("dailySleepDTO", "overallSleepScore"),
]


def _safe(d, *keys, default=None):
    """Dive into nested dicts without KeyError/TypeError."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur or cur[k] is None:
            return default
        cur = cur[k]
    return cur


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

    # On local runs, print the token blob so it can be pasted into the CI secret.
    if not tokens:
        print(f"\n── {person['name']} {person['tokens_env']} (store as a GitHub secret) ──")
        print(api.client.dumps())
        print("─" * 60)
    return api


def get_person(person):
    """Fetch resting HR + sleep score for one person."""
    print(f"→ Fetching Garmin for {person['name']}...")
    api = _login(person)
    today = date.today().isoformat()

    stats = api.get_stats(today) or {}
    sleep = api.get_sleep_data(today) or {}

    sleep_score = None
    for path in _SLEEP_SCORE_PATHS:
        sleep_score = _safe(sleep, *path)
        if sleep_score is not None:
            break

    print(f"  ✓ {person['name']}: HR={stats.get('restingHeartRate')} sleep={sleep_score}")
    return {
        "name": person["name"],
        "resting_hr": stats.get("restingHeartRate"),
        "sleep_score": sleep_score,
    }


def get_all():
    """Fetch every person in config.PEOPLE."""
    import config

    return [get_person(p) for p in config.PEOPLE]
