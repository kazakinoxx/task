"""Guardrail: the src2 project is the pure experiment-logic backend and
must never import psychopy -- all PsychoPy rendering lives in the
sibling `frontend/` project (see frontend/main.py's docstring). This
keeps `frontend` a swappable blackbox: a different frontend (or none,
for a future signal-processing-focused runtime) could stand in its
place without touching src2 at all.

`triggers/trigger.py` and `triggers/trigger_device.py` are a deliberate,
narrow exception: they optionally import `psychopy.core`/`psychopy.parallel`
for EEG trigger hardware I/O (timing/parallel-port output), which is a
different concern from screen rendering and predates this guardrail.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC2_ROOT = Path(__file__).parent.parent
_IMPORT_PATTERN = re.compile(r'^\s*(from psychopy|import psychopy)\b', re.MULTILINE)
_ALLOWED_EXCEPTIONS = {
    _SRC2_ROOT / 'triggers' / 'trigger.py',
    _SRC2_ROOT / 'triggers' / 'trigger_device.py',
}


def _all_backend_py_files():
    for path in _SRC2_ROOT.rglob('*.py'):
        if '__pycache__' in path.parts:
            continue
        yield path


def test_no_backend_file_imports_psychopy():
    offenders = []
    for path in _all_backend_py_files():
        if path in _ALLOWED_EXCEPTIONS:
            continue
        text = path.read_text(encoding='utf-8')
        if _IMPORT_PATTERN.search(text):
            offenders.append(str(path.relative_to(_SRC2_ROOT)))

    assert not offenders, (
        'These backend (src2) files import psychopy, breaking the backend/frontend '
        f'separation -- move the psychopy-touching code into frontend/ instead: {offenders}'
    )
