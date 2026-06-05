"""
sources/weather.py
===================
Fetch + parse weather from Open-Meteo (free, no API key). Returns a clean dict:

    {
      "today":    {"icon": "sun", "high": 28, "low": 16},
      "forecast": [ {"day": "Tue", "icon": "cloud", "high": 27, "low": 15}, ... ],
    }

WMO weather codes are bucketed into just three icon kinds (sun / cloud / rain)
to match the simplified header design.
"""

from datetime import datetime

import requests

import config


def _code_to_icon(code):
    """Bucket a WMO weather code into 'sun' | 'cloud' | 'rain'."""
    if code in (0, 1):
        return "sun"
    # 51+ covers drizzle, rain, snow, showers, thunderstorm — all "wet".
    if code >= 51:
        return "rain"
    return "cloud"  # 2, 3, 45, 48 (cloudy / fog)


def fetch_weather():
    """Call Open-Meteo and return the raw response dict."""
    print("→ Fetching weather (Open-Meteo)...")
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "timezone": config.TIMEZONE,
        "forecast_days": config.FORECAST_DAYS,
        "daily": ["temperature_2m_max", "temperature_2m_min", "weathercode"],
    }
    resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    resp.raise_for_status()
    print("  ✓ Got weather")
    return resp.json()


def parse_weather(data):
    """Extract today + the next FORECAST_DAYS-1 days into the clean dict."""
    daily = data["daily"]

    def day(i):
        return {
            "day": datetime.strptime(daily["time"][i], "%Y-%m-%d").strftime("%a"),
            "icon": _code_to_icon(daily["weathercode"][i]),
            "high": round(daily["temperature_2m_max"][i]),
            "low": round(daily["temperature_2m_min"][i]),
        }

    n = len(daily["time"])
    return {
        "today": day(0),
        "forecast": [day(i) for i in range(1, n)],
    }


def get_weather():
    """Convenience: fetch + parse in one call."""
    return parse_weather(fetch_weather())
