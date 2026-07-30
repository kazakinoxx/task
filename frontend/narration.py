"""Narration playback -- replaces the JS app's `jspsych-audio-narration`
`AudioNarration` instance (src/modules/experiment/experiment.ts's `run()`
takes a pre-built `narration: AudioNarration` and every parts/*.ts file
calls `narration.play(...)`/`narration.stop()` unconditionally).

`enabled` is resolved ONCE at construction from
`state.get_general_settings().useNarration` -- the JS app never rechecks
the setting at each call site either, since the enable/disable logic
lives entirely inside the AudioNarration instance handed to `run()`, not
in parts/*.ts. This means every call site in main.py can call
`narration.play(...)`/`.stop()` unconditionally, exactly mirroring the
JS `on_load`/`on_finish` hooks, with zero changes needed to any existing
trial render function's signature.

Output device selection: this dev machine's only installed PsychoPy
audio backend is PsychToolbox (PTB) -- `sounddevice`/`pyo`/`pygame`
aren't installed, so PTB is not just first-choice but the only option,
and reordering `prefs.hardware['audioLib']` wouldn't help. PTB enumerates
audio devices via PortAudio; on this machine both paired Bluetooth
headsets (checked via `psychtoolbox.audio.get_devices()`) only appear
under their Hands-Free Profile (HFP) endpoint -- mono/0-channel, meant
for call audio -- with no separate stereo A2DP playback endpoint visible
to PortAudio at all. That's a Windows Bluetooth/PortAudio enumeration
characteristic, not something this module can route around in software;
a wired headset (which does show a normal 2-channel WASAPI endpoint)
should work the same as speakers. `device`/`stereo` are exposed here so
a specific output can be forced if needed -- see `list_audio_devices()`
below to find the exact device name PsychoPy expects (must match
`DeviceName` exactly, not a substring).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src2.ui.assets import ASSETS_DIR


def list_audio_devices() -> List[dict]:
    """Lists output-capable audio devices as PsychToolbox/PortAudio sees
    them, for picking an exact `device` name to pass to Narration(). Not
    unit tested -- requires the psychtoolbox audio backend and real
    hardware. Run via:
        .venv310\\Scripts\\python -c "from frontend.narration import list_audio_devices; [print(d) for d in list_audio_devices()]"
    """
    import psychtoolbox.audio as ptb_audio

    return [d for d in ptb_audio.get_devices() if d.get('NrOutputChannels', 0) > 0]


class Narration:
    def __init__(
        self, assets_dir: Path = ASSETS_DIR, enabled: bool = True,
        device: Optional[str] = None, stereo: Optional[bool] = None,
    ):
        self.assets_dir = assets_dir
        self.enabled = enabled
        self.device = device
        self.stereo = stereo
        self._current_sound = None
        self._device_pref_applied = False

    def _apply_device_preference(self) -> None:
        """Sets prefs.hardware['audioDevice'] before the first
        `from psychopy import sound` anywhere in the process -- PTB reads
        this preference at import time, so it must be set before that
        first import (main.py imports psychopy.sound nowhere else, so
        this is the only place it happens)."""
        if self._device_pref_applied or self.device is None:
            return
        from psychopy import prefs

        prefs.hardware['audioDevice'] = [self.device]
        self._device_pref_applied = True

    def play(self, relative_path: str) -> None:
        if not self.enabled:
            return
        self._apply_device_preference()
        from psychopy import sound

        self.stop()
        file_path = self.assets_dir / relative_path
        if not file_path.exists():
            return
        kwargs = {} if self.stereo is None else {'stereo': self.stereo}
        self._current_sound = sound.Sound(str(file_path), **kwargs)
        self._current_sound.play()

    def stop(self) -> None:
        if self._current_sound is not None:
            self._current_sound.stop()
            self._current_sound = None
