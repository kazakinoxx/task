"""The rich-text parser is pure (no PsychoPy), so it's unit tested here;
the rendering (RichText) needs a real window and is verified manually.

Runs are (text, color-or-None, bold, size-scale).
"""

from frontend.rich_text import parse_rich_runs
from frontend.style_constants import HOLD_KEY_COLOR, TAP_KEY_COLOR


def test_plain_text_is_one_normal_run():
    assert parse_rich_runs('GO!') == [[('GO!', None, False, 1.0)]]


def test_hold_key_span_is_blue_bold():
    runs = parse_rich_runs("Hold the <span class='hold-key'>S</span> key")
    assert runs == [[('Hold the ', None, False, 1.0), ('S', HOLD_KEY_COLOR, True, 1.0), (' key', None, False, 1.0)]]


def test_tap_key_span_is_red_bold():
    runs = parse_rich_runs("Tap <span class='tap-key'>L</span>")
    assert runs == [[('Tap ', None, False, 1.0), ('L', TAP_KEY_COLOR, True, 1.0)]]


def test_hold_and_tap_fingers_use_the_same_colors_as_keys():
    runs = parse_rich_runs("<span class='hold-finger'>left</span><span class='tap-finger'>right</span>")
    assert runs == [[('left', HOLD_KEY_COLOR, True, 1.0), ('right', TAP_KEY_COLOR, True, 1.0)]]


def test_bold_tag_bolds_without_coloring():
    assert parse_rich_runs('<b>Get ready</b>') == [[('Get ready', None, True, 1.0)]]


def test_bold_with_inline_style_color():
    runs = parse_rich_runs("<b style='color:green'>GO!</b>")
    assert runs == [[('GO!', 'green', True, 1.0)]]


def test_span_with_inline_style_color_is_not_bold():
    runs = parse_rich_runs("<span style='color:#123456'>x</span>")
    assert runs == [[('x', '#123456', False, 1.0)]]


def test_headers_are_larger_and_bold():
    assert parse_rich_runs('<h2>Title</h2>') == [[('Title', None, True, 1.6)]]
    assert parse_rich_runs('<h3>Sub</h3>') == [[('Sub', None, True, 1.4)]]


def test_br_starts_a_new_line_without_a_gap():
    assert parse_rich_runs('one<br>two') == [[('one', None, False, 1.0)], [('two', None, False, 1.0)]]


def test_paragraphs_are_separated_by_a_blank_line():
    runs = parse_rich_runs('<p>hello</p><p>world</p>')
    assert runs == [[('hello', None, False, 1.0)], [], [('world', None, False, 1.0)]]


def test_html_entities_are_unescaped():
    assert parse_rich_runs('a &gt; b') == [[('a > b', None, False, 1.0)]]


def test_leading_and_trailing_blank_lines_are_dropped():
    assert parse_rich_runs('<br><br>text<br>') == [[('text', None, False, 1.0)]]


def test_literal_newline_breaks_a_line():
    assert parse_rich_runs('a\nb') == [[('a', None, False, 1.0)], [('b', None, False, 1.0)]]
