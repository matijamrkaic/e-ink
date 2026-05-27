"""
weather.py
==================
A weather dashboard that generates an 800x480 image — the exact size of a
7.5" Waveshare e-ink display. On your MacBook it saves a PNG and opens it.
Later, you'll swap the last section to push pixels to the real screen.

Learning goals in this file:
  1. Making HTTP requests to a free API
  2. Parsing JSON data
  3. Drawing text and shapes with Pillow (PIL)
  4. Organising code into functions
  5. Understanding the image format the e-ink needs

Requirements (install once):
  pip install requests Pillow

Run:
  python weather.py
"""

# ── Imports ──────────────────────────────────────────────────────────────────
import json  # Parsing JSON responses
import os
import subprocess  # Opening the image on Mac
import sys
from datetime import datetime  # Formatting dates

import requests  # HTTP requests (fetching weather data)
from PIL import Image, ImageDraw, ImageFont  # Drawing the image

# ── Configuration ─────────────────────────────────────────────────────────────
# Change these to your location. Belgrade coordinates are the default.
# Find yours at: https://www.latlong.net/
LATITUDE = 44.8125
LONGITUDE = 20.4612
CITY_NAME = "Belgrade"
TIMEZONE = "Europe/Belgrade"

# E-ink display resolution. Don't change this — it matches the 7.5" Waveshare.
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# Output file
OUTPUT_FILE = "weather_preview.png"


# ── Weather code → human label ────────────────────────────────────────────────
# Open-Meteo returns a numeric "weather code" (WMO standard).
# This dictionary translates the most common ones to readable text.
WEATHER_LABELS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy showers",
    85: "Snow showers",
    95: "Thunderstorm",
    99: "Heavy thunderstorm",
}

# Simple ASCII-art-style weather symbols drawn with PIL lines/arcs.
# Each returns a short Unicode symbol. On e-ink, shapes render crisply.
WEATHER_SYMBOLS = {
    0: "☀",
    1: "🌤",
    2: "⛅",
    3: "☁",
    45: "🌫",
    48: "🌫",
    51: "🌦",
    53: "🌧",
    61: "🌧",
    63: "🌧",
    65: "🌧",
    71: "❄",
    73: "❄",
    75: "❄",
    80: "🌦",
    81: "🌧",
    95: "⛈",
}


# ── Step 1: Fetch weather data ────────────────────────────────────────────────
def fetch_weather():
    """
    Calls the Open-Meteo API (completely free, no API key needed) and returns
    a dictionary with current + 4-day forecast data.

    The URL is built with parameters:
      - latitude/longitude  → your location
      - current             → what to return for right now
      - daily               → what to return per day
      - forecast_days       → how many days ahead
      - timezone            → so dates/times are local
    """
    url = "https://api.open-meteo.com/v1/forecast"

    # These are called "query parameters" — they go after ? in the URL.
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "forecast_days": 4,
        # Current conditions
        "current": [
            "temperature_2m",  # Temperature in °C at 2m height
            "apparent_temperature",  # "Feels like"
            "weathercode",  # WMO code (see WEATHER_LABELS above)
            "windspeed_10m",  # Wind speed km/h
            "relative_humidity_2m",  # Humidity %
        ],
        # Daily forecast (one value per day)
        "daily": [
            "temperature_2m_max",  # High for the day
            "temperature_2m_min",  # Low for the day
            "weathercode",  # Dominant weather code for the day
            "precipitation_sum",  # Total rain mm
        ],
    }

    print("→ Fetching weather data from Open-Meteo...")

    # requests.get() sends an HTTP GET request. params= adds ?key=value to URL.
    response = requests.get(url, params=params, timeout=10)

    # Raise an error if HTTP status is not 200 OK (e.g. 404, 500)
    response.raise_for_status()

    # .json() parses the response text into a Python dictionary
    data = response.json()

    print(f"  ✓ Got data for {CITY_NAME}")
    print(f"  ✓ Current temp: {data['current']['temperature_2m']}°C")

    return data


# ── Step 2: Parse into clean variables ────────────────────────────────────────
def parse_weather(data):
    """
    Takes the raw API response dictionary and extracts just what we need.
    Returns a clean dict that the drawing function will use.
    """
    current = data["current"]
    daily = data["daily"]

    # Format today's date nicely
    now = datetime.now()
    date_str = now.strftime("%A, %d %B %Y")  # e.g. "Saturday, 23 May 2026"
    time_str = now.strftime("%H:%M")  # e.g. "14:30"

    # Build a list of forecast days (skip index 0 = today for the side panel)
    forecast = []
    for i in range(1, 4):  # Days 1, 2, 3 (tomorrow + 2 more)
        day_date = datetime.strptime(daily["time"][i], "%Y-%m-%d")
        forecast.append(
            {
                "day": day_date.strftime("%a"),  # "Mon", "Tue", etc.
                "code": daily["weathercode"][i],
                "high": round(daily["temperature_2m_max"][i]),
                "low": round(daily["temperature_2m_min"][i]),
                "rain": daily["precipitation_sum"][i],
            }
        )

    return {
        "city": CITY_NAME,
        "date": date_str,
        "time": time_str,
        "temp": round(current["temperature_2m"]),
        "feels_like": round(current["apparent_temperature"]),
        "condition": WEATHER_LABELS.get(current["weathercode"], "Unknown"),
        "code": current["weathercode"],
        "wind": round(current["windspeed_10m"]),
        "humidity": current["relative_humidity_2m"],
        "today_high": round(daily["temperature_2m_max"][0]),
        "today_low": round(daily["temperature_2m_min"][0]),
        "today_rain": daily["precipitation_sum"][0],
        "forecast": forecast,
    }


# ── Step 3: Load fonts ────────────────────────────────────────────────────────
def load_fonts():
    """
    Tries to load system fonts. Falls back to PIL's default if none found.
    On macOS, these paths are standard. On the ESP32 we'll embed a font file.

    Returns a dict of font objects at different sizes.
    """
    # List of fonts to try, in order of preference
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/System/Library/Fonts/Arial.ttf",  # macOS alt
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    ]

    found_path = None
    for path in font_paths:
        if os.path.exists(path):
            found_path = path
            print(f"  ✓ Using font: {path}")
            break

    if not found_path:
        print("  ⚠ No TTF font found, using PIL default (less pretty)")

    def make_font(size):
        """Helper: load font at a given size, or fall back to default."""
        if found_path:
            try:
                return ImageFont.truetype(found_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    return {
        "tiny": make_font(16),
        "small": make_font(22),
        "medium": make_font(32),
        "large": make_font(52),
        "huge": make_font(110),
    }


# ── Step 4: Draw the image ────────────────────────────────────────────────────
def draw_image(weather):
    """
    Creates an 800x480 black-and-white image that matches the e-ink display.
    Uses Pillow's ImageDraw to place text, lines, and rectangles.

    Layout:
    ┌─────────────────────────────┬─────────────────┐
    │  City + Date (header)       │                 │
    ├──────────────┬──────────────│  3-day forecast │
    │  Big temp    │  Details     │  (right panel)  │
    │              │  (wind, hum) │                 │
    │  Condition   │  High / Low  │                 │
    └──────────────┴──────────────┴─────────────────┘
    """
    print("→ Drawing image...")

    fonts = load_fonts()

    # Create a white (255) image. Mode "L" = 8-bit grayscale.
    # The real e-ink driver will convert this to 1-bit (pure black/white).
    img = Image.new("L", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=255)
    draw = ImageDraw.Draw(img)

    BLACK = 0
    WHITE = 255
    GRAY = 180  # For secondary text; e-ink will render as dithered pattern

    # ── Layout constants ──────────────────────────────────────────────────────
    HEADER_H = 70  # Height of the top header bar
    LEFT_W = 530  # Width of the left weather panel
    RIGHT_X = LEFT_W + 1  # Where the right forecast panel starts
    DIVIDER_X = 300  # Vertical divider inside the left panel

    # ── Header bar ────────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (DISPLAY_WIDTH, HEADER_H)], fill=BLACK)

    # City name (left of header)
    draw.text((20, 12), weather["city"].upper(), font=fonts["large"], fill=WHITE)

    # Date and time (right of header, smaller)
    draw.text(
        (LEFT_W - 10, 10),
        weather["date"],
        font=fonts["small"],
        fill=WHITE,
        anchor="ra",  # anchor="ra" means right-aligned, top
    )
    draw.text(
        (LEFT_W - 10, 40),
        f"Updated {weather['time']}",
        font=fonts["tiny"],
        fill=GRAY,
        anchor="ra",
    )

    # ── Left panel: current temperature ───────────────────────────────────────
    # Giant temperature number
    temp_str = f"{weather['temp']}°"
    draw.text((30, 90), temp_str, font=fonts["huge"], fill=BLACK)

    # Weather condition below temp
    draw.text(
        (30, HEADER_H + 170),
        weather["condition"],
        font=fonts["medium"],
        fill=BLACK,
    )

    # Feels like
    draw.text(
        (30, HEADER_H + 215),
        f"Feels like {weather['feels_like']}°C",
        font=fonts["small"],
        fill=GRAY,
    )

    # ── Left panel: details (right half of left panel) ────────────────────────
    # Vertical divider line
    draw.line(
        [(DIVIDER_X, HEADER_H + 20), (DIVIDER_X, DISPLAY_HEIGHT - 20)],
        fill=GRAY,
        width=1,
    )

    details_x = DIVIDER_X + 20
    details_y = HEADER_H + 30

    def detail_row(label, value, y_offset):
        """Draw a label + value pair at a given vertical offset."""
        draw.text(
            (details_x, details_y + y_offset),
            label,
            font=fonts["tiny"],
            fill=GRAY,
        )
        draw.text(
            (details_x, details_y + y_offset + 18),
            value,
            font=fonts["medium"],
            fill=BLACK,
        )

    detail_row("HIGH / LOW", f"{weather['today_high']}° / {weather['today_low']}°", 0)
    detail_row("WIND", f"{weather['wind']} km/h", 90)
    detail_row("HUMIDITY", f"{weather['humidity']}%", 180)
    detail_row("RAIN TODAY", f"{weather['today_rain']} mm", 270)

    # ── Right panel: 3-day forecast ───────────────────────────────────────────
    # Vertical divider between left and right panels
    draw.line(
        [(RIGHT_X, HEADER_H), (RIGHT_X, DISPLAY_HEIGHT)],
        fill=BLACK,
        width=2,
    )

    # Each forecast day gets an equal slice of the right panel height
    right_panel_w = DISPLAY_WIDTH - RIGHT_X
    day_h = (DISPLAY_HEIGHT - HEADER_H) // 3

    for i, day in enumerate(weather["forecast"]):
        y_top = HEADER_H + i * day_h
        y_bottom = y_top + day_h
        y_center = y_top + day_h // 2

        # Alternating light background for readability
        if i % 2 == 0:
            draw.rectangle(
                [(RIGHT_X, y_top), (DISPLAY_WIDTH, y_bottom)],
                fill=245,
            )

        # Horizontal divider between days
        if i > 0:
            draw.line(
                [(RIGHT_X, y_top), (DISPLAY_WIDTH, y_top)],
                fill=GRAY,
                width=1,
            )

        # Day name
        draw.text(
            (RIGHT_X + 15, y_center - 28),
            day["day"].upper(),
            font=fonts["small"],
            fill=BLACK,
        )

        # Condition label
        condition_short = WEATHER_LABELS.get(day["code"], "?")
        # Truncate if too long for the panel
        if len(condition_short) > 12:
            condition_short = condition_short[:11] + "…"
        draw.text(
            (RIGHT_X + 15, y_center + 2),
            condition_short,
            font=fonts["tiny"],
            fill=GRAY,
        )

        # High / Low on the right side
        draw.text(
            (DISPLAY_WIDTH - 15, y_center - 20),
            f"{day['high']}°",
            font=fonts["medium"],
            fill=BLACK,
            anchor="ra",
        )
        draw.text(
            (DISPLAY_WIDTH - 15, y_center + 12),
            f"{day['low']}°",
            font=fonts["small"],
            fill=GRAY,
            anchor="ra",
        )

    # ── Bottom border line ────────────────────────────────────────────────────
    draw.rectangle(
        [(0, DISPLAY_HEIGHT - 6), (LEFT_W, DISPLAY_HEIGHT)],
        fill=BLACK,
    )

    print("  ✓ Image drawn")
    return img


# ── Step 5: Save and open ─────────────────────────────────────────────────────
def save_and_preview(img):
    """
    Saves the image as a PNG and opens it on macOS using the 'open' command.
    On the ESP32 this function will be replaced by the e-ink push code.
    """
    img.save(OUTPUT_FILE)
    print(f"  ✓ Saved to {OUTPUT_FILE}")

    # macOS: 'open' launches the default viewer (Preview)
    if sys.platform == "darwin":
        subprocess.run(["open", OUTPUT_FILE])
        print("  ✓ Opened in Preview")
    else:
        print(f"  → Open {OUTPUT_FILE} manually to view it")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    """
    Entry point. Runs steps 1–5 in sequence.
    This is the function that will become the main loop on the ESP32.
    """
    print("\n╔══════════════════════════════════╗")
    print("║   E-Ink Weather Dashboard        ║")
    print("╚══════════════════════════════════╝\n")

    # Step 1 + 2: Fetch and parse
    raw_data = fetch_weather()
    weather = parse_weather(raw_data)

    # Print what we got (good for learning/debugging)
    print("\n→ Parsed weather:")
    print(json.dumps(weather, indent=2, default=str))

    # Step 3 + 4: Draw
    print()
    img = draw_image(weather)

    # Step 5: Show on Mac (will become "push to e-ink" later)
    print()
    save_and_preview(img)

    print("\n✓ Done!\n")


# ── Run ───────────────────────────────────────────────────────────────────────
# This block only runs when you execute the file directly:
#   python weather_display.py
# It does NOT run when another file imports this one.
if __name__ == "__main__":
    main()
