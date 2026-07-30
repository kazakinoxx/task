"""PsychoPy rendering for the agency tapping task trial -- thin, not
unit tested. Verify manually with a real window/keyboard. See the
src2 project's trials/agency_tapping_task_trial.py for the pure state
machine this drives.
"""

from __future__ import annotations

from frontend.thermometer_stim import ThermometerStim
from src2.trials.agency_tapping_task_trial import AgencyTappingTaskParams, AgencyTappingTaskState


def run_agency_tapping(win, keyboard_monitor, clock, params: AgencyTappingTaskParams) -> dict:
    state = AgencyTappingTaskState(params)
    thermometer = ThermometerStim(win) if params.show_thermometer else None

    now = clock.getTime()
    if state.start(now):
        return state.build_trial_record()

    while not state.trial_ended:
        now = clock.getTime()
        for key, event_type, event_time in keyboard_monitor.poll():
            if event_type == 'down':
                state.handle_key_down(key, event_time)
            else:
                state.handle_key_up(key, event_time)

        if state.awaiting_interruption_response:
            for key, event_type, event_time in keyboard_monitor.poll():
                if event_type == 'up' and key.lower() in ('y', 'n', 'o'):
                    state.receive_interruption_response(key, event_time)
                    break
        elif state.awaiting_hold_key_reminder:
            if all(state.keys_state[k] for k in params.keys_to_hold):
                state.confirm_keys_reheld(now)
        else:
            state.tick(now)

        if thermometer is not None and not state.is_in_interruption:
            thermometer.update(state.mercury_height, params.bounds)
            thermometer.draw()
            win.flip()

    return state.build_trial_record()
