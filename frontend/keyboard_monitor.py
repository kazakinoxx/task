"""PsychoPy/pyglet keyboard hold/tap monitoring.

The JS trials attach `document.addEventListener('keydown'/'keyup', ...)`
for the life of a trial, mutating a `keysState` dict and counting taps on
`keyup`. The closest desktop equivalent is NOT PsychoPy's high-level
`psychopy.hardware.keyboard.Keyboard` (which is oriented around discrete
buffered key-press events, not live continuous hold-state) but the
pyglet window's native `on_key_press`/`on_key_release` callbacks --
PsychoPy's default window backend is a pyglet window, and pyglet
dispatches real keydown/keyup events just like the DOM does. This makes
`PygletKeyHoldMonitor` a genuinely 1:1 architectural analogue of the JS
event-listener model, not an approximation via polling.

The event-edge bookkeeping itself (`KeyEdgeBuffer`) is kept pure and
lives in src2/ui/keyboard_monitor.py so it can be unit tested without
pyglet/psychopy installed; `PygletKeyHoldMonitor` here is a thin,
hardware-dependent adapter on top, verified manually on a machine with a
real display and keyboard.
"""

from __future__ import annotations

from typing import List, Tuple

from src2.ui.keyboard_monitor import KeyEdgeBuffer


class PygletKeyHoldMonitor:
    """Adapts a PsychoPy (pyglet-backed) window's native keyboard events
    into the (key, 'down'|'up', time) stream that trial state machines
    consume.

    Not unit tested (requires a real window/display) -- verify manually
    on-machine: run scripts/demo_tapping_task.py with an actual keyboard
    and confirm hold/tap detection feels correct.
    """

    def __init__(self, win, clock):
        self.win = win
        self.clock = clock
        self._buffer = KeyEdgeBuffer()

        # pyglet.window.key module maps human key names to symbol constants;
        # build the reverse lookup once so callbacks can report lowercase
        # key names matching the JS `event.key.toLowerCase()` convention.
        import pyglet.window.key as pyglet_key

        self._symbol_to_name = {
            getattr(pyglet_key, attr): attr.lower()
            for attr in dir(pyglet_key)
            if not attr.startswith('_') and isinstance(getattr(pyglet_key, attr), int)
        }

        win.winHandle.on_key_press = self._on_key_press
        win.winHandle.on_key_release = self._on_key_release

    def _symbol_name(self, symbol: int) -> str:
        return self._symbol_to_name.get(symbol, str(symbol))

    def _on_key_press(self, symbol: int, modifiers: int) -> None:
        self._buffer.push(self._symbol_name(symbol), 'down', self.clock.getTime())

    def _on_key_release(self, symbol: int, modifiers: int) -> None:
        self._buffer.push(self._symbol_name(symbol), 'up', self.clock.getTime())

    def poll(self) -> List[Tuple[str, str, float]]:
        """Pumps the window's event queue (dispatching any buffered
        on_key_press/on_key_release callbacks) and returns the
        (key, type, time) events collected since the last poll.

        Escape quits immediately via core.quit(): fullscreen PsychoPy
        windows on Windows don't reliably respond to Alt+F4/Alt+Tab, so
        this is the only guaranteed way out of a running trial loop."""
        self.win.winHandle.dispatch_events()
        events = self._buffer.drain()
        if any(key == 'escape' and event_type == 'down' for key, event_type, _ in events):
            from psychopy import core

            core.quit()
        return events
