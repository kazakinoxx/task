"""Thermometer geometry -- port of the thermometer DOM structure in
src/modules/experiment/jspsych/stimulus.ts.

Geometry (mercury/bounds-marker/target-area placement as fractions of
the thermometer's height) is expressed as pure functions so it's unit
testable without a PsychoPy window; the PsychoPy drawing wrapper
(`ThermometerStim`) lives in src2/frontend/thermometer_stim.py.
"""

from __future__ import annotations

from typing import Tuple


def mercury_fraction(mercury_height_percent: float) -> float:
    """Converts a 0-100 mercury height percentage into a 0-1 fraction of
    the thermometer's fillable height, clamped to [0, 1]."""
    return max(0.0, min(1.0, mercury_height_percent / 100.0))


def bound_fraction(bound_percent: float) -> float:
    """Converts a 0-100 bound value into a 0-1 fraction, same clamping
    as mercury_fraction (bounds are defined on the same 0-100 scale)."""
    return max(0.0, min(1.0, bound_percent / 100.0))


def mercury_rect_geometry(
    mercury_height_percent: float,
    container_bottom_left: Tuple[float, float],
    container_width: float,
    container_height: float,
) -> Tuple[float, float, float, float]:
    """Returns (x, y, width, height) of the mercury fill rect in the same
    units as the container, anchored to the container's bottom edge and
    growing upward -- mirrors the CSS `height: {mercuryHeight}%` fill
    anchored at the bottom of #mercury in stimulus.ts."""
    x, y = container_bottom_left
    fill_height = container_height * mercury_fraction(mercury_height_percent)
    return (x, y, container_width, fill_height)


def bound_marker_y(
    bound_percent: float, container_bottom: float, container_height: float
) -> float:
    """Y position of a bound marker line, mirrors CSS `bottom: {bound}%`
    positioning relative to the container's bottom edge."""
    return container_bottom + container_height * bound_fraction(bound_percent)


def target_area_rect_geometry(
    bounds: Tuple[float, float],
    container_bottom_left: Tuple[float, float],
    container_width: float,
    container_height: float,
) -> Tuple[float, float, float, float]:
    """Returns (x, y, width, height) of the blue target-area fill rect
    spanning from the lower to the upper bound -- port of stimulus.ts's
    `#target-area` div (`bottom: {lowerBound}%; height: {upperBound -
    lowerBound}%; background-color: #0000ff`), which is drawn
    unconditionally whenever a thermometer is shown, independent of the
    `targetArea` flag (that flag only gates the separate "TARGET AREA"
    text label, not this box)."""
    x, bottom = container_bottom_left
    lower_y = bottom + container_height * bound_fraction(bounds[0])
    upper_y = bottom + container_height * bound_fraction(bounds[1])
    return (x, lower_y, container_width, upper_y - lower_y)
