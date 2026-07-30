"""Agency tapping task trial -- port of
src/modules/experiment/trials/agency-tapping-task-trial.ts
(`AgencyTappingTask`).

This is the most complex trial in the app: it extends the base tapping
mechanic with a mid-trial "interruption" (pause, Y/N agency question,
hold-key reminder, resume countdown) driven by adaptive (ADO-selected)
delay. Same pure-state-machine / thin-PsychoPy-runner split as
tapping_task_trial.py, with two verified, deliberately preserved
quirks called out below (not porting mistakes).

Quirk 1 -- requiredTimeInBounds is vestigial: the plugin declares a
`requiredTimeInBounds` parameter and stores it in the output record, but
no logic in the original `trial()` body actually reads or enforces it.
The interruption is gated purely by elapsed time (`interruptionTime`)
and a tap-count threshold (`MIN_TAPS_FOR_INTERRUPTION`), not by any
continuous "time spent in bounds" tracking. Reproduced as-is: the field
is carried through to the output record but has no gating effect here.

Quirk 2 -- "not enough taps" branch double-counts interruptionTime: when
the interruption timer fires but `tapCount <= MIN_TAPS_FOR_INTERRUPTION`,
the original schedules a *second* `interruptionTime`-length timeout
before calling `stopRunning`, rather than stopping immediately or using
`secondHalfDuration`. This means such trials actually run for roughly
`2 * interruptionTime` (~1.33x `trial_duration`) instead of stopping at
`trial_duration`. Reproduced exactly in `tick()` below.

No safety margin: unlike the base tapping task (which allows
+/-PATIENT_SAFETY_MARGIN around the bounds), `isSuccess()` here requires
the mercury to be strictly within `[bounds[0], bounds[1]]` -- no margin.

No re-hold grace period: a released hold-key immediately flags
`keysReleasedFlag`/`errorOccurred` and schedules a fixed
`PREMATURE_KEY_RELEASE_ERROR_TIME` (1000ms) stop, with no chance to
re-hold and recover (unlike the base tapping task's `REHOLD_TIMEOUT`).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    COUNTDOWN_TIME,
    EXPECTED_MAXIMUM_PERCENTAGE_FOR_CALIBRATION,
    HALF_WIDTH_AGENCY_DELAY,
    MIN_TAPS_FOR_INTERRUPTION,
    NUM_TAPS_AGENCY_WITHOUT_DELAY,
    PRACTICE_TRIAL_DURATION,
    PREMATURE_KEY_RELEASE_ERROR_TIME,
    TRIAL_DURATION,
    TRIAL_DURATION_AGENCY_TASK,
)
from src2.utils.calculations import auto_increase_amount_calculation
from src2.utils.randomization import sample_delay_uniform_centered

DEFAULT_BOUNDS: Tuple[float, float] = (30, 50)


def compute_agency_auto_increase_amount(delay_level: float) -> float:
    """Port of the `autoIncreaseAmount()` callback in `agencyTappingTrial`.

    NOTE (preserved quirk): uses a hardcoded median of 10 (not
    calibration-derived), TRIAL_DURATION (5000ms, the base tapping
    trial's duration) rather than TRIAL_DURATION_AGENCY_TASK (10000ms,
    this trial's own actual duration), and a symmetric
    `[delayLevel, delayLevel]` "delay range" rather than `[0, delayLevel]`
    -- all reproduced exactly as in the original, which appears to reuse
    constants meant for the base tapping task.
    """
    return auto_increase_amount_calculation(
        EXPECTED_MAXIMUM_PERCENTAGE_FOR_CALIBRATION,
        TRIAL_DURATION,
        AUTO_DECREASE_RATE,
        AUTO_DECREASE_AMOUNT,
        10,
        (delay_level, delay_level),
    )


@dataclass
class AgencyTappingTaskParams:
    task: str = 'core'  # 'target' | 'practice' | 'core'
    keys_to_hold: List[str] = field(default_factory=list)
    key_to_press: str = ''
    delay_original: float = 0  # ms, ADO-selected (0 for practice/target)
    auto_decrease_amount: float = AUTO_DECREASE_AMOUNT
    auto_decrease_rate: float = AUTO_DECREASE_RATE  # ms
    auto_increase_amount: float = 10
    required_time_in_bounds: float = 2000  # stored only -- see module docstring, quirk 1
    show_thermometer: bool = True
    show_freeze_frame: bool = True
    bounds: Tuple[float, float] = DEFAULT_BOUNDS
    keys_released_flag: bool = False
    key_tapped_early_flag: bool = False
    target_area: bool = False
    trial_duration: float = TRIAL_DURATION_AGENCY_TASK  # ms


class AgencyTappingTaskState:
    def __init__(self, params: AgencyTappingTaskParams, interruption_time_offset: Optional[float] = None):
        self.params = params
        self.mercury_height = 0.0
        self.is_key_down = False
        self.tap_count = 0
        self.start_time = 0.0
        self.end_time = 0.0
        self.error = ''
        self.keys_state = {key: True for key in params.keys_to_hold}
        self.are_keys_held = True
        self.error_occurred = False
        self.is_running = False
        self.trial_ended = False
        self.keys_released_flag = params.keys_released_flag

        self.no_interruption = params.task == 'target'
        self.interruption_triggered = False
        self.is_in_interruption = False
        self.interruption_response: Optional[str] = None
        # UI-step flags consumed by the (thin) rendering layer to know
        # which part of the interruption sequence to display next.
        self.awaiting_interruption_response = False
        self.awaiting_hold_key_reminder = False
        self.awaiting_resume_countdown = False

        offset = interruption_time_offset if interruption_time_offset is not None else (random.random() * 1000 - 500)
        # ms, relative to trial start -- port of
        # `trial.trial_duration * 0.667 + Math.random()*1000 - 500`.
        self.interruption_time = params.trial_duration * 0.667 + offset
        self.second_half_duration = params.trial_duration - self.interruption_time

        self._pending_increases: List[Tuple[float, float]] = []
        self._next_decrease_time: Optional[float] = None
        self._premature_release_deadline: Optional[float] = None
        self._interruption_check_time: Optional[float] = None
        self._stop_deadline: Optional[float] = None
        self._resume_countdown_deadline: Optional[float] = None

    # -- success / mercury -----------------------------------------------

    def is_success(self) -> bool:
        lower, upper = self.params.bounds
        in_bounds = lower <= self.mercury_height <= upper  # no safety margin, see docstring
        return (
            in_bounds
            and not self.keys_released_flag
            and not self.params.key_tapped_early_flag
            and (self.no_interruption or self.interruption_response is not None)
        )

    def increase_mercury(self, amount: Optional[float] = None) -> None:
        amount = self.params.auto_increase_amount if amount is None else amount
        self.mercury_height = min(self.mercury_height + amount, 100)

    # -- lifecycle ---------------------------------------------------------

    def start(self, now: float) -> bool:
        if self.params.key_tapped_early_flag:
            self.stop_running(now, error_flag=True)
            return True
        self._start_running(now)
        return False

    def _start_running(self, now: float) -> None:
        self.is_running = True
        self.start_time = now * 1000
        self.tap_count = 0
        self.mercury_height = 0.0
        self.error = ''
        self._next_decrease_time = now + self.params.auto_decrease_rate / 1000.0
        if self.no_interruption:
            self._stop_deadline = now + PRACTICE_TRIAL_DURATION / 1000.0
        else:
            self._interruption_check_time = now + self.interruption_time / 1000.0

    def stop_running(self, now: float, error_flag: bool = False) -> None:
        if self.trial_ended:
            return
        self.trial_ended = True
        self.end_time = now * 1000
        self.is_running = False
        if error_flag:
            self.error_occurred = error_flag

    # -- key handlers --------------------------------------------------------

    def handle_key_down(self, key: str, now: float) -> None:
        key = key.lower()
        if key in self.params.keys_to_hold:
            self.keys_state[key] = True
            self._update_are_keys_held(now)
        elif key == self.params.key_to_press and self.is_running and not self.is_key_down:
            self.is_key_down = True

    def handle_key_up(self, key: str, now: float) -> None:
        key = key.lower()
        if key in self.params.keys_to_hold:
            self.keys_state[key] = False
            self._update_are_keys_held(now)
        elif key == self.params.key_to_press and self.is_running:
            self.is_key_down = False
            self.tap_count += 1
            if self.tap_count > NUM_TAPS_AGENCY_WITHOUT_DELAY:
                delay_level = self.params.delay_original
                delay_ms = 0 if delay_level == 0 else sample_delay_uniform_centered(delay_level, HALF_WIDTH_AGENCY_DELAY)
                self._pending_increases.append((now + delay_ms / 1000.0, self.params.auto_increase_amount))
            else:
                self.increase_mercury()

    def _update_are_keys_held(self, now: float) -> None:
        if self.trial_ended:
            return
        self.are_keys_held = all(self.keys_state[k] for k in self.params.keys_to_hold)
        if not self.are_keys_held and not self.params.key_tapped_early_flag and not self.is_in_interruption:
            # No re-hold grace period here (unlike the base tapping task) --
            # any release outside an interruption is immediately flagged.
            self.error = 'PREMATURE_KEY_RELEASE_ERROR_MESSAGE'
            self.keys_released_flag = True
            self.error_occurred = True
            self._premature_release_deadline = now + PREMATURE_KEY_RELEASE_ERROR_TIME / 1000.0

    # -- interruption sequence (driven by the rendering layer) ---------------

    def receive_interruption_response(self, response: str, now: float) -> None:
        """`response` is 'y' or 'n' (also accepts 'o' for French "oui",
        normalized to 'y', matching the original's `isYes = key === 'y'
        || key === 'o'`)."""
        normalized = 'y' if response.lower() in ('y', 'o') else 'n'
        self.interruption_response = normalized
        self.awaiting_interruption_response = False
        self.awaiting_hold_key_reminder = True

    def confirm_keys_reheld(self, now: float) -> None:
        self.awaiting_hold_key_reminder = False
        self.awaiting_resume_countdown = True
        self._resume_countdown_deadline = now + COUNTDOWN_TIME

    # -- polling tick --------------------------------------------------------

    def _due_events(self, now: float) -> List[Tuple[float, str, int]]:
        """Collects every timer that is currently due, tagged with its
        own fire time, so tick() can resolve them in true chronological
        order (see tick()'s docstring for why this matters)."""
        events: List[Tuple[float, str, int]] = []
        for i, (fire_time, _amount) in enumerate(self._pending_increases):
            if now >= fire_time:
                events.append((fire_time, 'pending_increase', i))
        if self.is_running and self._next_decrease_time is not None and now >= self._next_decrease_time:
            events.append((self._next_decrease_time, 'decrease', 0))
        if self._premature_release_deadline is not None and now >= self._premature_release_deadline:
            events.append((self._premature_release_deadline, 'premature_release', 0))
        if self._interruption_check_time is not None and now >= self._interruption_check_time and not self.trial_ended:
            events.append((self._interruption_check_time, 'interruption_check', 0))
        if (
            self.awaiting_resume_countdown
            and self._resume_countdown_deadline is not None
            and now >= self._resume_countdown_deadline
        ):
            events.append((self._resume_countdown_deadline, 'resume', 0))
        if self._stop_deadline is not None and now >= self._stop_deadline and not self.trial_ended:
            events.append((self._stop_deadline, 'stop', 0))
        return events

    def tick(self, now: float) -> None:
        """Resolves every timer due by `now`, one at a time, in
        chronological order of their own fire times (not the order they
        happen to be checked in). This matters because the original JS
        timers are truly independent -- e.g. a per-tap delayed-increase
        timeout and the interruption timeout race against each other in
        real time, and a pending increase must only be dropped if the
        interruption fires *before* it, not merely because both became
        due within the same polling gap. Re-collecting due events after
        each single resolution lets later effects (e.g. the interruption
        check scheduling a new stop deadline) cascade correctly within
        one `tick()` call when `now` has jumped far ahead."""
        while True:
            events = self._due_events(now)
            if not events:
                return
            fire_time, kind, index = min(events, key=lambda e: e[0])

            if kind == 'pending_increase':
                _, amount = self._pending_increases.pop(index)
                if not self.is_in_interruption:
                    self.increase_mercury(amount)
                # else: dropped, not rescheduled -- matches `if
                # (!isInInterruption) increaseMercury();` at fire time.

            elif kind == 'decrease':
                self.mercury_height = max(self.mercury_height - self.params.auto_decrease_amount, 0)
                self._next_decrease_time += self.params.auto_decrease_rate / 1000.0

            elif kind == 'premature_release':
                self.stop_running(fire_time, error_flag=True)
                self._premature_release_deadline = None

            elif kind == 'interruption_check':
                self._interruption_check_time = None
                if self.tap_count > MIN_TAPS_FOR_INTERRUPTION and not self.trial_ended:
                    self.interruption_triggered = True
                    self.is_in_interruption = True
                    self.is_running = False
                    self.awaiting_interruption_response = True
                else:
                    # Preserved quirk 2 -- see module docstring: schedules
                    # another full interruption_time delay rather than
                    # stopping immediately or using second_half_duration.
                    self._stop_deadline = fire_time + self.interruption_time / 1000.0

            elif kind == 'resume':
                self.awaiting_resume_countdown = False
                self.is_in_interruption = False
                self.is_running = True
                self._next_decrease_time = fire_time + self.params.auto_decrease_rate / 1000.0
                self._stop_deadline = fire_time + self.second_half_duration / 1000.0
                self._resume_countdown_deadline = None

            elif kind == 'stop':
                self.stop_running(fire_time, error_flag=False)

    # -- output --------------------------------------------------------------

    def build_trial_record(self) -> dict:
        return {
            'tapCount': self.tap_count,
            'delayOriginal': self.params.delay_original,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'mercuryHeight': self.mercury_height,
            'error': self.error,
            'bounds': list(self.params.bounds),
            'task': self.params.task,
            'errorOccurred': self.error_occurred,
            'keysReleasedFlag': self.keys_released_flag,
            'success': self.is_success(),
            'keyTappedEarlyFlag': self.params.key_tapped_early_flag,
            'keysState': dict(self.keys_state),
            'requiredTimeInBounds': self.params.required_time_in_bounds,
            'interruptionResponse': self.interruption_response,
        }
