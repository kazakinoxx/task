"""
C:/Users/ikaze/AppData/Local/Programs/Python/Python313/python.exe -m src.connect
BLE worker – persistent asyncio event loop.
Commands:
- connect          : scan, connect, start streaming
- start_record     : enable writing to disk
- stop_record      : disable writing to disk
- lead_off_check   : run an accurate lead-off check (pauses streaming briefly)
- disconnect       : stop streaming, close file
- status           : return connection and recording state
"""

import sys
import json
import asyncio
import contextlib
from pathlib import Path
import shutil

import src.versa.ble as ble
from src.versa.ble import BLEStreamConfig
from src.versa.sensor_group import SENSOR_ATTR_NAMES, SensorGroup
from src.versa.raw_data import RawData, WriteLocation
from src.utils.config import Config
from src.utils.logger import logger
from src.utils.paths import CONFIG_PATH
from src.utils.exceptions import UnknownHeaderError
from src.versa.sensors.ads import ADS
from src.versa.process import parse_and_save_files, ParseConfig
from src.utils.typedefs import DeleteFiles, DryRun

# ------------------------------------------------------------------
# Windows event loop fix
# ------------------------------------------------------------------
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
RECORDING_FILE_PATH = Path("C:/Users/ikaze/Desktop/eeg/recording.csv")
RECORDING_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Global state
# ------------------------------------------------------------------
_recording_enabled = False
_address: str | None = None
stream_task: asyncio.Task | None = None
stop_event: asyncio.Event | None = None
raw_data: RawData | None = None
sensor_group: SensorGroup | None = None
connection_established = asyncio.Event()
connection_error: Exception | None = None
disconnect_event = asyncio.Event()
_subject_id: str | None = None
_notes: str = ""
# ------------------------------------------------------------------
# ControlledRawData
# ------------------------------------------------------------------
class ControlledRawData(RawData):
    def add_data(self, data):  # type: ignore
        global _recording_enabled
        if _recording_enabled:
            super().add_data(data)

    def close(self):
        if self.temp_file_path and self.temp_file_path.exists():
            size = self.temp_file_path.stat().st_size
            if size > 0:
                shutil.copy2(self.temp_file_path, RECORDING_FILE_PATH)
                logger.info(f"Recording saved to {RECORDING_FILE_PATH}")
        super().close()

# ------------------------------------------------------------------
# Callbacks
# ------------------------------------------------------------------
def connected_callback():
    connection_established.set()

def error_callback():
    global connection_error
    connection_error = RuntimeError("BLE connection error")
    connection_established.set()

def found_sensor_callback(sensor_name: str):
    pass  # optional debug

# ------------------------------------------------------------------
# Stream management
# ------------------------------------------------------------------
async def _import_recordings(subject_id: str, notes: str) -> None:
    """
    Import the recorded binary file into the database (generates CSVs).
    Runs in a background thread to avoid blocking the event loop.
    """
    try:
        # Define no‑op callbacks (the GUI callbacks are not needed here)
        def noop_path(p: Path) -> None:
            pass
        def noop_data(d) -> None:
            pass
        def noop_finished() -> None:
            pass

        callbacks = ParseConfig.Callbacks(
            set_raw_file_path=noop_path,
            set_raw_data=noop_data,
            finished_parsing_file=noop_finished,
        )

        parse_config = ParseConfig(
            config_path=CONFIG_PATH,
            delete_raw_files=DeleteFiles.NO,   # keep the .bin file
            dry_run=DryRun.WRITE,              # write to disk
            callbacks=callbacks,
            lead_off=None,                     # no lead‑off metadata
        )

        loop = asyncio.get_running_loop()
        import_folder = await loop.run_in_executor(
            None,
            parse_and_save_files,
            [RECORDING_FILE_PATH],   # list of files
            subject_id,
            notes,
            parse_config,
        )
        logger.info(f"Auto import completed: {import_folder}")
    except Exception as e:
        logger.exception(f"Auto import failed: {e}")

async def start_stream(address: str) -> bool:
    global stream_task, stop_event, raw_data, sensor_group, connection_established, connection_error

    sensor_group = SensorGroup()
    raw_data = ControlledRawData(WriteLocation.TO_DISK, config_path=CONFIG_PATH)
    raw_data.open()

    stop_event = asyncio.Event()
    device_disconnected_event = asyncio.Event()

    should_process = {name: True for name in SENSOR_ATTR_NAMES}
    config = BLEStreamConfig(
        should_process_data_of_sensor=should_process,
        stop_event=stop_event,
        device_disconnected_event=device_disconnected_event,
        connected_callback=connected_callback,
        error_callback=error_callback,
        found_sensor_callback=found_sensor_callback,
        sensor_parse_config=Config.get_sensor_parse_config(CONFIG_PATH),
    )

    connection_established.clear()
    connection_error = None

    stream_task = asyncio.create_task(
        ble.ble_start_stream(address, sensor_group, raw_data, config)
    )

    try:
        await asyncio.wait_for(connection_established.wait(), timeout=15.0)
    except asyncio.TimeoutError:
        connection_error = TimeoutError("Connection attempt timed out")
        stream_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stream_task
        return False

    if connection_error is not None:
        return False

    return True

async def stop_stream():
    global stream_task, stop_event, raw_data, sensor_group
    if stream_task is not None:
        stream_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stream_task
    if stop_event is not None:
        stop_event.set()
    if raw_data is not None:
        raw_data.close()
    stream_task = None
    stop_event = None
    raw_data = None
    sensor_group = None

# ------------------------------------------------------------------
# Scan helper
# ------------------------------------------------------------------
async def scan_devices():
    return await ble.find_versasens_ble_devices()

# ------------------------------------------------------------------
# Command handler
# ------------------------------------------------------------------
async def handle_command(line: str):
    global _recording_enabled, _address, _subject_id, _notes
    try:
        cmd = json.loads(line)
        action = cmd.get("action")
        response = {"status": "ok"}

        if action == "connect":
            devices = await scan_devices()
            if not devices:
                response = {"status": "error", "message": "No BLE devices found"}
            else:
                address = devices[0].address if hasattr(devices[0], 'address') else str(devices[0])
                logger.info(f"Connecting to {address}...")
                success = await start_stream(address)
                if success:
                    _address = address
                    response["message"] = f"Connected to {address}, stream ready"
                    response["device"] = address
                else:
                    err_msg = str(connection_error) if connection_error else "Connection failed"
                    response = {"status": "error", "message": err_msg}

        elif action == "lead_off_check":
            if _address is None:
                response = {"status": "error", "message": "No device address. Connect first."}
            else:
                # 1. Stop streaming
                logger.info("Pausing stream for lead-off check...")
                await stop_stream()
                # 2. Run the accurate check
                try:
                    result = await ble.ble_run_lead_off_check(_address)
                    if result is None:
                        response = {"status": "error", "message": "Lead-off check failed (no response)"}
                    else:
                        statp, statn, rld = result
                        response["statp"] = statp
                        response["statn"] = statn
                        response["rld"] = rld
                                        
                        stat_x = (statn & 0x01) | ((rld & 0x01) << 1)
                        status = ADS.decode_lead_off(statp, stat_x)
                        response["channels"] = status.channels  # list of bool
                        response["reference"] = status.reference  # bool
                        response["bias"] = status.bias  # bool
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
                # 3. Restart stream
                logger.info("Restarting stream after lead-off check...")
                success = await start_stream(_address)
                if not success:
                    response = {"status": "error", "message": "Failed to restart stream after lead-off check"}

        elif action == "start_record":
            if raw_data is None:
                response = {"status": "error", "message": "No active connection"}
            else:
                _recording_enabled = True
                response["message"] = "Recording started"

        elif action == "stop_record":
            if raw_data is None:
                response = {"status": "error", "message": "No active connection"}
            else:
                _recording_enabled = False
                response["message"] = "Recording stopped"

        elif action == "disconnect":
            await stop_stream()
            response["message"] = "Disconnected"
            if _subject_id is not None and RECORDING_FILE_PATH.exists():
                # Run import in background (non‑blocking)
                asyncio.create_task(_import_recordings(_subject_id, _notes))
            elif _subject_id is not None:
                logger.warning("Recording file not found; cannot import")

        elif action == "status":
            if raw_data is not None:
                response["status"] = "connected"
                response["recording"] = _recording_enabled
            else:
                response["status"] = "disconnected"

        elif action == "set_subject":
            _subject_id = cmd.get("subject_id")
            _notes = cmd.get("notes", "")
            if _subject_id:
                response["message"] = f"Subject set to {_subject_id}"
            else:
                response = {"status": "error", "message": "No subject_id provided"}

        else:
            response = {"status": "error", "message": f"Unknown action: {action}"}

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    except Exception as e:
        logger.exception(f"Command error: {e}")
        sys.stdout.write(json.dumps({"status": "error", "message": f"Command error: {str(e)}"}) + "\n")
        sys.stdout.flush()

async def read_stdin():
    loop = asyncio.get_running_loop()
    while not disconnect_event.is_set():
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        await handle_command(line.strip())

async def main():
    logger.info("BLE worker started (with lead-off support)")
    await read_stdin()
    await stop_stream()
    logger.info("BLE worker exiting")

if __name__ == "__main__":
    asyncio.run(main())