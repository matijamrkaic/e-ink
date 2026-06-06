"""
panels/quote.py
===============
Full-width quote strip along the bottom: small white text on a dark background.
Renders a multi-line quote (a couplet or short stanza) centered in its box,
honoring the quote's own line breaks and word-wrapping any over-long line. Picks
the largest font (small, then tiny) that fits the strip's height.
"""

from colors import BLACK, WHITE


def _wrap_line(draw, line, font, max_w):
    """Greedy word-wrap one logical line to fit max_w. Returns a list of lines."""
    words = line.split()
    if not words:
        return [""]
    out, cur = [], words[0]
    for w in words[1:]:
        if draw.textlength(cur + " " + w, font=font) <= max_w:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    return out


def draw_quote(draw, box, quote, fonts):
    """quote = a (possibly multi-line) string."""
    x0, y0, x1, y1 = box
    # Dark background for the strip; text is drawn in white over it.
    draw.rectangle([(x0, y0), (x1, y1)], fill=BLACK)

    pad = 14
    max_w = (x1 - x0) - 2 * pad
    max_h = (y1 - y0) - 2 * pad
    if not quote:
        return

    # Wrap the quote in curly quotes. If the last line is an attribution
    # (e.g. "— Seneca"), keep the closing quote before it, not around it.
    raw_lines = quote.splitlines()
    attribution = None
    if len(raw_lines) > 1 and raw_lines[-1].lstrip().startswith(("—", "–", "-")):
        attribution = raw_lines.pop()
    if raw_lines:
        raw_lines[0] = "“" + raw_lines[0]
        raw_lines[-1] = raw_lines[-1] + "”"
    if attribution is not None:
        raw_lines.append(attribution)

    # Small italic text: try small, then tiny; pick the largest that fits.
    for font_name in ("small", "tiny"):
        font = fonts(font_name, "book-italic")
        wrapped = []
        for line in raw_lines:
            wrapped.extend(_wrap_line(draw, line, font, max_w))
        line_h = font.size + 6
        total_h = line_h * len(wrapped)
        if total_h <= max_h or font_name == "tiny":
            break

    # Vertically center the block.
    cy = y0 + pad + (max_h - total_h) / 2
    center_x = (x0 + x1) / 2
    for line in wrapped:
        draw.text((center_x, cy), line, font=font, fill=WHITE, anchor="ma")
        cy += line_h
