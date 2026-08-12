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


class ThermometerStim:
    def __init__(self, win, pos=(0, 0), width=THERMOMETER_WIDTH, height=THERMOMETER_HEIGHT, skip_frames=1):
        from psychopy import visual

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
        self._last_mercury_height = 0.0
        self._skip_frames = skip_frames
        self._frame_counter = 0

    def update(self, mercury_height_percent: float, bounds: Tuple[float, float]) -> None:
        """Update mercury height (and static positions if bounds change)."""
        # Increment counter and only update geometry every N frames
        self._frame_counter += 1
        if self._frame_counter % self._skip_frames != 0:
            # Use cached values for drawing
            return

        # Update mercury geometry
        _, _, w, h = mercury_rect_geometry(
            mercury_height_percent, self._bottom_left, self.width, self.height
        )
        self.mercury.height = max(h, 0.001)
        self.mercury.pos = (self.pos[0], self._bottom_left[1] + self.mercury.height / 2)
        self._last_mercury_height = mercury_height_percent

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