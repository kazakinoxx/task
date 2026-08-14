"""Thermometer PsychoPy drawing wrapper -- with frame‑skipping for performance."""

from __future__ import annotations

from typing import Tuple

from frontend.style_constants import (
    THERMOMETER_BOUND_LINE_COLOR,
    THERMOMETER_HEIGHT,
    THERMOMETER_MERCURY_COLOR,
    THERMOMETER_OUTLINE_COLOR,
    THERMOMETER_TARGET_AREA_COLOR,
    THERMOMETER_UNITS,
    THERMOMETER_WIDTH,
)
from src2.ui.thermometer_stim import bound_marker_y, mercury_rect_geometry, target_area_rect_geometry


# Time constant for easing the drawn mercury toward its true height, matching
# the web app's `#mercury { transition: height 0.1s linear; }` -- without it the
# PsychoPy bar snaps between discrete tap/decay steps and looks choppy next to
# the browser's animated one.
MERCURY_SMOOTH_TIME = 0.1  # seconds


class ThermometerStim:
    def __init__(self, win, pos=(0, 0), width=THERMOMETER_WIDTH, height=THERMOMETER_HEIGHT, skip_frames=1):
        from psychopy import visual
        import time as _time

        self._time = _time

        self.win = win
        self.pos = pos
        self.width = width
        self.height = height
        bottom_left = (pos[0] - width / 2, pos[1] - height / 2)
        self._bottom_left = bottom_left

        # Create all drawing primitives (static and dynamic)
        self.outline = visual.Rect(
            win, width=width, height=height, pos=pos, lineColor=THERMOMETER_OUTLINE_COLOR,
            fillColor=None, units=THERMOMETER_UNITS,
        )
        self.target_area = visual.Rect(
            win, width=width, height=1, fillColor=THERMOMETER_TARGET_AREA_COLOR,
            lineColor=None, units=THERMOMETER_UNITS,
        )
        self.lower_bound_line = visual.Line(win, lineColor=THERMOMETER_BOUND_LINE_COLOR, units=THERMOMETER_UNITS)
        self.upper_bound_line = visual.Line(win, lineColor=THERMOMETER_BOUND_LINE_COLOR, units=THERMOMETER_UNITS)
        self.mercury = visual.Rect(
            win, width=width, height=1, fillColor=THERMOMETER_MERCURY_COLOR,
            lineColor=None, units=THERMOMETER_UNITS,
        )

        # Cached geometry
        self._bounds = None
        # Drawn (eased) height vs. the true target height. The drawn value
        # glides toward the target so the bar animates smoothly between the
        # discrete mercury steps (see MERCURY_SMOOTH_TIME).
        self._displayed_height = 0.0
        self._last_time = None

    def update(self, mercury_height_percent: float, bounds: Tuple[float, float]) -> None:
        """Update mercury height (and static positions if bounds change).

        The drawn height eases toward `mercury_height_percent` over
        ~MERCURY_SMOOTH_TIME, framerate-independently (using the real elapsed
        time between calls), so the bar reads as a smooth glide rather than
        snapping on each tap/decay step -- matching the web app's CSS
        `transition: height 0.1s linear`."""
        now = self._time.perf_counter()
        dt = (now - self._last_time) if self._last_time is not None else 0.0
        self._last_time = now
        alpha = 1.0 if MERCURY_SMOOTH_TIME <= 0 else min(1.0, dt / MERCURY_SMOOTH_TIME)
        self._displayed_height += (mercury_height_percent - self._displayed_height) * alpha

        # Update mercury geometry from the eased height
        _, _, w, h = mercury_rect_geometry(
            self._displayed_height, self._bottom_left, self.width, self.height
        )
        self.mercury.height = max(h, 0.001)
        self.mercury.pos = (self.pos[0], self._bottom_left[1] + self.mercury.height / 2)

        # Update static elements if bounds changed
        if bounds != self._bounds:
            self._bounds = bounds
            _, target_y, _, target_h = target_area_rect_geometry(
                bounds, self._bottom_left, self.width, self.height
            )
            self.target_area.height = max(target_h, 0.001)
            self.target_area.pos = (self.pos[0], target_y + self.target_area.height / 2)

            lower_y = bound_marker_y(bounds[0], self._bottom_left[1], self.height)
            upper_y = bound_marker_y(bounds[1], self._bottom_left[1], self.height)
            half_w = self.width / 2
            self.lower_bound_line.start = (self.pos[0] - half_w, lower_y)
            self.lower_bound_line.end = (self.pos[0] + half_w, lower_y)
            self.upper_bound_line.start = (self.pos[0] - half_w, upper_y)
            self.upper_bound_line.end = (self.pos[0] + half_w, upper_y)

    def draw(self) -> None:
        """Draw the thermometer, back-to-front, so the stacking priority is
        black > red > blue: the blue target area sits at the back, the red
        mercury bar over it, and the black outline + bound lines on top (so
        the outline reads as a clean frame in front of the red bar rather
        than being hidden behind it)."""
        self.target_area.draw()
        self.mercury.draw()
        self.outline.draw()
        self.lower_bound_line.draw()
        self.upper_bound_line.draw()