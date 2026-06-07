"""
dashboard.py
============
Entry point. Fetches every source, composes them onto one 800x480 e-ink image,
and saves it. Layout lives in config.LAYOUT — this file just hands each panel
its box and data. Set config.DEBUG_BOXES = True to overlay the region grid.

Run:
  python dashboard.py
"""

from datetime import datetime

from PIL import Image, ImageDraw

import config
from fonts import load_fonts
from panels.header import draw_header
from panels.health import draw_health
from panels.quote import draw_quote
from sources import garmin, quote, weather


def _debug_boxes(draw, fonts):
    """Outline + label every region so the layout is easy to eyeball."""
    for name, (x0, y0, x1, y1) in config.LAYOUT.items():
        draw.rectangle([(x0, y0), (x1 - 1, y1 - 1)], outline=128, width=1)
        draw.text((x0 + 3, y0 + 3), name, font=fonts["tiny"], fill=128)


def build_image(weather_data, people, quote_text):
    """Compose all panels onto a fresh canvas and return the image."""
    print("→ Drawing image...")
    fonts = load_fonts()

    img = Image.new("L", (config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT), color=255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    now_str = now.strftime("%H:%M")
    weather_data = {
        **weather_data,
        "weekday": now.strftime("%A").upper(),
        "date_fmt": now.strftime("%d / %m / %Y"),
    }

    draw_header(draw, config.LAYOUT["header"], weather_data, fonts, now_str)
    draw_health(draw, config.LAYOUT["health"], people, fonts)
    draw_quote(draw, config.LAYOUT["quote"], quote_text, fonts)

    if config.DEBUG_BOXES:
        _debug_boxes(draw, fonts)

    print("  ✓ Image drawn")
    return img


def main():
    print("\n╔══════════════════════════════════╗")
    print("║   E-Ink Family Dashboard         ║")
    print("╚══════════════════════════════════╝\n")

    weather_data = weather.get_weather()
    people = garmin.get_all()
    quote_text = quote.get_quote()

    print()
    img = build_image(weather_data, people, quote_text)
    img.save(config.OUTPUT_FILE)
    print(f"\n✓ Saved {config.OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()
