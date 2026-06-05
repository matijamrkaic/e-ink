"""
fonts.py
========
Shared font loading for every panel. Tries a few system fonts and falls back to
PIL's built-in default so the script never hard-fails on a machine without the
expected TTFs (e.g. the GitHub Actions runner uses DejaVu).
"""

import os

from PIL import ImageFont

FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/System/Library/Fonts/Arial.ttf",  # macOS alt
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux / CI
]

# Named sizes. Add or retune freely — panels reference these by name, so a
# size change here ripples everywhere consistently.
SIZES = {
    "tiny": 16,
    "small": 22,
    "medium": 30,
    "large": 44,
    "huge": 88,
}


def load_fonts():
    """Return a dict of {name: ImageFont} at the sizes defined in SIZES."""
    found_path = next((p for p in FONT_PATHS if os.path.exists(p)), None)
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

    return {name: make_font(size) for name, size in SIZES.items()}
