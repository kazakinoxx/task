"""Asset path resolution for images/audio copied from the JS app's
public/assets/ into src2/assets/ (see src2/assets/README location:
audio/*.mp3, images/*.png).

Two of the JS app's own image references are already broken in the
source app itself (`two-offer-view-{en,fr}.png` and `agency-task-en.png`
don't exist there either -- only oddly-named/French-only variants do).
Per this port's "preserve-as-found, don't silently fix" convention,
`resolve_image_path` returns None for a missing file instead of raising,
so callers can gracefully skip drawing the image (matching a browser's
own graceful degradation for a 404'd <img>) rather than crash or
fabricate a substitute.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

ASSETS_DIR = Path(__file__).parent.parent.parent / 'src2' / 'assets'


def resolve_image_path(filename: str) -> Optional[Path]:
    path = ASSETS_DIR / 'images' / filename
    return path if path.exists() else None


def resolve_audio_relative_path(filename: str) -> str:
    """Returns the path relative to ASSETS_DIR (what Narration.play()
    expects), matching the JS app's `assets/audio/xxx.mp3`-relative call
    convention."""
    return f'audio/{filename}'
