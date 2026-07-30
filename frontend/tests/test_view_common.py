"""resolve_text (frontend/trials/common.py) is pure -- no PsychoPy -- so
its source-priority and plain/markup handling are unit tested here.
MarkupStim needs a real window and is verified via the live smoke run.
"""

from frontend.trials.common import resolve_text


class FakeTranslator:
    """Minimal stand-in for src2.i18n.translator.Translator: looks a key
    up in a dict and does {{VAR}} interpolation, matching the real one."""

    def __init__(self, mapping):
        self.mapping = mapping

    def t(self, key, **interpolations):
        text = self.mapping[key]
        for name, value in interpolations.items():
            text = text.replace('{{' + name + '}}', str(value))
        return text


def test_override_wins_over_translator():
    translator = FakeTranslator({'K': 'translated'})
    assert resolve_text(translator, 'K', override='explicit') == 'explicit'


def test_translator_used_when_no_override():
    translator = FakeTranslator({'K': 'translated'})
    assert resolve_text(translator, 'K') == 'translated'


def test_fallback_used_when_no_translator():
    assert resolve_text(None, 'K', fallback='fb') == 'fb'


def test_fallback_defaults_to_empty_string():
    assert resolve_text(None, 'K') == ''


def test_empty_string_override_is_respected():
    # '' is a real value (not None), so it must win over the translator.
    translator = FakeTranslator({'K': 'translated'})
    assert resolve_text(translator, 'K', override='') == ''


def test_interpolations_are_passed_through():
    translator = FakeTranslator({'K': 'Hold {{HOLD_KEYS_REPLACE}} now'})
    assert resolve_text(translator, 'K', HOLD_KEYS_REPLACE='S and D') == 'Hold S and D now'


def test_plain_strips_markup():
    translator = FakeTranslator({'K': "Hold the <span class='hold-key'>S</span> key"})
    result = resolve_text(translator, 'K', plain=True)
    assert '<' not in result
    assert result == 'Hold the S key'


def test_markup_preserved_when_not_plain():
    translator = FakeTranslator({'K': "Hold the <span class='hold-key'>S</span> key"})
    assert resolve_text(translator, 'K') == "Hold the <span class='hold-key'>S</span> key"
