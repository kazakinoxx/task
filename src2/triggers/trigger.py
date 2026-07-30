"""send_trigger -- port of sendSerialTrigger's pulse timing
(src/modules/experiment/triggers/trigger.ts).

The JS version fires the reset via `setTimeout(..., 100)`, a macrotask
scheduled on the browser's event loop with typical jitter in the several-
-millisecond range under load. Here the pulse is held with a blocking
wait on a high-resolution clock (psychopy.core.wait by default), which
is tighter than browser setTimeout jitter -- a genuine fidelity
improvement for EEG event-marker alignment, not a compromise.
"""

from __future__ import annotations

from typing import Callable, Optional

from src2.triggers.trigger_codes import build_trigger_byte
from src2.triggers.trigger_device import TriggerDevice

PULSE_DURATION_SECONDS = 0.1  # 100ms, matches TRIGGER pulse width in trigger.ts


def send_trigger(
    device: TriggerDevice,
    outside_task: bool,
    decision_trigger: bool,
    delayed_condition: bool = False,
    reward: Optional[str] = None,
    bounds: Optional[str] = None,
    is_end: bool = False,
    wait_fn: Optional[Callable[[float], None]] = None,
) -> int:
    """Builds and sends the trigger byte, holds it for
    PULSE_DURATION_SECONDS, then resets to 0. Returns the code sent (for
    logging/testing). `wait_fn` defaults to psychopy.core.wait but can be
    injected (e.g. a no-op) for unit tests that don't want to import
    psychopy or actually block."""
    code = build_trigger_byte(
        outside_task=outside_task,
        decision_trigger=decision_trigger,
        delayed_condition=delayed_condition,
        reward=reward,
        bounds=bounds,
        is_end=is_end,
    )
    device.send(code)
    if wait_fn is None:
        from psychopy import core

        wait_fn = core.wait
    wait_fn(PULSE_DURATION_SECONDS)
    device.reset()
    return code
