# frontend/parts/ble_connection_phase.py

import logging
import frontend.drawUtils.message as message
from frontend.parts.context import PhaseContext

logger = logging.getLogger(__name__)


class BLEConnectionPhase:
    def __init__(self, context: PhaseContext):
        self.context = context

    def run(self) -> None:
        win = self.context.win
        kb = self.context.keyboard_monitor
        ble = self.context.ble

        if ble is None:
            return

        connected = False
        while not connected:
            # 1. Show initial connect screen (with "Connect" button)
            intro_text = (
                "Please connect the VersaSense BLE device.\n\n"
                "Make sure the device is powered on and in range.\n"
                "Or press 'Skip' to run without a device connected."
            )
            choice = message.run_choice(
                win, kb, intro_text,
                {"connect": 0, "skip": 1},
                button_labels=["Connect", "Skip"],
                align='center',
            )
            if choice is None:
                return  # window closed, abort
            if choice['response'] == 1:
                # Skip up front: proceed with no device connected, without going
                # through a connection attempt / troubleshooting.
                logger.info("BLE connection skipped by operator (running with no device).")
                return

            # 2. Show scanning message (no button) – immediate flip
            message.run_text_only(
                win, "Scanning for BLE devices...\n\nPlease wait.",
                align='center'
            )

            # 3. Attempt connection (blocking)
            try:
                response = ble.connect(timeout=15.0)
            except TimeoutError:
                logger.warning("BLE connection timeout")
                response = {"status": "error", "message": "Connection timed out (15s)."}
            except Exception as e:
                logger.exception("BLE connection error")
                response = {"status": "error", "message": str(e)}

            # 4. Process response
            if response.get("status") == "ok":
                device = response.get("device", "Unknown")
                success_text = f"✅ BLE device connected successfully!\n\nDevice: {device}"
                message.run_message(win, kb, success_text, button_label="Continue", align='center')
                connected = True
            else:
                # Show error with Retry / Skip options
                error_text = (
                    f"❌ BLE connection failed.\n\n"
                    f"Error: {response.get('message', 'Unknown error')}\n\n"
                    "Press 'Retry' to try again, or 'Skip' to continue without BLE."
                )
                retry_choice = message.run_choice(
                    win, kb, error_text,
                    {"retry": 0, "skip": 1},
                    button_labels=["Retry", "Skip"],
                    align='center',
                )
            
                if retry_choice['response'] == 1:  # "Skip" selected
                    break  # exit loop, skip BLE
                # "Retry" selected: loop continues to the top,
                # showing the initial "Connect" screen again