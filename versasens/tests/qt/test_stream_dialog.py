import asyncio
import random
from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from PySide6.QtGui import QCloseEvent
from pytestqt.qtbot import QtBot

from src.qt.stream import stream_dialog
from src.qt.stream.stream_dialog import StreamDialog
from src.utils.constants import BLE_DEVICE_NAME, BLE_MAX_CONNECTION_ATTEMPTS
from src.versa.ble import BLEStreamConfig
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor_group import SensorGroup


def _patch_close_teardown(
    monkeypatch: pytest.MonkeyPatch,
    dialog: StreamDialog,
) -> None:
    """Avoid save prompts and RawDataStateError when qtbot closes the widget."""
    monkeypatch.setattr(dialog, "_ask_to_save_data", MagicMock(return_value=False))

    original_has_data = RawData.has_data

    def _safe_has_data(self: RawData) -> bool:
        if self.write_location == WriteLocation.TO_DISK and self.temp_file_path is None:
            return False
        return original_has_data(self)

    monkeypatch.setattr(RawData, "has_data", _safe_has_data)


@pytest.fixture
def random_ble_address() -> str:
    return ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))


@pytest.fixture
def ble_device(random_ble_address) -> BLEDevice:
    return BLEDevice(
        address=random_ble_address,
        name=BLE_DEVICE_NAME,
        details={},
    )


def _make_stream_dialog(
    config_with_path: Path,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    ble_device: BLEDevice,
) -> StreamDialog:
    """Create a StreamDialog wired up for streaming tests."""
    monkeypatch.setattr(StreamDialog, "_start_refresh_devices_task", MagicMock())
    monkeypatch.setattr(stream_dialog, "LoadingDialog", MagicMock())
    monkeypatch.setattr(stream_dialog, "QMessageBox", MagicMock())

    dialog = StreamDialog(config_path=config_with_path)
    qtbot.addWidget(dialog)
    dialog.devices.append(ble_device)
    dialog.device_box.addItem("ABC")
    dialog.device_box.setCurrentIndex(0)
    return dialog


async def _wait_for(predicate: Callable[[], bool], max_wait_s: float = 2.0) -> None:
    """Poll a sync predicate until true or fail after max_wait_s seconds."""
    try:
        async with asyncio.timeout(max_wait_s):
            while not predicate():  # noqa: ASYNC110
                await asyncio.sleep(0.01)
    except TimeoutError as exc:
        msg = "Timed out waiting for condition"
        raise AssertionError(msg) from exc


class TestStartStream:
    @pytest.mark.asyncio
    async def test_ends_on_failed_attempts(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        # Patch _start_refresh_devices_task
        monkeypatch.setattr(StreamDialog, "_start_refresh_devices_task", MagicMock())

        # Create dialog
        dialog = StreamDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

        # Add a device
        dialog.devices.append(ble_device)

        # Select something in the device box
        dialog.device_box.addItem("ABC")
        dialog.device_box.setCurrentIndex(0)

        # Skip the loading dialog
        monkeypatch.setattr(stream_dialog, "LoadingDialog", MagicMock())

        # Skip QMessageBoxes
        monkeypatch.setattr(stream_dialog, "QMessageBox", MagicMock())

        # Skip the reconnect backoff delay
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        # Patch so ble_start_stream works
        calls = []

        # Always fails
        async def _mock_ble_start_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> Exception | None:
            config.error_callback()
            calls.append(len(calls) + 1)

        monkeypatch.setattr(
            stream_dialog,
            "ble_start_stream",
            _mock_ble_start_stream,
        )

        await dialog._start_stream()

        # 1st attempt + retries
        assert len(calls) == BLE_MAX_CONNECTION_ATTEMPTS

    @pytest.mark.asyncio
    async def test_attempt_count_resets_on_successful_attempt(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        # Patch _start_refresh_devices_task
        monkeypatch.setattr(StreamDialog, "_start_refresh_devices_task", MagicMock())

        # Create dialog
        dialog = StreamDialog(config_path=config_with_path)
        qtbot.addWidget(dialog)

        # Add a device
        dialog.devices.append(ble_device)

        # Select something in the device box
        dialog.device_box.addItem("ABC")
        dialog.device_box.setCurrentIndex(0)

        # Skip the loading dialog
        monkeypatch.setattr(stream_dialog, "LoadingDialog", MagicMock())

        # Skip QMessageBoxes
        monkeypatch.setattr(stream_dialog, "QMessageBox", MagicMock())

        # Skip the reconnect backoff delay
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        # Patch so ble_start_stream works
        calls = []

        # Fail the first time, success the second time, then fail afterwards
        async def _mock_ble_start_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> Exception | None:
            if len(calls) == 1:
                config.connected_callback()
                calls.append("success")
            else:
                config.error_callback()
                calls.append("error")

        monkeypatch.setattr(
            stream_dialog,
            "ble_start_stream",
            _mock_ble_start_stream,
        )

        await dialog._start_stream()

        # 1st attempt: fail (attempt = 1)
        # 2nd attempt: success (attempt = 0)
        # 3rd attempt: fail (attempt = 1)
        # 4th attempt: fail (attempt = 2)
        assert len(calls) == BLE_MAX_CONNECTION_ATTEMPTS + 1

    @pytest.mark.asyncio
    async def test_retries_max_times_when_connection_errors(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        calls = []

        async def _always_errors(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> BleakError:
            config.error_callback()
            calls.append(1)
            return BleakError("boom")

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _always_errors)

        await dialog._start_stream()

        assert len(calls) == BLE_MAX_CONNECTION_ATTEMPTS

    @pytest.mark.asyncio
    async def test_shows_single_error_popup_when_attempts_exhausted(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        async def _always_errors(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> BleakError:
            config.error_callback()
            return BleakError("boom")

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _always_errors)

        await dialog._start_stream()

        # One consolidated popup from end_streaming — NOT one per failed attempt
        assert stream_dialog.QMessageBox.critical.call_count == 1

    @pytest.mark.asyncio
    async def test_backoff_skipped_on_first_attempt(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        delay_mock = AsyncMock()
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", delay_mock)

        async def _always_errors(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            config.error_callback()

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _always_errors)

        await dialog._start_stream()

        # Backoff runs before attempts 2..N (i.e. N-1 times), never before the first
        assert delay_mock.await_count == BLE_MAX_CONNECTION_ATTEMPTS - 1

    @pytest.mark.asyncio
    async def test_parsed_data_not_cleared_on_reconnect(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        # Spy on clear() of the live SensorGroup used during streaming
        clear_spy = MagicMock(wraps=dialog.data.clear)
        monkeypatch.setattr(dialog.data, "clear", clear_spy)

        state = {"phase": 0}

        async def _reconnecting_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            if state["phase"] == 0:
                # First attempt: connect, then the device drops by itself
                config.connected_callback()
                state["phase"] = 1
                config.device_disconnected_event.set()
                return
            # Second attempt (the reconnect): connect then stop
            config.connected_callback()
            config.stop_event.set()
            return

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _reconnecting_stream)

        await dialog._start_stream()

        # A reconnect happened (two attempts) and data.clear() was never called
        assert state["phase"] == 1
        clear_spy.assert_not_called()

    @pytest.mark.asyncio
    async def test_end_streaming_resets_ui_when_all_attempts_fail(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        async def _always_errors(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            config.error_callback()

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _always_errors)

        await dialog._start_stream()

        # end_streaming must have run: session inactive and UI re-enabled
        assert not dialog.stream_active_event.is_set()
        assert not dialog.stop_button.isEnabled()
        assert dialog.start_button.isEnabled()
        assert dialog.device_box.isEnabled()


class TestStopAndClose:
    @pytest.mark.asyncio
    async def test_stop_button_ends_running_stream(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        async def _blocking_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            config.connected_callback()
            await config.stop_event.wait()

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _blocking_stream)

        dialog._create_start_stream_task()
        await _wait_for(lambda: dialog.is_running_event.is_set())

        # Press stop
        dialog._handle_stop_stream_button()
        await asyncio.wait_for(dialog.start_stream_task, timeout=5)

        assert not dialog.stream_active_event.is_set()
        assert not dialog.stop_button.isEnabled()
        assert dialog.start_button.isEnabled()
        assert dialog.device_box.isEnabled()

    @pytest.mark.asyncio
    async def test_close_during_active_connection(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        _patch_close_teardown(monkeypatch, dialog)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        async def _blocking_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            config.connected_callback()
            await config.stop_event.wait()

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _blocking_stream)

        dialog._create_start_stream_task()
        await _wait_for(lambda: dialog.is_running_event.is_set())

        event = QCloseEvent()
        dialog.closeEvent(event)
        await asyncio.wait_for(dialog.close_task, timeout=5)

        assert dialog.stop_event.is_set()
        assert not dialog.stream_active_event.is_set()
        assert dialog.start_stream_task.done()

    @pytest.mark.asyncio
    async def test_close_during_reconnection_stops_loop(
        self,
        config_with_path: Path,
        qtbot: QtBot,
        monkeypatch: pytest.MonkeyPatch,
        ble_device: BLEDevice,
    ):
        dialog = _make_stream_dialog(config_with_path, qtbot, monkeypatch, ble_device)
        _patch_close_teardown(monkeypatch, dialog)
        monkeypatch.setattr(StreamDialog, "_reconnect_delay", AsyncMock())

        state = {"phase": 0}

        async def _two_phase_stream(
            _address: str,
            _data: SensorGroup,
            _raw_data: RawData,
            config: BLEStreamConfig,
        ) -> None:
            if state["phase"] == 0:
                # Connect, then device drops by itself -> triggers a reconnect
                config.connected_callback()
                state["phase"] = 1
                config.device_disconnected_event.set()
                return
            # Reconnect attempt in progress: block until stop
            await config.stop_event.wait()
            return

        monkeypatch.setattr(stream_dialog, "ble_start_stream", _two_phase_stream)

        dialog._create_start_stream_task()
        # Wait until mid-reconnect: not connected, but session still active
        await _wait_for(
            lambda: not dialog.is_running_event.is_set()
            and dialog.stream_active_event.is_set(),
        )

        # Sanity-check the exact state that used to fool closeEvent
        assert not dialog.is_running_event.is_set()
        assert dialog.stream_active_event.is_set()

        event = QCloseEvent()
        dialog.closeEvent(event)
        await asyncio.wait_for(dialog.close_task, timeout=5)

        assert dialog.stop_event.is_set()
        assert not dialog.stream_active_event.is_set()
        # The stream task finished — no leftover reconnect loop (zombie)
        assert dialog.start_stream_task.done()
