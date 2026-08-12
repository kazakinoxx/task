"""Phase wiring -- binds the real PsychoPy trial/screen renderers (this
frontend project) into the `PhaseRunners` bundle that the sibling src2
project's `run_experiment` timeline consumes.

Everything here is the concrete "how each phase is shown" layer;
`frontend/main.py` is the thin entry point that builds the window,
constructs these runners, and hands them to `run_experiment`. Kept in
its own module so `main.py` reads as a short launcher and each phase's
wiring lives in one place.

The high-level experiment *structure* (which phases run, in what order)
lives in `src2/experiment_runner.py::run_experiment`; this module only
supplies the per-phase presentation.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from frontend.narration import Narration


from src2.data.data_writer import RecordingTrialHistory
from src2.experiment_runner import PhaseRunners
import src2.i18n.stimulus_text as stimulus_text
from src2.i18n.translator import Translator
from src2.parts.agency_task_core import (
    AgencyBreakRunners,
    AgencyCoreRunners,
    AgencyPracticeRunners,
    run_agency_core_block,
    run_agency_practice_trials,
)
from src2.parts.calibration import CalibrationRunners, run_calibration_loop
from src2.parts.introduction import IntroductionRunners, run_introduction

from src2.parts.task_core import (
    AcceptanceRunners,
    TaskBlockScreenRunners,
    TaskTrialRunners,
    get_num_trials_per_block,
    resolve_trial_block_sequence,
    run_task_trial_block,
)
from src2.parts.validation import (
    ValidationFailedError,
    ValidationRunners,
    resolve_validation_result,
    run_validation_trial_loop,
    should_finish_early_after_extra_validation,
    should_run_extra_validation,
)
from src2.state.experiment_state import ExperimentState
from src2.trials.acceptance_trial import AcceptanceTrialParams
from src2.trials.agency_tapping_task_trial import AgencyTappingTaskParams
from src2.trials.countdown_trial import CountdownParams
from src2.trials.hold_key_practice_trial import HoldKeyPracticeParams
from src2.trials.likert_trial import LikertSurveyParams
from src2.trials.release_keys_trial import ReleaseKeysParams
from src2.trials.success_trial import (
    resolve_basic_success_screen_params,
    resolve_success_screen_params,
    resolve_success_screen_params_validation,
)
from src2.trials.tapping_task_trial import TappingTaskParams
from src2.triggers.trigger import send_trigger
from src2.triggers.trigger_device import resolve_device_status_message
from src2.ui.assets import resolve_audio_relative_path, resolve_image_path
from src2.utils.calculations import get_hold_keys, get_tap_key, resolve_link
from src2.utils.constants import HOLD_KEY_MAX_FAILURES, MAIN_TASK_BREAK_DURATION, TASK_COMPLETION_BREAK_DURATION
from device_connection.connect import connect_device

from frontend.drawUtils.message import run_message
from frontend.parts import introduction, practice, calibration, validation, task_core, agency_task_core,final_calibration, connection
from frontend.parts.context import PhaseContext
from device_connection import BLEController


CONTINUE_HINT = '\nClick the button below to proceed.'
SKIP_HINT = '\n\n[Press SPACE to skip]'
LEFT_HAND_KEY = 'left'
RIGHT_HAND_KEY = 'right'




def resolve_end_message_text(state: ExperimentState, translator: Translator, participant_name: str) -> str:
    """Shared by run_end_page and main()'s abort-early handler -- both
    port finishExperimentEarly (jspsych/finish.ts) / getEndPage
    (experiment.ts), which build the identical next-step-or-generic-
    message html."""
    next_step = state.get_next_step_settings()
    if next_step.linkToNextPage:
        title = stimulus_text.to_plain_text(next_step.title)
        description = stimulus_text.to_plain_text(next_step.description)
        link = resolve_link(next_step.link, participant_name)
        return f'{title}\n\n{description}\n\n{next_step.linkText}: {link}'
    return stimulus_text.to_plain_text(stimulus_text.experiment_has_ended_message(translator))


def make_phase_runners(
    win, keyboard_monitor, clock, state: ExperimentState, history: RecordingTrialHistory, trigger_device,
    translator: Translator, participant_name: str, narration: Narration, ble: Optional[connection.BLEController] = None
) -> PhaseRunners:
    """Wires the real PsychoPy trial runners into the same orchestration
    functions exercised by tests/test_end_to_end_smoke.py with fakes."""

    context = PhaseContext(
        win=win,
        keyboard_monitor=keyboard_monitor,
        clock=clock,
        state=state,
        history=history,
        trigger_device=trigger_device,
        translator=translator,
        participant_name=participant_name,
        narration=narration,
        ble=ble,
    )

    def trigger(outside_task: bool, decision: bool, is_end: bool, **kwargs) -> None:
        send_trigger(trigger_device, outside_task=outside_task, decision_trigger=decision, is_end=is_end, **kwargs)


    def run_device_connect() -> None:
        """Port of deviceConnectPages (triggers/serialport.ts). The
        actual device is already resolved deterministically from the
        `--trigger` CLI flag before this runs (see resolve_device_status_
        message's docstring) -- this is a status confirmation, not a
        connect/retry flow."""
        status_text = resolve_device_status_message(trigger_device)
        run_message(win, keyboard_monitor, status_text + CONTINUE_HINT)

   

    def run_continue_message() -> None:
        """Port of continueMessageDirection (experiment.ts) -- shown
        instead of introduction/practice/calibration/validation when
        resuming a previously-started participant."""
        header = f'<h2>{stimulus_text.continue_message_title(translator)}</h2>'
        text = stimulus_text.continue_message_direction(translator)
        run_message(
            win, keyboard_monitor, text + CONTINUE_HINT, align='center',
            header=header, header_pos=(0, 0.7), header_align='center', wrap_width=0.9,
        )

    def run_end_of_agency_break() -> None:
        from frontend.drawUtils.message import run_break
        """Port of endOfAgencyTaskBreak (parts/agency-task-core.ts) --
        the one-time break shown between the EBDM and Agency blocks when
        both run in the same session, distinct from the per-N-trial
        agency break (`run_break` above), which always shows a skip
        button unconditionally."""
        title = stimulus_text.to_plain_text(stimulus_text.agency_task_completion_title(translator))

        def message_fn(remaining_seconds: float) -> str:
            base = stimulus_text.to_plain_text(stimulus_text.agency_task_completion_message(translator))
            break_msg = stimulus_text.to_plain_text(stimulus_text.task_completion_break_message(translator, f'{remaining_seconds:.0f}'))
            return f'{base}\n\n{break_msg}{SKIP_HINT}'

        run_break(
            win, keyboard_monitor, clock, title, message_fn,
            duration_ms=TASK_COMPLETION_BREAK_DURATION, continue_key='space'
        )

    def run_end_page() -> None:
        """Port of getEndPage (experiment.ts). A hyperlink can't be made
        clickable in a desktop window, so the resolved URL is shown as
        plain informational text instead."""
        text = resolve_end_message_text(state, translator, participant_name)
        run_message(win, keyboard_monitor, text + CONTINUE_HINT)

    

    return PhaseRunners(
        # run_device_connect=connection.BLEConnectionPhase(context).run,
        run_introduction=introduction.IntroductionPhase(context).run,
        run_practice=practice.PracticePhase(context).run,
        run_calibration=calibration.CalibrationPhase(context).run,
        run_validation=validation.ValidationPhase(context).run,
        run_continue_message=run_continue_message,
        run_task_core=task_core.TaskCorePhase(context).run,
        run_final_calibration=final_calibration.FinalCalibrationPhase(context).run,
        run_end_of_agency_break=run_end_of_agency_break,
        run_agency_task_core=agency_task_core.AgencyTaskCorePhase(context).run,
        run_end_page=run_end_page,
    )


