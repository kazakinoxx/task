"""Inline rich text -- thin, the parser is unit tested; the rendering
needs a real window and is verified manually.

A single PsychoPy TextStim carries one style, so to color/bold/resize
individual words we parse the i18n HTML the web app already ships into
styled "runs" and lay them out as several TextStims, wrapping to fit.

Handled: `<span class='hold-key'|'hold-finger'>` -> bold blue,
`'tap-key'|'tap-finger'>` -> bold red; `<b>` -> bold; `<b>`/`<span>` with
`style='color:X'` -> that color; `<h1>`..`<h4>` -> larger + bold;
`<br>` -> line break; `</p>` and headers -> a blank line of spacing;
`<li>` -> its own line; HTML entities are unescaped. Other tags are
stripped. Not a general CSS engine (alignment, list markers, indentation
are not reproduced). Colors live in frontend/style_constants.py.
"""

from __future__ import annotations

import html as _html
import re
from typing import List, Optional, Tuple

from frontend.style_constants import DEFAULT_FONT, HOLD_KEY_COLOR, TAP_KEY_COLOR, TEXT_COLOR, TEXT_HEIGHT

# (text, color-or-None-for-base, bold, size-scale)
Run = Tuple[str, Optional[str], bool, float]

_TOKEN = re.compile(r'<[^>]+>|[^<]+')
_TAGNAME = re.compile(r'</?\s*([a-zA-Z0-9]+)')
_CLASS = re.compile(r"""class\s*=\s*['"]([^'"]*)['"]""")
_STYLE = re.compile(r"""style\s*=\s*['"]([^'"]*)['"]""")
_COLOR_IN_STYLE = re.compile(r'color\s*:\s*([#\w]+)')

# CSS h1..h4 sizes (2.5/2/1.75/1.5rem) relative to the 1.25rem body base.
_HEADER_SCALES = {'h1': 2.0, 'h2': 1.6, 'h3': 1.4, 'h4': 1.2}
# tags that break a line when they close
_LINE_CLOSE = {'br', 'li'}
# block tags that add a blank line of spacing when they close
_PARAGRAPH_CLOSE = {'p', 'div', 'ol', 'ul'}
_KEY_COLORS = (HOLD_KEY_COLOR, TAP_KEY_COLOR)


def _style_color(tag: str) -> Optional[str]:
    style = _STYLE.search(tag)
    if not style:
        return None
    match = _COLOR_IN_STYLE.search(style.group(1))
    return match.group(1) if match else None


def parse_rich_runs(markup: str) -> List[List[Run]]:
    """Parses `markup` into lines of styled runs (see module docstring for
    the supported tags). An empty inner list represents a blank spacer
    line; consecutive blanks are collapsed and leading/trailing ones
    dropped."""
    lines: List[List[Run]] = [[]]
    colors: List[Optional[str]] = []       # span / styled-tag color stack
    color_pushed: List[bool] = []          # per <b>: did it push a color?
    bold_depth = 0
    header_scales: List[float] = []

    def newline() -> None:
        lines.append([])

    for tok in _TOKEN.findall(markup):
        if tok.startswith('<'):
            m = _TAGNAME.match(tok)
            if not m:
                continue
            name = m.group(1).lower()
            closing = tok[:2] == '</'

            if name == 'br':
                newline()
            elif name in _HEADER_SCALES:
                if closing:
                    if header_scales:
                        header_scales.pop()
                    newline()
                    newline()  # blank line after a header
                else:
                    if lines[-1]:
                        newline()
                    header_scales.append(_HEADER_SCALES[name])
            elif name == 'p':
                if closing:
                    newline()
                    newline()  # blank line between paragraphs
                elif lines[-1]:
                    newline()
            elif name == 'li':
                if closing:
                    newline()
                elif lines[-1]:
                    newline()
            elif name in _PARAGRAPH_CLOSE and closing:
                newline()
            elif name == 'b':
                if closing:
                    bold_depth = max(0, bold_depth - 1)
                    if color_pushed and color_pushed.pop():
                        colors.pop()
                else:
                    bold_depth += 1
                    col = _style_color(tok)
                    color_pushed.append(bool(col))
                    if col:
                        colors.append(col)
            elif name == 'span':
                if closing:
                    if colors:
                        colors.pop()
                else:
                    css = _CLASS.search(tok)
                    css_val = css.group(1) if css else ''
                    if 'hold-key' in css_val or 'hold-finger' in css_val:
                        colors.append(HOLD_KEY_COLOR)
                    elif 'tap-key' in css_val or 'tap-finger' in css_val:
                        colors.append(TAP_KEY_COLOR)
                    else:
                        colors.append(_style_color(tok))
            # any other tag is stripped
        else:
            text = _html.unescape(tok)
            if not text:
                continue
            color = colors[-1] if colors else None
            scale = header_scales[-1] if header_scales else 1.0
            bold = bold_depth > 0 or bool(header_scales) or color in _KEY_COLORS
            for i, part in enumerate(text.split('\n')):  # literal newlines break lines too
                if i > 0:
                    newline()
                if part:
                    lines[-1].append((part, color, bold, scale))

    # collapse consecutive blank lines to one; drop leading/trailing blanks
    result: List[List[Run]] = []
    prev_blank = False
    for line in lines:
        if line:
            result.append(line)
            prev_blank = False
        elif result and not prev_blank:
            result.append([])
            prev_blank = True
    while result and not result[-1]:
        result.pop()
    return result


class RichText:
    """Parses `markup` once and draws it as colored/bold/sized runs.
    Rebuild only when the markup string changes. `pos`/`height`/
    `wrap_width` are in the window's norm units; laid out internally in
    pixels. With `wrap_width`, words wrap greedily to the next line."""

    def __init__(self, win, markup: str, height: float = TEXT_HEIGHT, color: str = TEXT_COLOR,
                 font: str = DEFAULT_FONT, pos: Tuple[float, float] = (0, 0),
                 wrap_width: Optional[float] = None, align: str = 'center'):
        """`align`: 'center' (default -- short prompts sit centered on
        their anchor) or 'left' (paragraphs read left-to-right from a
        fixed left edge, like normal HTML body text; requires
        `wrap_width` to know where that edge is, matching the CSS
        `.instruction-text { text-align: left }` reference layout)."""
        from psychopy import visual

        half_w = win.size[0] / 2
        half_h = win.size[1] / 2
        base_h = height * half_h
        space_w = base_h * 0.28
        max_width_pix = wrap_width * half_w if wrap_width else None

        def build_word(word: str, run_color: Optional[str], bold: bool, word_h: float):
            stim = visual.TextStim(
                win, text=word, units='pix', height=word_h, color=run_color or color,
                bold=bold, font=font, anchorHoriz='center', anchorVert='center', alignText='center',
            )
            width = 0.0
            try:
                box = stim.boundingBox
                if box is not None:
                    width = float(box[0])
            except Exception:
                width = 0.0
            if width <= 0:
                width = len(word) * word_h * 0.5  # fallback if boundingBox is unavailable
            return stim, width

        # visual_lines: (list of (stim, width), line_height_pix)
        visual_lines: List[Tuple[list, float]] = []
        for runs in parse_rich_runs(markup):
            if not runs:  # blank spacer line
                visual_lines.append(([], base_h * 0.6))
                continue
            words = [(w, c, b, base_h * s) for text, c, b, s in runs for w in text.split()]
            current: list = []
            current_w = 0.0
            for word, run_color, bold, word_h in words:
                stim, width = build_word(word, run_color, bold, word_h)
                extra = width + (space_w if current else 0)
                if max_width_pix and current and current_w + extra > max_width_pix:
                    visual_lines.append((current, max(h for _, _, h in current)))
                    current, current_w = [(stim, width, word_h)], width
                else:
                    current.append((stim, width, word_h))
                    current_w += extra
            if current:
                visual_lines.append((current, max(h for _, _, h in current)))

        left_edge_pix = pos[0] * half_w - (max_width_pix / 2 if max_width_pix else 0)

        slot_heights = [lh * 1.5 for _, lh in visual_lines]
        y = pos[1] * half_h + sum(slot_heights) / 2
        self._stims = []
        for (line, _), slot in zip(visual_lines, slot_heights):
            center_y = y - slot / 2
            total_w = sum(w for _, w, _ in line) + space_w * max(0, len(line) - 1)
            x = left_edge_pix if align == 'left' else pos[0] * half_w - total_w / 2
            for stim, width, _ in line:
                stim.pos = (x + width / 2, center_y)
                x += width + space_w
                self._stims.append(stim)
            y -= slot

    def draw(self) -> None:
        for stim in self._stims:
            stim.draw()
