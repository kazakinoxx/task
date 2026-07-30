"""PsychoPy rendering for the generic message/choice/timed-break screens
-- thin, not unit tested. See src2/trials/message_trial.py for the pure
logic this drives.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from frontend.style_constants import (
    BREAK_BODY_POS,
    BREAK_TITLE_POS,
    INSTRUCTION_FONT,
    MESSAGE_IMAGE_POS,
    MESSAGE_IMAGE_SIZE,
    MESSAGE_TEXT_POS_CENTERED,
    MESSAGE_TEXT_POS_WITH_IMAGE,
    MESSAGE_WRAP_WIDTH,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TITLE_TEXT_HEIGHT,
)
from frontend.rich_text import RichText
from frontend.widgets import run_button_screen, single_button, two_button_row
from src2.trials.message_trial import resolve_break_remaining_seconds

logger = logging.getLogger(__name__)


@dataclass
class TextStyle:
    """Subset of psychopy.visual.TextStim's styling params worth
    overriding per-screen. `to_kwargs()` maps `wrap_width` to TextStim's
    `wrapWidth` -- everything else already matches TextStim's own
    keyword names, so it can be passed straight through. Defaults come
    from frontend/style_constants.py."""

    font: str = INSTRUCTION_FONT
    color: str = TEXT_COLOR
    height: float = TEXT_HEIGHT
    wrap_width: float = MESSAGE_WRAP_WIDTH
    bold: bool = False
    italic: bool = False

    def to_kwargs(self) -> dict:
        return {
            'font': self.font,
            'color': self.color,
            'height': self.height,
            'wrapWidth': self.wrap_width,
            'bold': self.bold,
            'italic': self.italic,
        }


@dataclass
class StimConfig:
    """Default styles by role. Pass an explicit `style=`/`title_style=`/
    `body_style=` to any of this module's render functions to override
    per call; omit it to fall back to these defaults."""

    text: TextStyle = field(default_factory=TextStyle)
    title: TextStyle = field(default_factory=lambda: TextStyle(height=TITLE_TEXT_HEIGHT, bold=True))
    body: TextStyle = field(default_factory=TextStyle)


CONFIG = StimConfig()


def _build_image_stim(win, image_path: Optional[Path], pos=MESSAGE_IMAGE_POS, size=MESSAGE_IMAGE_SIZE):
    """Port of the JS instruction screens' two-column (text left, image
    right) layout. Returns None if `image_path` is None or the file
    doesn't exist -- degrades gracefully instead of crashing, matching a
    browser's own behavior for a 404'd <img> (see ui/assets.py's
    docstring for the two JS asset references this covers)."""
    if image_path is None:
        return None
    from psychopy import visual

    if not Path(image_path).exists():
        logger.warning('Image not found: %s', image_path)
        return None

    try:
        return visual.ImageStim(win, image=str(image_path), pos=pos, size=size)
    except Exception:
        logger.exception('Failed to load image %s', image_path)
        return None


def _build_header_stim(
    win, header: Optional[str], header_pos, header_align: str, header_style: Optional[TextStyle],
    header_wrap_width: Optional[float] = None,
):
    if not header:
        return None
    resolved = header_style or CONFIG.title
    return RichText(
        win, header, height=resolved.height, color=resolved.color, font=resolved.font,
        pos=header_pos, wrap_width=header_wrap_width if header_wrap_width is not None else resolved.wrap_width,
        align=header_align,
    )


def run_message(
    win, keyboard_monitor, text: str, continue_key: str = 'space', image_path: Optional[Path] = None,
    style: Optional[TextStyle] = None, button_label: str = 'Continue', align: str = 'left',
    text_pos=None, image_pos=MESSAGE_IMAGE_POS, image_size=MESSAGE_IMAGE_SIZE, wrap_width: Optional[float] = None,
    header: Optional[str] = None, header_pos=(0, 0.7), header_align: str = 'center',
    header_style: Optional[TextStyle] = None, header_wrap_width: Optional[float] = None,
) -> dict:
    """Draws `text` (and an optional image beside it, and an optional
    separately-positioned `header`) plus a single clickable `button_label`
    button, and waits for the button to be clicked OR `continue_key` to be
    released -- all as ONE screen/click (calling this twice makes two
    sequential screens, not one combined layout; use `header=` instead of
    a second call if you want a header pinned above the body). Port of
    the generic HtmlButtonResponsePlugin "read this, click to continue"
    screens (sitComfortably, tutorialIntroductionTrial,
    continueMessageDirection, getEndPage, deviceConnectPages' status
    confirmation, and the various instruction screens). `text`/`header`
    may contain the i18n HTML spans -- the hold-key/tap-key words are
    colored inline (see rich_text). `style`/`header_style` override the
    default text styling (CONFIG.text/CONFIG.title); `wrap_width`/
    `header_wrap_width` (norm units) override just the wrap width without
    needing a full `style=TextStyle(...)`, defaulting to the style's own
    wrap_width (CONFIG.text.wrap_width/CONFIG.title.wrap_width) when
    omitted. `align`/`header_align`: 'left' (default, paragraphs) or
    'center' (short single-line messages). `text_pos`/`header_pos`/
    `image_pos`/`image_size` (norm units) override the default layout
    (frontend/style_constants.py's MESSAGE_TEXT_POS_*/MESSAGE_IMAGE_*) --
    `text_pos` defaults to the with-image or centered position depending
    on whether `image_path` is given."""
    resolved_style = style or CONFIG.text
    resolved_text_pos = text_pos if text_pos is not None else (
        MESSAGE_TEXT_POS_WITH_IMAGE if image_path is not None else MESSAGE_TEXT_POS_CENTERED
    )
    resolved_wrap_width = wrap_width if wrap_width is not None else resolved_style.wrap_width
    text_stim = RichText(
        win, text, height=resolved_style.height, color=resolved_style.color, font=resolved_style.font,
        pos=resolved_text_pos, wrap_width=resolved_wrap_width, align=align,
    )
    extra_stims = [text_stim]
    header_stim = _build_header_stim(win, header, header_pos, header_align, header_style, header_wrap_width)
    if header_stim is not None:
        extra_stims.append(header_stim)
    image_stim = _build_image_stim(win, image_path, pos=image_pos, size=image_size)
    if image_stim is not None:
        extra_stims.append(image_stim)

    run_button_screen(
        win, keyboard_monitor, buttons=[single_button(win, button_label)],
        key_map={continue_key.lower(): 0}, extra_stims=extra_stims,
    )
    return {}


def run_choice(
    win, keyboard_monitor, text: str, key_map: Dict[str, int], image_path: Optional[Path] = None,
    style: Optional[TextStyle] = None, button_labels: Optional[List[str]] = None, align: str = 'center',
    text_pos=None, image_pos=MESSAGE_IMAGE_POS, image_size=MESSAGE_IMAGE_SIZE, wrap_width: Optional[float] = None,
    header: Optional[str] = None, header_pos=(0, 0.7), header_align: str = 'center',
    header_style: Optional[TextStyle] = None, header_wrap_width: Optional[float] = None,
) -> dict:
    """Draws `text` (and an optional image, and an optional
    separately-positioned `header`) plus one clickable button per choice,
    and waits for a button click OR one of `key_map`'s keys to be
    released, returning `{'response': index}` -- all as ONE screen/click
    (see run_message_trial's docstring on why two calls won't combine
    into one layout). `key_map` maps key -> response index;
    `button_labels[i]` labels the button for index i (a click returns
    that index). Used for the hand-preference screen, whose two choices
    don't correspond to the tap/hold keys since preferredHand isn't known
    yet. `style`/`header_style` override the default text styling;
    `wrap_width`/`header_wrap_width` override just the wrap width, same as
    run_message_trial. `align`/`header_align`: 'left' (paragraphs) or
    'center' (default, short single-line messages). `text_pos`/
    `header_pos`/`image_pos`/`image_size` (norm units) override the
    default layout, same as run_message_trial."""
    resolved_style = style or CONFIG.text
    resolved_text_pos = text_pos if text_pos is not None else (
        MESSAGE_TEXT_POS_WITH_IMAGE if image_path is not None else MESSAGE_TEXT_POS_CENTERED
    )
    resolved_wrap_width = wrap_width if wrap_width is not None else resolved_style.wrap_width
    text_stim = RichText(
        win, text, height=resolved_style.height, color=resolved_style.color, font=resolved_style.font,
        pos=resolved_text_pos, wrap_width=resolved_wrap_width, align=align,
    )
    extra_stims = [text_stim]
    header_stim = _build_header_stim(win, header, header_pos, header_align, header_style, header_wrap_width)
    if header_stim is not None:
        extra_stims.append(header_stim)
    image_stim = _build_image_stim(win, image_path, pos=image_pos, size=image_size)
    if image_stim is not None:
        extra_stims.append(image_stim)

    # buttons[i] must return the same index i that key_map maps its key to.
    labels = button_labels or [str(i) for i in range(len(key_map))]
    buttons = two_button_row(win, labels) if len(labels) == 2 else [single_button(win, labels[0])]

    response = run_button_screen(win, keyboard_monitor, buttons=buttons, key_map=key_map, extra_stims=extra_stims)
    return {'response': response}


def run_break(
    win,
    keyboard_monitor,
    clock,
    title: str,
    message_fn: Callable[[float], str],
    duration_ms: float,
    skip_key: Optional[str] = None,
    title_style: Optional[TextStyle] = None,
    body_style: Optional[TextStyle] = None,
) -> dict:
    """Live-updating countdown break screen. `message_fn(remaining_seconds)`
    rebuilds the body text every frame, matching the JS break screens'
    `renderStimulus()` re-render on each `setInterval` tick. Ends early if
    `skip_key` is released, otherwise after `duration_ms` elapses. Port of
    endOfAgencyTaskBreak (parts/agency-task-core.ts), which always shows a
    skip button unconditionally (unlike the per-N-trial agency break,
    whose allowSkip is conditional and which is wired separately/more
    simply in main.py's run_break). `title_style`/`body_style` override
    the defaults (CONFIG.title/CONFIG.body)."""
    from psychopy import visual

    resolved_title_style = title_style or CONFIG.title
    resolved_body_style = body_style or CONFIG.body
    title_stim = visual.TextStim(win, text=title, pos=BREAK_TITLE_POS, **resolved_title_style.to_kwargs())
    body_stim = visual.TextStim(win, text='', pos=BREAK_BODY_POS, **resolved_body_style.to_kwargs())

    skip_key_lower = skip_key.lower() if skip_key else None
    start_time = clock.getTime()
    skipped = False

    while True:
        elapsed_ms = (clock.getTime() - start_time) * 1000.0
        remaining_seconds = resolve_break_remaining_seconds(elapsed_ms, duration_ms)

        for key, event_type, _ in keyboard_monitor.poll():
            if skip_key_lower is not None and event_type == 'up' and key.lower() == skip_key_lower:
                skipped = True

        if skipped or remaining_seconds <= 0:
            break

        body_stim.text = message_fn(remaining_seconds)
        title_stim.draw()
        body_stim.draw()
        win.flip()

    return {}


def run_text_only(
    win, text: str, image_path: Optional[Path] = None,
    style: Optional[TextStyle] = None, align: str = 'center',
    text_pos=None, image_pos=MESSAGE_IMAGE_POS, image_size=MESSAGE_IMAGE_SIZE, wrap_width: Optional[float] = None,
    header: Optional[str] = None, header_pos=(0, 0.7), header_align: str = 'center',
    header_style: Optional[TextStyle] = None, header_wrap_width: Optional[float] = None,
) -> None:
    """Draws a text-only (plus optional image/header) screen and flips it,
    but does NOT wait for any keypress or button click. Returns immediately.
    Useful for showing a message while a blocking operation (e.g., BLE connection)
    is in progress."""
    resolved_style = style or CONFIG.text
    resolved_text_pos = text_pos if text_pos is not None else (
        MESSAGE_TEXT_POS_WITH_IMAGE if image_path is not None else MESSAGE_TEXT_POS_CENTERED
    )
    resolved_wrap_width = wrap_width if wrap_width is not None else resolved_style.wrap_width
    text_stim = RichText(
        win, text, height=resolved_style.height, color=resolved_style.color, font=resolved_style.font,
        pos=resolved_text_pos, wrap_width=resolved_wrap_width, align=align,
    )
    extra_stims = [text_stim]
    header_stim = _build_header_stim(win, header, header_pos, header_align, header_style, header_wrap_width)
    if header_stim is not None:
        extra_stims.append(header_stim)
    image_stim = _build_image_stim(win, image_path, pos=image_pos, size=image_size)
    if image_stim is not None:
        extra_stims.append(image_stim)

    # Draw all stimuli and flip
    for stim in extra_stims:
        stim.draw()
    win.flip()