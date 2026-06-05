"""
panels/quote.py
===============
Left-hand quote block. Renders a multi-line quote (a couplet or short stanza)
centered in its square-ish box. Honors the quote's own line breaks, and also
word-wraps any single line that's too wide for the box. Shrinks the font a step
if the whole thing won't fit vertically.
"""

BLACK = 0
GRAY = 180


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
    pad = 28
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

    # Try fonts largest-first; pick the biggest that fits the box height.
    for font_name in ("medium", "small", "tiny"):
        font = fonts[font_name]
        wrapped = []
        for line in raw_lines:
            wrapped.extend(_wrap_line(draw, line, font, max_w))
        line_h = font.size + 8
        total_h = line_h * len(wrapped)
        if total_h <= max_h or font_name == "tiny":
            break

    # Vertically center the block.
    cy = y0 + pad + (max_h - total_h) / 2
    center_x = (x0 + x1) / 2
    for line in wrapped:
        draw.text((center_x, cy), line, font=font, fill=BLACK, anchor="ma")
        cy += line_h
