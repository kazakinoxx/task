from src2.ui.assets import resolve_audio_relative_path, resolve_image_path


def test_resolve_image_path_returns_path_for_existing_file():
    path = resolve_image_path('tip.png')
    assert path is not None
    assert path.exists()
    assert path.name == 'tip.png'


def test_resolve_image_path_returns_none_for_missing_file():
    # Mirrors two JS asset references that are broken in the source app
    # itself (two-offer-view-{en,fr}.png, agency-task-en.png) -- callers
    # must degrade gracefully (skip the image) rather than crash.
    assert resolve_image_path('two-offer-view-en.png') is None
    assert resolve_image_path('agency-task-en.png') is None
    assert resolve_image_path('definitely-not-a-real-file.png') is None


def test_resolve_audio_relative_path_is_audio_prefixed():
    assert resolve_audio_relative_path('sit-comfortably.mp3') == 'audio/sit-comfortably.mp3'
