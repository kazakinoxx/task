import asyncio
import pathlib
import random
import string
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService
from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
    BleakError,
)

from src.utils.config import SensorParseConfig
from src.utils.constants import BLE_DEVICE_NAME
from src.versa.ble import (
    _get_ble_notification_handler,
    _get_disconnect_callback,
    ble_start_stream,
    find_versasens_ble_devices,
)
from src.versa.raw_data import RawData
from src.versa.sensor_group import SENSOR_ATTR_NAMES, SensorGroup

# ======================================== MOCK ========================================


@pytest.fixture
def random_ble_address() -> str:
    return ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))


@pytest.fixture
def versasens_device(random_ble_address) -> BLEDevice:
    return BLEDevice(
        address=random_ble_address,
        name=BLE_DEVICE_NAME,
        details={},
    )


@pytest.fixture
def random_ble_device(random_ble_address) -> BLEDevice:
    random_name = BLE_DEVICE_NAME

    while random_name == BLE_DEVICE_NAME:
        random_name = "".join(random.choices(string.ascii_letters, k=10))

    return BLEDevice(
        address=random_ble_address,
        name=random_name,
        details={},
    )


@pytest.fixture
def sensor_name_callback() -> MagicMock:
    """Mock callback function."""
    return MagicMock()


@pytest.fixture
def should_process_data() -> dict[str, bool]:
    """Mock function that always returns True."""
    return dict.fromkeys(SENSOR_ATTR_NAMES, True)


@pytest.fixture
def should_not_process_data() -> dict[str, bool]:
    """Mock function that always returns False."""
    return dict.fromkeys(SENSOR_ATTR_NAMES, False)


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock(spec=BleakClient)


@pytest.fixture
def mock_data() -> SensorGroup:
    """Mock SensorGroup instance."""
    return SensorGroup()


@pytest.fixture
def stop_event() -> asyncio.Event:
    """Mock stop event."""
    return asyncio.Event()


@pytest.fixture
def device_disconnected_event() -> asyncio.Event:
    """Mock disconnect event."""
    return asyncio.Event()


@pytest.fixture
def connected_callback() -> MagicMock:
    return MagicMock()


@pytest.fixture
def connection_error_callback() -> MagicMock:
    return MagicMock()


@pytest.fixture
def found_sensor_callback() -> MagicMock:
    return MagicMock()


@dataclass
class BLEStreamConfigMock:
    should_process_data_of_sensor: dict[str, bool]
    stop_event: asyncio.Event
    device_disconnected_event: asyncio.Event
    connected_callback: MagicMock
    error_callback: MagicMock
    found_sensor_callback: MagicMock
    sensor_parse_config: SensorParseConfig


class BleStartStreamArgs(TypedDict):
    address: str
    data: SensorGroup
    raw_data: RawData
    config: BLEStreamConfigMock


@pytest.fixture
def mock_ble_start_stream_args(
    random_ble_address: str,
    mock_data: SensorGroup,
    raw_data_memory: RawData,
    should_not_process_data: dict[str, bool],
    stop_event: asyncio.Event,
    device_disconnected_event: asyncio.Event,
    connected_callback: MagicMock,
    connection_error_callback: MagicMock,
    found_sensor_callback: MagicMock,
    sensor_parse_config: SensorParseConfig,
) -> BleStartStreamArgs:
    return {
        "address": random_ble_address,
        "data": mock_data,
        "raw_data": raw_data_memory,
        "config": BLEStreamConfigMock(
            should_process_data_of_sensor=should_not_process_data,
            stop_event=stop_event,
            device_disconnected_event=device_disconnected_event,
            connected_callback=connected_callback,
            error_callback=connection_error_callback,
            found_sensor_callback=found_sensor_callback,
            sensor_parse_config=sensor_parse_config,
        ),
    }


@pytest.fixture
def mock_ble_start_stream_args_process_data(
    mock_ble_start_stream_args: BleStartStreamArgs,
    should_process_data: dict[str, bool],
) -> BleStartStreamArgs:
    mock_ble_start_stream_args[
        "config"
    ].should_process_data_of_sensor = should_process_data
    return mock_ble_start_stream_args


# ============================= find_versasens_ble_devices =============================


class TestFindVersasensBleDevices:
    @pytest.mark.asyncio
    async def test_works(
        self,
        versasens_device: BLEDevice,
        random_ble_device: BLEDevice,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Create mock BLE devices
        mock_devices = [versasens_device, random_ble_device]

        # Patch discover
        async def mock_discover(*args, **kwargs) -> list[BLEDevice]:  # noqa: ANN002, ARG001
            return mock_devices

        monkeypatch.setattr("bleak.BleakScanner.discover", mock_discover)

        result = await find_versasens_ble_devices()

        # Assertions
        assert len(result) == 1
        assert result[0].name == BLE_DEVICE_NAME
        assert result[0].address == versasens_device.address

    @pytest.mark.asyncio
    async def test_works_when_none_present(
        self,
        random_ble_device: BLEDevice,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Patch discover
        async def mock_discover(*args, **kwargs) -> list[BLEDevice]:  # noqa: ANN002, ARG001
            return [random_ble_device]

        monkeypatch.setattr("bleak.BleakScanner.discover", mock_discover)

        result = await find_versasens_ble_devices()
        assert len(result) == 0


# =========================== _get_ble_notification_handler ============================


@pytest.fixture
def service() -> BleakGATTService:
    return BleakGATTService(None, 0, "")


@pytest.fixture
def characteristic(service: BleakGATTService) -> BleakGATTCharacteristic:
    return BleakGATTCharacteristic(None, 0, "", [], lambda: 1, service)


class TestGetBleNotificationHandler:
    def test_works(
        self,
        characteristic: BleakGATTCharacteristic,
        should_process_data: dict[str, bool],
        sensor_name_callback: MagicMock,
        raw_data_memory: RawData,
        sensor_group: SensorGroup,
        test_files_chunks_and_parsed: list[tuple[list[bytes], SensorGroup]],
        sensor_parse_config: SensorParseConfig,
    ) -> None:
        # Send data in chunks
        for test_file_chunks, exp_data in test_files_chunks_and_parsed:
            # Reset sensor group and raw data
            sensor_group = SensorGroup()
            raw_data_memory.clear()

            # Get the handler
            handler = _get_ble_notification_handler(
                sensor_group,
                raw_data_memory,
                should_process_data_of_sensor=should_process_data,
                found_sensor_callback=sensor_name_callback,
                sensor_parse_config=sensor_parse_config,
            )

            # Call the handler on each chunk
            for chunk in test_file_chunks:
                handler(characteristic, bytearray(chunk))

            # Check the callbacks were called
            sensor_name_callback.assert_called()

            # Data should have been processed
            assert sensor_group.has_data()

            # Compare results
            assert exp_data == sensor_group

    def test_only_parse_if_needed(
        self,
        characteristic: BleakGATTCharacteristic,
        sensor_name_callback: MagicMock,
        raw_data_memory_factory: Callable[[], RawData],
        test_files_chunks_and_parsed: list[tuple[list[bytes], SensorGroup]],
        sensor_parse_config: SensorParseConfig,
    ):
        # Pick random sensors to test
        nbr_rnd_names = random.randint(1, len(SENSOR_ATTR_NAMES))
        rnd_sensor_names = random.choices(SENSOR_ATTR_NAMES, k=nbr_rnd_names)

        should_process_data_of_sensor: dict[str, bool] = {}
        for sensor_name in SENSOR_ATTR_NAMES:
            should_process_data_of_sensor[sensor_name] = sensor_name in rnd_sensor_names

        # Send chunks
        for test_file_chunks, exp_data in test_files_chunks_and_parsed:
            data = SensorGroup()
            raw_data = raw_data_memory_factory()

            # Get handler
            handler = _get_ble_notification_handler(
                data,
                raw_data,
                should_process_data_of_sensor=should_process_data_of_sensor,
                found_sensor_callback=sensor_name_callback,
                sensor_parse_config=sensor_parse_config,
            )

            # Call the handler on each chunk
            for chunk in test_file_chunks:
                handler(characteristic, bytearray(chunk))

            # Only the random sensors should have data
            name_to_exp = {
                name: exp_data._get_sensor(name) for name in rnd_sensor_names
            }

            for sensor in data._get_all_sensors():
                if sensor.attr_name() in name_to_exp:
                    exp = name_to_exp[sensor.attr_name()]
                    assert sensor == exp
                else:
                    assert sensor.is_empty()

    def test_works_no_data_parsed(
        self,
        characteristic: BleakGATTCharacteristic,
        should_not_process_data: dict[str, bool],
        sensor_name_callback: MagicMock,
        raw_data_memory_factory: Callable[[], RawData],
        test_files_chunks: list[list[bytes]],
        sensor_parse_config: SensorParseConfig,
    ):
        for test_file_chunks in test_files_chunks:
            data = SensorGroup()
            raw_data = raw_data_memory_factory()

            handler = _get_ble_notification_handler(
                data,
                raw_data,
                should_process_data_of_sensor=should_not_process_data,
                found_sensor_callback=sensor_name_callback,
                sensor_parse_config=sensor_parse_config,
            )

            # Call the handler on each chunk
            for chunk in test_file_chunks:
                handler(characteristic, bytearray(chunk))

            # No data should have been processed
            assert not data.has_data()

    def test_callback_is_called(
        self,
        characteristic: BleakGATTCharacteristic,
        should_not_process_data: dict[str, bool],
        raw_data_memory_factory: Callable[[], RawData],
        test_files_chunks_and_parsed: list[tuple[list[bytes], SensorGroup]],
        sensor_parse_config: SensorParseConfig,
    ):
        for test_file_chunks, exp_data in test_files_chunks_and_parsed:
            res_data = SensorGroup()
            raw_data = raw_data_memory_factory()

            found_names: set[str] = set()

            def _sensor_name_callback(names_set: set[str]) -> Callable[[str], None]:
                def _fct(sensor_name: str) -> None:
                    names_set.add(sensor_name)

                return _fct

            handler = _get_ble_notification_handler(
                res_data,
                raw_data,
                should_process_data_of_sensor=should_not_process_data,
                found_sensor_callback=_sensor_name_callback(found_names),
                sensor_parse_config=sensor_parse_config,
            )

            # Call the handler on each chunk
            for chunk in test_file_chunks:
                handler(characteristic, bytearray(chunk))

            # Check that the sensors that have data in the parsed data are present in
            # the set of names
            for exp_sensor in exp_data._get_all_sensors():
                if not exp_sensor.is_empty():
                    assert exp_sensor.attr_name() in found_names
                else:
                    assert exp_sensor.attr_name() not in found_names


# ============================== _get_disconnect_callback ==============================


class TestGetDisconnectCallback:
    def test_works(
        self,
        stop_event: asyncio.Event,
        device_disconnected_event: asyncio.Event,
    ):
        # Get the callback
        callback = _get_disconnect_callback(stop_event, device_disconnected_event)

        # Create client
        client = BleakClient("")

        # After call, the event is set
        callback(client)
        assert device_disconnected_event.is_set()
        assert not stop_event.is_set()

        # If already set, nothing changes
        callback(client)
        assert device_disconnected_event.is_set()
        assert not stop_event.is_set()


# ================================== ble_start_stream ==================================


def get_mock_client_class(mock_client: AsyncMock) -> type:
    class FakeBleakClient:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002
            pass

        async def __aenter__(self) -> AsyncMock:
            return mock_client

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    return FakeBleakClient


class TestBleStartStream:
    @pytest.mark.asyncio
    async def test_works(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args_process_data: BleStartStreamArgs,
        raw_data_memory_factory: Callable[[], RawData],
        test_files_path_chunks_and_parsed: list[
            tuple[pathlib.Path, list[bytes], SensorGroup]
        ],
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Need to capture the start_notify handler
        captured_kwargs = {}

        # Create event to wait until start_notify has started
        ready_event = asyncio.Event()

        # Get the handler by intercepting the function call
        async def _mock_start_notify(_uuid, handler) -> None:
            captured_kwargs["handler"] = handler
            ready_event.set()

        # Set as side_effect and ensure the mock_client is given to the async
        mock_client.start_notify.side_effect = _mock_start_notify
        mock_client.__aenter__.return_value = mock_client

        # Test for each test file
        for file, chunks, sensor_group in test_files_path_chunks_and_parsed:
            # Reset data before each iteration
            mock_ble_start_stream_args_process_data["data"] = SensorGroup()
            mock_ble_start_stream_args_process_data["raw_data"] = (
                raw_data_memory_factory()
            )

            # Reset the call counts
            mock_ble_start_stream_args_process_data[
                "config"
            ].found_sensor_callback.reset_mock()

            # Patch so we return our mock client
            monkeypatch.setattr(
                "src.versa.ble.BleakClient",
                get_mock_client_class(mock_client),
            )

            # Start the stream
            task = asyncio.create_task(
                ble_start_stream(**mock_ble_start_stream_args_process_data),  # pyright: ignore[reportArgumentType]
            )

            # Wait to be ready
            await asyncio.sleep(0)
            await ready_event.wait()

            # Manually call callback
            notif_handler = captured_kwargs["handler"]

            # Send each chunk
            for chunk in chunks:
                notif_handler(None, bytearray(chunk))

            # Check the raw data is the same
            res_buf: bytes = mock_ble_start_stream_args_process_data[
                "raw_data"
            ].get_contents()
            exp_buf = file.read_bytes()
            assert res_buf == exp_buf

            # Check that all of the data was parsed
            assert sensor_group == mock_ble_start_stream_args_process_data["data"]

            # Check how many times the callbacks was called
            assert mock_ble_start_stream_args_process_data[
                "config"
            ].found_sensor_callback.call_count == len(chunks)

            # End the task
            mock_ble_start_stream_args_process_data[
                "config"
            ].device_disconnected_event.set()
            exp = await asyncio.wait_for(task, None)
            assert exp is None

    @pytest.mark.asyncio
    async def test_sets_disconnect_event_if_disconnected(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args: BleStartStreamArgs,
    ):
        # Need to manually call the disconnected_callback
        captured_kwargs = {}

        # Get the callback by intercepting the constructor call
        def _mock_client_constructor(*args, **kwargs):  # noqa: ANN002, ANN202, ARG001
            captured_kwargs.update(kwargs)
            return mock_client

        # Create event to wait until start_notify has started
        ready_event = asyncio.Event()
        mock_client.start_notify.side_effect = ready_event.set()
        mock_client.__aenter__.return_value = mock_client

        # Patch so we return our mock client
        with patch("src.versa.ble.BleakClient", side_effect=_mock_client_constructor):
            # Start the stream
            task = asyncio.create_task(ble_start_stream(**mock_ble_start_stream_args))  # pyright: ignore[reportArgumentType]

            # Wait to be ready
            await asyncio.sleep(0)
            await ready_event.wait()

            # Manually call callback
            disconnected_callback = captured_kwargs["disconnected_callback"]
            disconnected_callback(mock_client)

            # Check that the event was set
            assert mock_ble_start_stream_args[
                "config"
            ].device_disconnected_event.is_set()

            exp = await asyncio.wait_for(task, None)

            assert exp is None

    @pytest.mark.asyncio
    async def test_calls_connected_callback(
        self,
        mock_ble_start_stream_args: BleStartStreamArgs,
        mock_client: AsyncMock,
    ):
        # Disconnect as a side effect to stop notify loop
        mock_client.start_notify.side_effect = mock_ble_start_stream_args[
            "config"
        ].stop_event.set()

        # Patch so we return our mock client
        with patch("src.versa.ble.BleakClient", return_value=mock_client):
            # Start the stream
            await ble_start_stream(**mock_ble_start_stream_args)  # pyright: ignore[reportArgumentType]

            # Check that the callback was called
            mock_ble_start_stream_args["config"].connected_callback.assert_called()

    @pytest.mark.asyncio
    async def test_calls_error_callback_if_error(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args: BleStartStreamArgs,
    ):
        # Can do this by patching the client so it disconnects just after the await
        # enter
        connection_error = BleakError("Connection failed")
        mock_client.__aenter__.side_effect = connection_error

        # Patch so we return our mock client
        with patch("src.versa.ble.BleakClient", return_value=mock_client):
            # Start the stream
            res = await ble_start_stream(**mock_ble_start_stream_args)  # pyright: ignore[reportArgumentType]

            # Check that the error was raised
            assert res == connection_error

            # Check that the callback was called
            mock_ble_start_stream_args["config"].error_callback.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc",
        [
            BleakError("connection failed"),
            BleakDeviceNotFoundError("device not found"),
            BleakCharacteristicNotFoundError("characteristic not found"),
            TimeoutError("connection timed out"),
        ],
    )
    async def test_returns_error_and_calls_callback_on_connection_error(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args: BleStartStreamArgs,
        exc: Exception,
    ):
        # Raise the error when entering the client context
        mock_client.__aenter__.side_effect = exc

        with patch("src.versa.ble.BleakClient", return_value=mock_client):
            res = await ble_start_stream(**mock_ble_start_stream_args)  # pyright: ignore[reportArgumentType]

        # The exception is returned (not raised) and the error callback fires
        assert res == exc
        mock_ble_start_stream_args["config"].error_callback.assert_called()

    @pytest.mark.asyncio
    async def test_calls_found_sensor_callback(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args: BleStartStreamArgs,
        test_files_chunks: list[list[bytes]],
    ):
        # Need to capture the start_notify handler
        captured_kwargs = {}

        # Create event to wait until start_notify has started
        ready_event = asyncio.Event()

        # Get the handler by intercepting the function call
        async def _mock_start_notify(_uuid, handler) -> None:
            captured_kwargs["handler"] = handler
            ready_event.set()

        # Set as side_effect and ensure the mock_client is given to the async
        mock_client.start_notify.side_effect = _mock_start_notify
        mock_client.__aenter__.return_value = mock_client

        # Test for each test file
        for chunks in test_files_chunks:
            # Patch so we return our mock client
            with patch("src.versa.ble.BleakClient", return_value=mock_client):
                # Start the stream
                task = asyncio.create_task(
                    ble_start_stream(**mock_ble_start_stream_args),  # pyright: ignore[reportArgumentType]
                )

                # Wait to be ready
                await asyncio.sleep(0)
                await ready_event.wait()

                # Manually call callback
                notif_handler = captured_kwargs["handler"]

                # Send each chunk
                for chunk in chunks:
                    notif_handler(None, chunk)

                # Check how many times the sensor callback was called
                assert mock_ble_start_stream_args[
                    "config"
                ].found_sensor_callback.call_count == len(chunks)

                # Reset the call count
                mock_ble_start_stream_args["config"].found_sensor_callback.reset_mock()

                # End the task
                mock_ble_start_stream_args["config"].device_disconnected_event.set()
                exp = await asyncio.wait_for(task, None)
                assert exp is None

    @pytest.mark.asyncio
    async def test_still_has_data_after_error(
        self,
        mock_client: AsyncMock,
        mock_ble_start_stream_args_process_data: BleStartStreamArgs,
        raw_data_memory_factory: Callable[[], RawData],
        test_files_path_chunks_and_parsed: list[
            tuple[pathlib.Path, list[bytes], SensorGroup]
        ],
    ):
        # Need to capture the start_notify handler
        captured_kwargs = {}

        # Create event to wait until start_notify has started
        ready_event = asyncio.Event()

        # Get the handler by intercepting the function call
        async def _mock_start_notify(_uuid, handler) -> None:
            captured_kwargs["handler"] = handler
            ready_event.set()

        # Set as side_effect and ensure the mock_client is given to the async
        mock_client.start_notify.side_effect = _mock_start_notify
        mock_client.__aenter__.return_value = mock_client

        # Test for each test file
        for _, chunks, sensor_group in test_files_path_chunks_and_parsed:
            # Reset data before each iteration
            mock_ble_start_stream_args_process_data["data"] = SensorGroup()
            mock_ble_start_stream_args_process_data["raw_data"] = (
                raw_data_memory_factory()
            )

            # Patch so we return our mock client
            with patch("src.versa.ble.BleakClient", return_value=mock_client):
                # Start the stream
                task = asyncio.create_task(
                    ble_start_stream(**mock_ble_start_stream_args_process_data),  # pyright: ignore[reportArgumentType]
                )

                # Wait to be ready
                await asyncio.sleep(0)
                await ready_event.wait()

                # Manually call callback
                notif_handler = captured_kwargs["handler"]

                # Split in two parts
                middle_i = len(chunks) // 2

                # Send first half
                for chunk in chunks[:middle_i]:
                    notif_handler(None, bytearray(chunk))

                # Send blank data
                notif_handler(None, bytearray(b""))

                # Send second half
                for chunk in chunks[middle_i:]:
                    notif_handler(None, bytearray(chunk))

                # Send blank data
                notif_handler(None, bytearray(b""))

                # Check that all of the data was parsed
                assert sensor_group == mock_ble_start_stream_args_process_data["data"]

                # End the task
                mock_ble_start_stream_args_process_data[
                    "config"
                ].device_disconnected_event.set()
                exp = await asyncio.wait_for(task, None)
                assert exp is None
