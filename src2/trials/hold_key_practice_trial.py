"""Hold-key practice trial -- port of
src/modules/experiment/trials/hold-key-practice-trial.ts
(`HoldKeyPracticePlugin`).

State machine: idle -> holding -> release_prompt -> feedback -> ended.
A brief release during 'holding' (a "twitch") gets a TWITCH_GRACE_MS
grace period to recover before counting as a failure; recovering does
NOT reset the original hold-duration countdown, which keeps running
from the initial hold start -- replicated faithfully below (see
docstring in `tick`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src2.utils.constants import HOLD_KEY_PRACTICE_DURATION

# Local to hold-key-practice-trial.ts.
SUCCESS_FEEDBACK_DURATION = 1.5  # seconds
FAILURE_FEEDBACK_DURATION = 3.0  # seconds
TWITCH_GRACE_SECONDS = 0.3


@dataclass
class HoldKeyPracticeParams:
    hold_key: str = ''
    hold_duration: float = HOLD_KEY_PRACTICE_DURATION  # seconds


class HoldKeyPracticeState:
    def __init__(self, params: HoldKeyPracticeParams):
        self.params = params
        self.phase = 'idle'  # idle | holding | release_prompt | feedback
        self.ended = False
        self.success: Optional[bool] = None

        self._hold_deadline: Optional[float] = None
        self._twitch_grace_deadline: Optional[float] = None
        self._feedback_deadline: Optional[float] = None

    def handle_key_down(self, key: str, now: float) -> None:
        if self.ended or key.lower() != self.params.hold_key.lower():
            return

        if self._twitch_grace_deadline is not None:
            # Key returned within the grace window -- cancel the pending
            # failure and resume; the original hold-duration countdown
            # (self._hold_deadline) is untouched and keeps running.
            self._twitch_grace_deadline = None
            return

        if self.phase == 'idle':
            self.phase = 'holding'
            self._hold_deadline = now + self.params.hold_duration

    def handle_key_up(self, key: str, now: float) -> None:
        if self.ended or key.lower() != self.params.hold_key.lower():
            return

        if self.phase == 'holding':
            self._twitch_grace_deadline = now + TWITCH_GRACE_SECONDS
        elif self.phase == 'release_prompt':
            self._show_feedback(now, success=True)

    def _show_release_prompt(self) -> None:
        self.phase = 'release_prompt'

    def _show_feedback(self, now: float, success: bool) -> None:
        self.phase = 'feedback'
        self.success = success
        self._feedback_deadline = now + (SUCCESS_FEEDBACK_DURATION if success else FAILURE_FEEDBACK_DURATION)

    def tick(self, now: float) -> None:
        if self.ended:
            return

        if self.phase == 'feedback':
            if self._feedback_deadline is not None and now >= self._feedback_deadline:
                self.ended = True
            return

        if self.phase != 'holding':
            return

        # hold_deadline and twitch_grace_deadline are independent timers
        # (matching the two independent setTimeout calls in the original);
        # if both are due in the same tick, resolve whichever was
        # chronologically earlier first.
        candidates = []
        if self._hold_deadline is not None and now >= self._hold_deadline:
            candidates.append((self._hold_deadline, 'hold_elapsed'))
        if self._twitch_grace_deadline is not None and now >= self._twitch_grace_deadline:
            candidates.append((self._twitch_grace_deadline, 'twitch_failed'))

        if not candidates:
            return
        candidates.sort(key=lambda c: c[0])
        _, event = candidates[0]
        if event == 'hold_elapsed':
            self._hold_deadline = None
            self._show_release_prompt()
        else:
            self._twitch_grace_deadline = None
            self._hold_deadline = None
            self._show_feedback(now, success=False)

    def hold_progress(self, now: float) -> Optional[float]:
        """Port of startProgressIndicator()'s `pct = elapsed / totalMs`.
        Returns a 0..1 fraction of `hold_duration` elapsed since the hold
        began, or None outside the 'holding' phase (mirrors the JS
        `currentPhase !== 'holding'` early-return in `updateProgress`)."""
        if self.phase != 'holding' or self._hold_deadline is None:
            return None
        remaining = self._hold_deadline - now
        elapsed = self.params.hold_duration - remaining
        return max(0.0, min(elapsed / self.params.hold_duration, 1.0))

    def build_trial_record(self) -> dict:
        return {'task': 'hold-key-practice', 'success': bool(self.success)}
