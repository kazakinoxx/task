from src2.ui.assets import resolve_audio_relative_path, resolve_image_path


def test_resolve_image_path_returns_path_for_existing_file():
    path = resolve_image_path('tip.png')
    assert path is not None
    assert path.exists()
    assert path.name == 'tip.png'


def test_resolve_image_path_returns_none_for_missing_file():
    # A genuinely absent asset must degrade gracefully (return None so the
    # caller skips the image) rather than crash. (The previously-listed
    # two-offer-view-*/agency-task-en.png images DO ship in the source app
    # and are now present in assets, so they are no longer examples here.)
    assert resolve_image_path('definitely-not-a-real-file.png') is None


def test_resolve_audio_relative_path_is_audio_prefixed():
    assert resolve_audio_relative_path('sit-comfortably.mp3') == 'audio/sit-comfortably.mp3'
