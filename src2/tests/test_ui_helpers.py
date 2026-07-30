from src2.ui.keyboard_monitor import KeyEdgeBuffer
from src2.ui.thermometer_stim import (
    bound_marker_y,
    mercury_fraction,
    mercury_rect_geometry,
    target_area_rect_geometry,
)


def test_mercury_fraction_clamps_to_0_1():
    assert mercury_fraction(-10) == 0
    assert mercury_fraction(0) == 0
    assert mercury_fraction(50) == 0.5
    assert mercury_fraction(100) == 1
    assert mercury_fraction(150) == 1


def test_mercury_rect_geometry_grows_from_bottom():
    x, y, w, h = mercury_rect_geometry(50, (0, -200), 100, 400)
    assert x == 0
    assert y == -200
    assert w == 100
    assert h == 200  # 50% of 400


def test_bound_marker_y_relative_to_container_bottom():
    y = bound_marker_y(25, -200, 400)
    assert y == -200 + 100  # 25% of 400 above the bottom


def test_target_area_rect_geometry_spans_lower_to_upper_bound():
    # Port of stimulus.ts's `#target-area` div (bottom: lowerBound%,
    # height: upperBound - lowerBound %) -- always drawn, independent of
    # the `targetArea` text-label flag.
    x, y, w, h = target_area_rect_geometry((25, 75), (0, -200), 100, 400)
    assert x == 0
    assert w == 100
    assert y == -200 + 400 * 0.25  # lower bound (25%) above the container bottom
    assert h == 400 * (0.75 - 0.25)  # spans from 25% to 75%


def test_target_area_rect_geometry_clamps_out_of_range_bounds():
    x, y, w, h = target_area_rect_geometry((-10, 150), (0, -200), 100, 400)
    assert y == -200  # clamped to 0%
    assert h == 400  # clamped to 100% - 0%


def test_key_edge_buffer_push_and_drain_in_order():
    buf = KeyEdgeBuffer()
    buf.push('S', 'down', 1.0)
    buf.push('L', 'up', 1.5)
    assert len(buf) == 2
    events = buf.drain()
    assert events == [('s', 'down', 1.0), ('l', 'up', 1.5)]
    assert len(buf) == 0
    assert buf.drain() == []
