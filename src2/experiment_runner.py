"""ExperimentRunner -- port of the master timeline builder in
src/modules/experiment/experiment.ts (`run()`).

The JS version builds one big declarative jsPsych timeline array; there
is no timeline interpreter to replace here, so `run_experiment()` simply
*is* the timeline, expressed as ordinary Python control flow. Every
branch predicate (device-connect gate, resume-vs-fresh, taskOrder
EBDMFirst/AgencyFirst, the should-show-EBDM/Agency guards, the
should-break gate) is preserved exactly -- see `resolve_should_show_ebdm`
/ `resolve_should_show_agency` for the two trickiest ones.

Each phase is delegated to an injected callable (`PhaseRunners`) rather
than built inline, so this module's actual logic -- the sequencing and
branch decisions -- is fully unit-testable without PsychoPy, a window,
or any real trial execution. `main.py` wires the real callables (which
in turn call into parts/*.py and trials/*.py) for an actual run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from src2.state.experiment_state import ExperimentState
from src2.state.reload import ReloadObject


def resolve_should_show_ebdm(general_settings, reload_object: Optional[ReloadObject]) -> bool:
    """Port of `shouldShowEBDM`."""
    if general_settings.skipEBDMTask:
        return False
    if reload_object is None:
        return True
    task_order = general_settings.taskOrder or 'EBDMFirst'
    return reload_object.phase == 'EBDM' or (task_order == 'AgencyFirst' and reload_object.phase == 'agency')


def resolve_should_show_agency(general_settings, reload_object: Optional[ReloadObject]) -> bool:
    """Port of `shouldShowAgency`."""
    if general_settings.skipAgencyTask:
        return False
    task_order = general_settings.taskOrder or 'EBDMFirst'
    if task_order == 'EBDMFirst':
        return True
    if reload_object is None:
        return True
    return reload_object.phase == 'agency'

@dataclass
class PhaseRunners:
    run_device_connect: Optional[Callable[[], None]] = None
    run_introduction: Optional[Callable[[], None]] = None
    run_practice: Optional[Callable[[], None]] = None
    run_calibration: Optional[Callable[[], None]] = None
    run_validation: Optional[Callable[[], None]] = None
    run_continue_message: Optional[Callable[[], None]] = None
    run_task_core: Optional[Callable[[Optional[List[str]]], None]] = None
    run_final_calibration: Optional[Callable[[], None]] = None
    run_agency_task_core: Optional[Callable[[], None]] = None
    run_end_of_agency_break: Optional[Callable[[], None]] = None
    run_end_page: Optional[Callable[[], None]] = None
def run_experiment(
    state: ExperimentState,
    reload_object: Optional[ReloadObject],
    runners: PhaseRunners,
) -> None:
    general_settings = state.get_general_settings()

    if general_settings.useDevice and runners.run_device_connect is not None:
        print("Running device connect phase...")
        runners.run_device_connect()

    if reload_object is None:
        if runners.run_introduction is not None:
            runners.run_introduction()
        if runners.run_practice is not None:
            runners.run_practice()
        if runners.run_calibration is not None:
            runners.run_calibration()
        if runners.run_validation is not None:
            runners.run_validation()
    else:
        if runners.run_continue_message is not None:
            runners.run_continue_message()

    task_order = general_settings.taskOrder or 'EBDMFirst'
    should_show_ebdm = resolve_should_show_ebdm(general_settings, reload_object)
    should_show_agency = resolve_should_show_agency(general_settings, reload_object)
    should_break = should_show_ebdm and should_show_agency

    def push_ebdm() -> None:
        if not should_show_ebdm:
            return
        if runners.run_task_core is not None:
            remaining_trial_blocks = reload_object.remainingTrialBlocks if reload_object else None
            runners.run_task_core(remaining_trial_blocks)
        if runners.run_final_calibration is not None:
            runners.run_final_calibration()

    def push_agency() -> None:
        if not should_show_agency:
            return
        if runners.run_agency_task_core is not None:
            runners.run_agency_task_core()

    if task_order == 'AgencyFirst':
        push_agency()
        if should_break and runners.run_end_of_agency_break is not None:
            runners.run_end_of_agency_break()
        push_ebdm()
    else:
        push_ebdm()
        if should_break and runners.run_end_of_agency_break is not None:
            runners.run_end_of_agency_break()
        push_agency()

    # Always show the end page. run_end_page (via resolve_end_message_text)
    # already renders either the next-step link OR a generic "experiment has
    # ended" message, so gating it on linkToNextPage left a normal finish with
    # no closing screen at all -- the window just shut. This also matches the
    # abort path (main.py), which always shows that same message.
    if runners.run_end_page is not None:
        runners.run_end_page()