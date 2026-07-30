"""PhotoDiode flash schedule -- port of sendPhotoDiodeTrigger
(src/modules/experiment/triggers/trigger.ts).

The DOM version toggles a CSS class on a fixed-position div:
white -> (100ms) -> black, and if isEnd, a second white/black double-
pulse at 200ms/300ms. Here that becomes a `visual.Rect` pinned to the
configured screen corner, flipped white/black on the same schedule (see
frontend/photodiode.py's `PhotoDiodeFlasher`, a sibling project to this
one that owns all PsychoPy rendering).

The flash schedule is expressed as pure data (`photodiode_flash_schedule`)
so the timing logic is unit-testable without a PsychoPy window.
"""

from __future__ import annotations

from typing import List, Tuple

WHITE = 'white'
BLACK = 'black'

# Position/geometry defaults mirror the CSS corner classes in main.scss;
# actual pixel geometry comes from PhotoDiodeSettings at construction time.
CORNER_POSITIONS = ('top-left', 'top-right', 'customize', 'off')


def photodiode_flash_schedule(is_end: bool) -> List[Tuple[float, str]]:
    """Returns a list of (delay_seconds_from_now, color) events, in the
    order they should be applied. Matches sendPhotoDiodeTrigger exactly:
    immediate white, black at +100ms, and if is_end, white at +200ms and
    black at +300ms."""
    schedule = [(0.0, WHITE), (0.1, BLACK)]
    if is_end:
        schedule += [(0.2, WHITE), (0.3, BLACK)]
    return schedule
