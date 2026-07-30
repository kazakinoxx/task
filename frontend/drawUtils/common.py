"""Shared rendering helpers for the trial views in this package.

The view modules in `frontend/trials/` are deliberately thin adapters
that drive a pure state machine (from the src2 project) against a real
PsychoPy window. Two bits of glue were copy-pasted across almost all of
them; they live here instead:

- `resolve_text`: the "explicit override, else translated key, else
  literal fallback" resolution every view does for its on-screen strings.
- `MarkupStim`: a RichText that only rebuilds when its markup changes,
  for the per-frame text of the polling-loop views (countdown, tapping,
  hold-key practice) whose text usually stays the same frame-to-frame.

Neither is unit tested for its rendering (that needs a real window);
`resolve_text` is pure and is covered in frontend/tests.
"""

from __future__ import annotations

from typing import Optional

from src2.i18n.stimulus_text import to_plain_text


def resolve_text(
    translator,
    key: str,
    *,
    override: Optional[str] = None,
    plain: bool = False,
    fallback: str = '',
    **interpolations,
) -> str:
    """Resolve one piece of on-screen text from the three usual sources,
    in priority order:

      1. an explicit `override` (whatever non-None value the caller was
         given to show instead of the default),
      2. otherwise the translated `key` -- `translator.t(key,
         **interpolations)`, stripped to plain text when `plain=True`
         (for a `visual.TextStim`) or left as raw i18n markup when False
         (for a `RichText`/`MarkupStim` that colors the hold-key/tap-key
         spans),
      3. otherwise the `fallback` literal, used when there is no
         translator at all (e.g. the standalone demo scripts).

    Collapses the override/translator/fallback branch that was repeated
    in nearly every trial view."""
    if override is not None:
        return override
    if translator is not None:
        text = translator.t(key, **interpolations)
        return to_plain_text(text) if plain else text
    return fallback


class MarkupStim:
    """A `RichText` that only rebuilds when its markup actually changes.

    The polling-loop views recompute a markup string every frame, but the
    text usually stays the same across frames; rebuilding a RichText
    (which re-parses the markup and lays out fresh TextStims) every frame
    is wasteful. This keeps the last markup and its RichText and rebuilds
    only on change. Construct it once with the same styling kwargs you'd
    pass to RichText (`height`/`color`/`font`/`pos`/`wrap_width`/`align`),
    then call `draw(markup)` once per frame; empty markup draws nothing."""

    def __init__(self, win, **rich_kwargs):
        self._win = win
        self._rich_kwargs = rich_kwargs
        self._rich = None
        self._last_markup: Optional[str] = None

    def draw(self, markup: str) -> None:
        if not markup:
            return
        if markup != self._last_markup:
            from frontend.rich_text import RichText

            self._rich = RichText(self._win, markup, **self._rich_kwargs)
            self._last_markup = markup
        self._rich.draw()
