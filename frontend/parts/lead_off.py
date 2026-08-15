# frontend/parts/lead_off.py

import logging
from psychopy import visual
import frontend.drawUtils.message as message
from frontend.parts.context import PhaseContext
from pathlib import Path

logger = logging.getLogger(__name__)

# Norm-unit positions for each electrode overlaid on the EEG-head.png diagram.
# These are layout knobs (positions ON the diagram, not physiological montage
# positions) -- tune them against the actual PNG on a real display. There must
# be one entry here for every non-None name in CHANNEL_MAP.
ELECTRODE_POSITIONS = {
    "Fp1": (-0.04, 0.65),   # left frontal pole
    "Fp2": (0.04,  0.65),   # right frontal pole
    "C3":  (-0.07, 0.50),   # left central
    "C4":  (0.07,  0.50),   # right central
    "O1":  (-0.03, 0.30),   # left occipital
    "O2":  (0.03,  0.30),   # right occipital
}

# Maps ADS lead-off channel index -> electrode name, in hardware channel order.
# `channels[i]` from the lead-off check is True when channel i has POOR contact;
# CHANNEL_MAP[i] is the electrode wired to that channel. `None` marks an unused
# channel (nothing physically connected) -- those indices are ignored for both
# the "poor contact" list and the diagram overlay.
#
# IF A NEW ELECTRODE IS ADDED IN THE FUTURE: replace the `None` at that channel's
# index with the electrode name (e.g. "Cz"), and add a matching entry to
# ELECTRODE_POSITIONS above so it gets a dot on the diagram. Keep this list in
# hardware channel order -- index position is what ties a name to its channel.
CHANNEL_MAP = ["Fp2", "C4", "O2", None, "Fp1", "C3", "O1", None]


class LeadOffCheckPhase:
    def __init__(self, context: PhaseContext):
        self.context = context
        self.diagram_path = Path(__file__).parent.parent.parent / "src2" / "assets" / "images" / "EEG-head.png"

    def run(self) -> None:
        win = self.context.win
        kb = self.context.keyboard_monitor
        ble = self.context.ble

        if ble is None:
            return

        # Show initial instruction
        instr_text = (
            "We need to check electrode impedance.\n\n"
            "Please ensure all electrodes are properly connected.\n"
            "Press 'Check' to begin the test."
        )
        choice = message.run_choice(
            win, kb, instr_text,
            {"check": 0, "skip": 1},
            button_labels=["Check", "Skip"],
            align='center'
        )
        if choice is None or choice['response'] == 1:
            return  # skip phase

        while True:
            # Show waiting message (no button)
            message.run_text_only(
                win, "Checking electrode impedance...\n\nPlease wait.",
                align='center'
            )

            # Run the lead-off check
            try:
                response = ble.lead_off_check(timeout=15.0)
            except TimeoutError:
                logger.warning("Lead-off check timeout")
                response = {"status": "error", "message": "Check timed out (15s)."}
            except Exception as e:
                logger.exception("Lead-off check failed")
                response = {"status": "error", "message": str(e)}

            if response.get("status") != "ok":
                error_text = (
                    f"Lead-off check failed.\n\n"
                    f"Error: {response.get('message', 'Unknown error')}\n\n"
                    "Press 'Retry' to try again, or 'Skip' to continue without check."
                )
                retry_choice = message.run_choice(
                    win, kb, error_text,
                    {"retry": 0, "skip": 1},
                    button_labels=["Retry", "Skip"],
                    align='center'
                )
                if retry_choice is None or retry_choice['response'] == 1:
                    return
                continue

            # Decode channels
            channels = response.get("channels")
            reference = response.get("reference")
            bias = response.get("bias")
            print(f"Lead-off check channels: {channels}")
            if channels is None:
                try:
                    from src.versa.sensors.ads import ADS
                    statp = response.get("statp", 0)
                    statn = response.get("statn", 0)
                    rld = response.get("rld", 0)
                    stat_x = (statn & 0x01) | ((rld & 0x01) << 1)
                    status = ADS.decode_lead_off(statp, stat_x)
                    channels = status.channels
                    reference = status.reference
                    bias = status.bias
                except ImportError:
                    channels = [False] * 8

            # Reference and bias are the montage-wide electrodes: if either has
            # poor contact (truthy) the per-channel readings can't be trusted, so
            # fix those first before looking at the individual electrodes. Only
            # when BOTH are good (False) do we fall through to the per-electrode
            # display below.
            if reference or bias:
                bad = []
                if reference:
                    bad.append("reference")
                if bias:
                    bad.append("bias")
                error_text = (
                    f"Poor contact on the {' and '.join(bad)} electrode"
                    f"{'s' if len(bad) > 1 else ''}.\n\n"
                    "These must be fixed before the other electrodes can be checked.\n"
                    "Please adjust them and retry, or skip to continue.\n"
                )
                retry_choice = message.run_choice(
                    win, kb, error_text,
                    {"retry": 0, "skip": 1},
                    button_labels=["Retry", "Skip"],
                    align='center'
                )
                if retry_choice is None or retry_choice['response'] == 1:
                    return
                continue

            # Only mapped channels count -- unused (None) channels float and can
            # read as "poor", so ignore them here and on the diagram.
            poor_indices = [
                i for i, ch in enumerate(channels[:8])
                if ch and i < len(CHANNEL_MAP) and CHANNEL_MAP[i] is not None
            ]
            if poor_indices:
                # Build diagram stimuli
                diagram_stims = self._build_diagram_stims(win, channels)
                poor_names = [CHANNEL_MAP[i] for i in poor_indices]
                error_text = (
                    f"Poor electrode contact detected on:\n"
                    f"{', '.join(poor_names)}\n\n"
                    "Please adjust the electrodes and retry, or skip to continue.\n"
                )
                retry_choice = message.run_choice(
                    win, kb, error_text,
                    {"retry": 0, "skip": 1},
                    button_labels=["Retry", "Skip"],
                    align='center',
                    extra_stims=diagram_stims   # display diagram with the message
                )
                if retry_choice is None or retry_choice['response'] == 1:
                    return
                continue

            # All good
            success_text = "All electrodes have good contact.\n\nYou may proceed."
            message.run_message(win, kb, success_text, button_label="Continue", align='center')
            break

    def _build_diagram_stims(self, win, channels):
        """Return a list of stimuli (ImageStim + Circles) to overlay on the message screen."""
        stims = []
        if self.diagram_path.exists():
            diagram = visual.ImageStim(win, image=str(self.diagram_path), pos=(0, 0.5), size=(0.4, 0.5), units='norm')
        else:
            diagram = visual.TextStim(win, text="EEG diagram missing", pos=(0, 0), height=0.1)
        stims.append(diagram)

        # Circles for each channel
        for i, status in enumerate(channels[:8]):
            if i >= len(CHANNEL_MAP):
                break
            name = CHANNEL_MAP[i]
            if name is None:
                continue  # unused channel -- nothing to draw on the diagram
            pos = ELECTRODE_POSITIONS.get(name, (0, 0))
            print(f"Channel {name} at {pos} is {'poor' if status else 'good'}")
            color = 'red' if status else 'green'
            circle = visual.Circle(win, radius=(0.024,0.030), pos=pos, fillColor=color, lineColor=None, units='norm')
            stims.append(circle)
        return stims