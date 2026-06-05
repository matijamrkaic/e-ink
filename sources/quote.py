"""
sources/quote.py
================
Pick one random quote from a plain-text file whose entries are separated by a
blank line. A quote may span several lines (a couplet or a short stanza); the
whole block between blank lines is one entry, returned verbatim with its line
breaks intact. The quote panel handles wrapping of over-long single lines.
"""

import os
import random

import config


def get_quote(path=None):
    """Return a random multi-line quote string, or "" if the file is empty/missing."""
    path = path or config.QUOTES_FILE
    if not os.path.exists(path):
        print(f"  ⚠ Quote file not found: {path}")
        return ""

    with open(path, encoding="utf-8") as f:
        text = f.read()

    # Split on blank lines (one or more), trim, drop empties.
    entries = [block.strip() for block in text.split("\n\n") if block.strip()]
    if not entries:
        return ""

    quote = random.choice(entries)
    print(f"  ✓ Quote ({len(quote.splitlines())} line(s))")
    return quote
