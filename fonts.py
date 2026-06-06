"""
fonts.py
========
Shared font loading. Uses the JetBrains Mono TTFs vendored in assets/fonts/ so
rendering is identical locally and on CI — no dependency on host-installed fonts.
JetBrains Mono is OFL-licensed, so it's safe to commit to a public repo.

load_fonts() returns a Fonts object:
    fonts["small"]            → Regular weight at the named 'small' size
    fonts("large", "bold")    → Bold at the 'large' size
    fonts("small", "book-italic")  → italic
Sizes are a named key from SIZES, or a raw pixel int.
"""

import os

from PIL import ImageFont

FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

# Weight/style name → JetBrains Mono file. "book" = Regular (kept as the weight
# name so existing call sites and the fonts["size"] default don't change).
WEIGHT_FILES = {
    "light": "JetBrainsMono-Light.ttf",
    "book": "JetBrainsMono-Regular.ttf",
    "medium": "JetBrainsMono-Medium.ttf",
    "bold": "JetBrainsMono-Bold.ttf",
    "light-italic": "JetBrainsMono-LightItalic.ttf",
    "book-italic": "JetBrainsMono-Italic.ttf",
    "medium-italic": "JetBrainsMono-MediumItalic.ttf",
    "bold-italic": "JetBrainsMono-BoldItalic.ttf",
}
DEFAULT_WEIGHT = "book"

# Named sizes. Add or retune freely — panels reference these by name.
SIZES = {
    "tiny": 14,
    "small": 20,
    "medium": 28,
    "large": 40,
    "huge": 80,
}


class Fonts:
    """Lazily loads + caches JetBrains Mono at any (size, weight)."""

    def __init__(self):
        self._cache = {}

    def __call__(self, size, weight=DEFAULT_WEIGHT):
        px = SIZES[size] if isinstance(size, str) else int(size)
        key = (px, weight)
        if key not in self._cache:
            filename = WEIGHT_FILES.get(weight, WEIGHT_FILES[DEFAULT_WEIGHT])
            self._cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, filename), px)
        return self._cache[key]

    def __getitem__(self, size):
        return self(size)


def load_fonts():
    print(f"  ✓ Using JetBrains Mono from {FONT_DIR}")
    return Fonts()
