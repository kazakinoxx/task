"""Translator -- lightweight replacement for the i18next instance in
src/modules/experiment/jspsych/i18n.ts.

Translation content is NOT re-transcribed by hand -- it's the same JSON
resource files (src/locales copy/{en,fr}/ns1.json) copied verbatim into
i18n/locales/{en,fr}.json, loaded at runtime. This keeps the actual
wording/HTML markup byte-identical to the source rather than risking
transcription errors across ~230 lines of interpolated strings.

Interpolation uses the same `{{VAR}}` syntax i18next uses (not Python's
`str.format`), specifically so the JSON files can stay an unmodified
copy of the original resource files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union

_LOCALES_DIR = Path(__file__).parent / 'locales'
_INTERPOLATION_PATTERN = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def _load_locale(language: str) -> Dict[str, Any]:
    path = _LOCALES_DIR / f'{language}.json'
    with path.open('r', encoding='utf-8') as fh:
        return json.load(fh)


class Translator:
    def __init__(self, language: str = 'en'):
        self._tables: Dict[str, Dict[str, Any]] = {}
        self.language = language

    def _table(self, language: str) -> Dict[str, Any]:
        if language not in self._tables:
            self._tables[language] = _load_locale(language)
        return self._tables[language]

    def set_language(self, language: str) -> None:
        self.language = language

    def _lookup(self, key: str) -> Union[str, List[str], Dict[str, Any]]:
        """Supports dotted keys (e.g. 'LIKERT_RESPONSES.STRONGLY_DISAGREE')
        for nested JSON objects, mirroring how constants.ts calls
        `i18n.t('LIKERT_RESPONSES.STRONGLY_DISAGREE')`."""
        table = self._table(self.language)
        node: Any = table
        for part in key.split('.'):
            if not isinstance(node, dict) or part not in node:
                fallback_table = self._table('en')
                node = fallback_table
                for fallback_part in key.split('.'):
                    node = node[fallback_part]
                return node
            node = node[part]
        return node

    def t(self, key: str, return_objects: bool = False, **kwargs) -> Union[str, List[str]]:
        """Port of i18n.t(key, {...vars, returnObjects}). `return_objects`
        mirrors i18next's `returnObjects: true` option, used for array
        values like CORE_TAPPING_INSTRUCTIONS_PAGES.

        i18next interpolates {{VAR}} placeholders regardless of whether
        returnObjects is set or the looked-up value is a list vs. a
        plain string -- interpolation and returnObjects are independent
        options. The list/string branches below must both interpolate;
        skipping it for a non-list value with return_objects=True was a
        bug (a caller like INSTRUCTION_PAGES, whose locale value happens
        to be a single string rather than an array, would get back
        un-interpolated `{{HOLD_KEY}}` etc. placeholders)."""
        value = self._lookup(key)
        if return_objects:
            if isinstance(value, list):
                return [self._interpolate(v, kwargs) for v in value]
            if isinstance(value, str):
                return self._interpolate(value, kwargs)
            return value
        if isinstance(value, str):
            return self._interpolate(value, kwargs)
        return value

    @staticmethod
    def _interpolate(text: str, values: Dict[str, Any]) -> str:
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            return str(values[var_name]) if var_name in values else match.group(0)

        return _INTERPOLATION_PATTERN.sub(replace, text)
