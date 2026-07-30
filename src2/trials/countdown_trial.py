"""Countdown trial -- port of
src/modules/experiment/trials/countdown-trial.ts (`CountdownTrialPlugin`).

Same pure-state-machine / thin-PsychoPy-runner split as tapping_task_trial.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src2.utils.constants import COUNTDOWN_TIME, REHOLD_TIMEOUT

# Local to countdown-trial.ts (`const freezeFrameTime = 3000`), distinct
# from any other 3000ms constant in constants.py.
COUNTDOWN_FREEZE_FRAME_DURATION = 3.0  # seconds


def format_countdown_time(remaining_ms: float) -> str:
    """Port of formatTime -- MM:SS."""
    minutes = int(remaining_ms // 1000 // 60)
    seconds = int((remaining_ms - minutes * 1000 * 60) // 1000)
    return f'{minutes}:{seconds:02d}'


@dataclass
class CountdownParams:
    keys_to_hold: List[str] = field(default_factory=list)
    key_to_press: str = ''
    wait_time: float = COUNTDOWN_TIME  # seconds
    show_freeze_frame: bool = False


class CountdownState:
    """Pure port of the closure state in CountdownTrialPlugin.trial()."""

    def __init__(self, params: CountdownParams):
        self.params = params
        # NB: keys start as NOT held here (unlike TappingTaskState, which
        # assumes keys are already held at trial start) -- matches the JS
        # `keysState[key] = false` initialization.
        self.keys_state = {key: False for key in params.keys_to_hold}
        self.are_keys_held = False
        self.key_tapped_early_flag = False
        self.countdown_active = False
        self.freeze_frame_active = False
        self.ended = False

        self._countdown_deadline: Optional[float] = None
        self._freeze_frame_deadline: Optional[float] = None
        self._rehold_deadline: Optional[float] = None

    def handle_key_down(self, key: str, now: float) -> None:
        key = key.lower()
        if key in self.params.keys_to_hold:
            self.keys_state[key] = True
            self._update_are_keys_held(now)
        if key == self.params.key_to_press and (self.countdown_active or self.freeze_frame_active):
            self.key_tapped_early_flag = True

    def handle_key_up(self, key: str, now: float) -> None:
        key = key.lower()
        if key in self.params.keys_to_hold:
            self.keys_state[key] = False
            self._update_are_keys_held(now)

    def _update_are_keys_held(self, now: float) -> None:
        self.are_keys_held = all(self.keys_state[k] for k in self.params.keys_to_hold)
        if self.are_keys_held and not self.countdown_active and not self.freeze_frame_active:
            self._rehold_deadline = None
            if self.params.show_freeze_frame:
                self._start_freeze_frame(now)
            else:
                self._start_countdown(now)
        elif not self.are_keys_held and (self.countdown_active or self.freeze_frame_active):
            self._rehold_deadline = now + REHOLD_TIMEOUT / 1000.0

    def _start_freeze_frame(self, now: float) -> None:
        self.freeze_frame_active = True
        self._freeze_frame_deadline = now + COUNTDOWN_FREEZE_FRAME_DURATION

    def _start_countdown(self, now: float) -> None:
        self.countdown_active = True
        self._countdown_deadline = now + self.params.wait_time

    def tick(self, now: float) -> None:
        if (
            self.freeze_frame_active
            and self._freeze_frame_deadline is not None
            and now >= self._freeze_frame_deadline
        ):
            self.freeze_frame_active = False
            self._start_countdown(now)

        if self.countdown_active and self._countdown_deadline is not None and now >= self._countdown_deadline:
            self.countdown_active = False
            self.ended = True

        if self._rehold_deadline is not None and now >= self._rehold_deadline and not self.are_keys_held:
            # Reset back to the initial "hold keys" message, same as the
            # JS reholdTimeout callback -- including clearing
            # keyTappedEarlyFlag, which is a deliberate original behavior:
            # restarting the countdown from scratch forgets an early tap
            # from the aborted attempt.
            self.freeze_frame_active = False
            self.countdown_active = False
            self.key_tapped_early_flag = False
            self._rehold_deadline = None
            self._freeze_frame_deadline = None
            self._countdown_deadline = None

    def build_trial_record(self) -> dict:
        return {'task': 'countdown', 'keyTappedEarlyFlag': self.key_tapped_early_flag}
