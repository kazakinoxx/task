"""Release-keys trial -- port of
src/modules/experiment/trials/release-keys-trial.ts (`ReleaseKeysPlugin`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ReleaseKeysParams:
    valid_responses: List[str] = field(default_factory=list)


class ReleaseKeysState:
    """Pure port of the closure state in ReleaseKeysPlugin.trial()."""

    def __init__(self, params: ReleaseKeysParams):
        self.params = params
        self.keys_state = {key.lower(): True for key in params.valid_responses}
        self.error_occurred = False
        self.ended = False
        self._check_initial()

    def _all_keys_released(self) -> bool:
        return not any(self.keys_state.values())

    def _check_initial(self) -> None:
        if self._all_keys_released():
            self.ended = True

    def handle_key_up(self, key: str) -> None:
        key = key.lower()
        if key in self.keys_state:
            self.keys_state[key] = False
            if self._all_keys_released():
                self.ended = True
        if key == 'enter':
            self.ended = True

    def handle_key_down(self, key: str) -> None:
        key = key.lower()
        if key in self.keys_state:
            self.keys_state[key] = True

    def build_trial_record(self) -> dict:
        return {'errorOccurred': self.error_occurred}
