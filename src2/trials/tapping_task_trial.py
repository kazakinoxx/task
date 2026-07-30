"""Tapping task trial -- port of
src/modules/experiment/trials/tapping-task-trial.ts (the `TappingTask`
jsPsych plugin).

Split in two, per the project's testing strategy:

- `TappingTaskParams` / `TappingTaskState`: a pure state machine with no
  PsychoPy dependency, driven by external (key, event, time) inputs and
  a `tick(now)` call once per polling iteration. This is where almost
  all of the experimentally-meaningful logic lives (mercury math,
  success criteria, timing thresholds), so it's fully unit-testable.
- `run_tapping_task_trial`: the thin PsychoPy rendering loop that wires
  a real window/keyboard/trigger device to the state machine. Not unit
  tested -- verify manually on a machine with a display and keyboard.

Timing model note: the JS version uses independent `setTimeout`/
`setInterval` calls (a self-rescheduling `decreaseInterval`, a per-tap
delayed-increase timeout, a re-hold grace-period timeout). PsychoPy has
no direct equivalent to independent concurrent timers, so this port
uses a single polling loop that calls `tick(now)` every iteration; `tick`
checks a list of "due" events (pending delayed increases, the next
auto-decrease time, the re-hold deadline) against the current clock
time. This is behaviorally equivalent (same thresholds fire at the same
wall-clock offsets) and, being driven by the same window/keyboard poll
loop, has tighter jitter than the browser's independent macrotask timers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src2.utils.constants import (
    AUTO_DECREASE_AMOUNT,
    AUTO_DECREASE_RATE,
    GO_DURATION,
    NUM_TAPS_WITHOUT_DELAY,
    PATIENT_SAFETY_MARGIN,
    REHOLD_TIMEOUT,
    TRIAL_DURATION,
)
from src2.utils.randomization import random_number_bm


@dataclass
class TappingTaskParams:
    task: str = ''
    keys_to_hold: List[str] = field(default_factory=list)
    key_to_press: str = ''
    random_delay: Tuple[float, float] = (0, 0)  # ms
    auto_decrease_amount: float = AUTO_DECREASE_AMOUNT
    auto_decrease_rate: float = AUTO_DECREASE_RATE  # ms
    auto_increase_amount: float = 10
    show_thermometer: bool = True
    bounds: Tuple[float, float] = (20, 40)
    trial_duration: float = TRIAL_DURATION  # ms
    keys_released_flag: bool = False
    reward: float = 0
    key_tapped_early_flag: bool = False
    show_freeze_frame: bool = False
    show_keyboard: bool = False
    random_chance_accepted: bool = False
    target_area: bool = False
    use_photo_diode: str = 'off'
    # Deviation from the JS (which flashes the #go-message on every trial):
    # here the brief green GO header only appears when this is True. Left
    # off for practice/calibration/demo (where the go text stays visible
    # in the center while tapping); switched on only for validation, per
    # the study author's request.
    flash_go_message: bool = False
    start_prompt_message: Optional[str] = None
    continue_tapping_reminder_message: Optional[str] = None
    continue_tapping_reminder_delay: float = 1200  # ms


class TappingTaskState:
    """Pure port of the closure state + handlers inside TappingTask.trial()."""

    def __init__(self, params: TappingTaskParams):
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
        # 'start' | 'firstTap' | None (None when show_freeze_frame is False)
        self.freeze_frame_state = 'start' if params.show_freeze_frame else None
        self.last_tap_time = 0.0
        self.keys_released_flag = params.keys_released_flag
        # Port of showContinueReminder()/the 200ms continueReminderInterval:
        # True once tapping has gone quiet for continue_tapping_reminder_delay
        # after at least one tap; only ever set when
        # continue_tapping_reminder_message is configured (opt-in per trial,
        # matching the JS `if (trial.continueTappingReminderMessage)` guard --
        # only practice.ts's tappingPracticeBlock wires this on, at 700ms).
        self.showing_continue_reminder = False
        # Port of the #go-message flash: visible for GO_DURATION ms right
        # when the trial starts running, then hidden -- see
        # startRunning()'s goElement.style.visibility toggle and
        # stopRunning()'s "REMOVE GO IN CASE IT IS SHOWING" cleanup. Only
        # ever set when params.flash_go_message is True (validation only).
        self.showing_go_message = False

        self._random_skip = params.random_chance_accepted
        self._pending_increases: List[Tuple[float, float]] = []
        self._rehold_deadline: Optional[float] = None
        self._next_decrease_time: Optional[float] = None
        self._go_message_deadline: Optional[float] = None

    # -- success / mercury -----------------------------------------------

    def is_success(self) -> bool:
        lower, upper = self.params.bounds
        in_bounds = (
            lower - PATIENT_SAFETY_MARGIN <= self.mercury_height <= upper + PATIENT_SAFETY_MARGIN
        )
        return (
            in_bounds and not self.keys_released_flag and not self.params.key_tapped_early_flag
        ) or self._random_skip

    def increase_mercury(self, amount: Optional[float] = None) -> None:
        amount = self.params.auto_increase_amount if amount is None else amount
        self.mercury_height = min(self.mercury_height + amount, 100)

    # -- lifecycle ---------------------------------------------------------

    def start(self, now: float) -> bool:
        """Mirrors the top-of-trial() branch: if the trial was already
        flagged as a key-tapped-early error (set by a preceding countdown
        trial) and this isn't a random-chance auto-success, end
        immediately. Returns True if the trial ended here."""
        if self.params.key_tapped_early_flag and not self._random_skip:
            self.stop_running(now, error_flag=True)
            return True
        return False

    def start_running(self, now: float) -> bool:
        """Mirrors startRunning(). Returns True if the trial ended
        immediately (random-chance auto-success skip)."""
        if self._random_skip:
            self.stop_running(now, error_flag=False)
            return True
        self.is_running = True
        self.start_time = now * 1000  # ms, matches jsPsych.getTotalTime()
        self.tap_count = 0
        self.mercury_height = 0.0
        self.error = ''
        self._next_decrease_time = now + self.params.auto_decrease_rate / 1000.0
        self.last_tap_time = 0.0
        self.showing_continue_reminder = False
        self.showing_go_message = self.params.flash_go_message
        self._go_message_deadline = (
            now + GO_DURATION / 1000.0 if self.params.flash_go_message else None
        )
        return False

    def stop_running(self, now: float, error_flag: bool = False) -> None:
        if self.trial_ended:
            return
        self.trial_ended = True
        self.end_time = now * 1000  # ms, matches jsPsych.getTotalTime()
        self.is_running = False
        self.error_occurred = error_flag
        self.showing_go_message = False

    # -- key handlers --------------------------------------------------------

    def handle_key_down(self, key: str, now: float) -> None:
        key = key.lower()
        if key in self.params.keys_to_hold:
            self.keys_state[key] = True
            self._update_are_keys_held(now)
        elif key == self.params.key_to_press and self.is_running and not self.is_key_down:
            self.is_key_down = True

    def handle_key_up(self, key: str, now: float) -> List[str]:
        """Returns a list of cosmetic UI event names for the rendering
        layer (e.g. 'flash_checkmark', 'freeze_frame_first_tap') -- these
        carry no experimental data, only visual feedback."""
        key = key.lower()
        ui_events: List[str] = []

        if key in self.params.keys_to_hold:
            self.keys_state[key] = False
            self._update_are_keys_held(now)
        elif key == self.params.key_to_press and self.is_running:
            self.is_key_down = False
            self.tap_count += 1
            self.last_tap_time = now
            self.showing_continue_reminder = False
            if self.params.task == 'practice':
                ui_events.append('flash_checkmark')

            if self.params.task in ('demo', 'block') and self.tap_count > NUM_TAPS_WITHOUT_DELAY:
                delay_ms = random_number_bm(*self.params.random_delay)
                self._pending_increases.append((now + delay_ms / 1000.0, self.params.auto_increase_amount))
            else:
                self.increase_mercury()

        if self.params.show_freeze_frame:
            if self.freeze_frame_state == 'start' and key == self.params.key_to_press:
                self.freeze_frame_state = 'firstTap'
                ui_events.append('freeze_frame_first_tap')
            elif self.freeze_frame_state == 'firstTap' and key == self.params.key_to_press:
                ui_events.append('freeze_frame_subsequent_tap')

        return ui_events

    def _update_are_keys_held(self, now: float) -> None:
        if self.trial_ended:
            return
        self.are_keys_held = all(self.keys_state[k] for k in self.params.keys_to_hold)
        if not self.are_keys_held and not self.params.key_tapped_early_flag and not self._random_skip:
            self._rehold_deadline = now + REHOLD_TIMEOUT / 1000.0
        elif self.are_keys_held:
            # Simplification vs. the JS version, which never explicitly
            # clears a stacked reholdTimeout on re-hold -- but each such
            # timeout's callback re-checks `areKeysHeld` at fire time and
            # no-ops if keys are held again, so clearing here produces
            # identical observable behavior.
            self._rehold_deadline = None

    # -- polling tick --------------------------------------------------------

    def tick(self, now: float) -> List[str]:
        """Call once per polling loop iteration. Applies due delayed
        mercury increases, auto-decrease steps, and the re-hold timeout.
        Returns event names for anything the trial-ending caller should
        react to (currently just 'stopped_due_to_release')."""
        events: List[str] = []

        if (
            self.showing_go_message
            and self._go_message_deadline is not None
            and now >= self._go_message_deadline
        ):
            self.showing_go_message = False
            self._go_message_deadline = None

        still_pending = []
        for fire_time, amount in self._pending_increases:
            if now >= fire_time:
                self.increase_mercury(amount)
            else:
                still_pending.append((fire_time, amount))
        self._pending_increases = still_pending

        if self.is_running and self._next_decrease_time is not None:
            while now >= self._next_decrease_time:
                self.mercury_height = max(self.mercury_height - self.params.auto_decrease_amount, 0)
                self._next_decrease_time += self.params.auto_decrease_rate / 1000.0

        if (
            self._rehold_deadline is not None
            and now >= self._rehold_deadline
            and not self.are_keys_held
            and not self.trial_ended
        ):
            self.keys_released_flag = True
            self.stop_running(now, error_flag=True)
            events.append('stopped_due_to_release')

        # Port of the 200ms continueReminderInterval poller: matches the JS
        # early-return guard (`trialEnded || !isRunning || tapCount === 0 ||
        # lastTapTime === 0`) inverted, then the inactivity check.
        if (
            self.params.continue_tapping_reminder_message
            and not self.trial_ended
            and self.is_running
            and self.tap_count > 0
            and self.last_tap_time != 0
        ):
            inactive_time = now - self.last_tap_time
            if inactive_time >= self.params.continue_tapping_reminder_delay / 1000.0:
                self.showing_continue_reminder = True
            self._rehold_deadline = None

        return events

    # -- output --------------------------------------------------------------

    def build_trial_record(self) -> dict:
        return {
            'tapCount': self.tap_count,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'mercuryHeight': self.mercury_height,
            'error': self.error,
            'bounds': list(self.params.bounds),
            'reward': self.params.reward,
            'task': self.params.task,
            'errorOccurred': self.error_occurred,
            'keysReleasedFlag': self.keys_released_flag,
            'success': self.is_success(),
            'keyTappedEarlyFlag': self.params.key_tapped_early_flag,
            'keysState': dict(self.keys_state),
            'medianTaps': (
                100 + (self.params.trial_duration / self.params.auto_decrease_rate) * self.params.auto_decrease_amount
            ) / self.params.auto_increase_amount,
        }
