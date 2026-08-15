"""Module containing functions related to BLE communication with VersaSens devices."""

import asyncio
import contextlib
import weakref
from collections.abc import Callable
from dataclasses import dataclass

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
    BleakError,
)

from src.utils.config import SensorParseConfig
from src.utils.constants import (
    BLE_CHARACTERISTIC_UUID,
    BLE_CMD_CHARACTERISTIC_UUID,
    BLE_CMD_GET_LOFF_CFG,
    BLE_CMD_LEAD_OFF_CHECK,
    BLE_CMD_SET_LOFF_CFG,
    BLE_CONNECTION_TIMEOUT,
    BLE_DEVICE_NAME,
    BLE_FIND_DEVICES_TIMEOUT,
    BLE_LEAD_OFF_CHECK_TIMEOUT,
    BLE_LOFF_CFG_TIMEOUT,
    LOFF_CFG_RESPONSE_LEN,
    LOFF_CFG_STATUS_OK,
)
from src.utils.exceptions import UnknownHeaderError
from src.utils.logger import logger
from src.utils.typedefs import SensorName
from src.versa.raw_data import RawData, WriteLocation
from src.versa.sensor_group import SensorGroup, data_to_sensor_attr_name

# Live BLE clients, tracked so they can be disconnected before the event loop is
# torn down. On macOS/CoreBluetooth a characteristic callback delivered after the
# loop closes crashes the app; disconnecting first makes that far less likely.
# WeakSet: entries drop automatically once a client is garbage-collected.
_active_clients: weakref.WeakSet = weakref.WeakSet()


async def ble_disconnect_all() -> None:
    """
    Best-effort disconnect of every currently-connected BLE client.

    Intended to run on application shutdown, while the event loop is still alive,
    so no late CoreBluetooth callbacks arrive after it closes.
    """
    for client in list(_active_clients):
        with contextlib.suppress(Exception):
            if client.is_connected:
                await client.disconnect()
    logger.debug("[BLE] Disconnected all active clients on shutdown")


async def find_versasens_ble_devices() -> list[BLEDevice]:
    """
    Async function to find VersaSens BLE devices.

    Returns:
        The list of BLE devices alongside their

    """
    logger.debug("[BLE] Finding VersaSens BLE devices...")
    devices: list[BLEDevice] = await BleakScanner.discover(
        cb={"use_bdaddr": False},
        timeout=BLE_FIND_DEVICES_TIMEOUT,
    )

    versasens_devices = [
        d
        for d in devices
        if d.name is not None and BLE_DEVICE_NAME.lower() in d.name.lower()
    ]

    logger.debug(
        f"[BLE] Found {len(versasens_devices)} VersaSens BLE devices",
        devices=versasens_devices,
    )

    return versasens_devices


async def _command_exchange(
    address: str,
    payload: bytes,
    matches: Callable[[bytearray], bool],
    timeout_s: float,
    what: str,
) -> bytearray | None:
    """
    Write one command to the command characteristic and await its indication.

    Used by the short request/response exchanges that run while the device is
    idle (electrode check, lead-off configuration). Each call opens its own
    connection: the device accepts a single central at a time, so these cannot
    overlap with a running stream.

    Args:
        address: The BLE address of the device.
        payload: The bytes to write to the command characteristic.
        matches: Predicate picking this command's reply out of the indications
                 that share the characteristic. Must check both the first byte
                 and the length, since neither identifies a reply on its own.
        timeout_s: Seconds to wait for the reply.
        what: Short description used in the log messages.

    Returns:
        The matching indication payload, or None on timeout/error.

    """
    loop = asyncio.get_running_loop()
    result_future: asyncio.Future[bytearray] = loop.create_future()

    def _indication_handler(_: BleakGATTCharacteristic, data: bytearray) -> None:
        if matches(data) and not result_future.done():
            result_future.set_result(data)

    # Resolve a live device handle first. On macOS/CoreBluetooth a device cannot
    # be connected by address string unless it was freshly discovered, so scan
    # for it here instead of passing the raw address to BleakClient.
    logger.debug(f"[BLE] Running {what}", address=address)
    device = await BleakScanner.find_device_by_address(
        address,
        timeout=BLE_FIND_DEVICES_TIMEOUT,
    )
    if device is None:
        logger.warning(f"[BLE] Device not found for {what}", address=address)
        return None

    try:
        async with BleakClient(
            device,
            timeout=BLE_CONNECTION_TIMEOUT,
        ) as client:
            _active_clients.add(client)
            await client.start_notify(
                BLE_CMD_CHARACTERISTIC_UUID,
                _indication_handler,
            )
            await client.write_gatt_char(
                BLE_CMD_CHARACTERISTIC_UUID,
                payload,
                response=True,
            )
            try:
                return await asyncio.wait_for(result_future, timeout=timeout_s)
            except TimeoutError:
                logger.warning(f"[BLE] {what} timed out")
                return None
            finally:
                with contextlib.suppress(Exception):
                    await client.stop_notify(BLE_CMD_CHARACTERISTIC_UUID)
    except (BleakError, TimeoutError, EOFError) as exc:
        logger.warning(f"[BLE] {what} connection failed", exc=exc)
        return None


async def ble_run_lead_off_check(address: str) -> tuple[int, int, int] | None:
    """
    Run a one-shot electrode lead-off check on the device over BLE.

    Intended to be run before an acquisition, while the device is idle.

    Args:
        address: The BLE address of the device to check.

    Returns:
        A (loff_statp, loff_statn, rld_stat) tuple, or None on timeout/error.

    """
    # Result frame: [BLE_CMD_LEAD_OFF_CHECK, statp, statn, rld].
    min_len = 4
    data = await _command_exchange(
        address,
        bytes([BLE_CMD_LEAD_OFF_CHECK]),
        lambda d: len(d) >= min_len and d[0] == BLE_CMD_LEAD_OFF_CHECK,
        BLE_LEAD_OFF_CHECK_TIMEOUT,
        "lead-off check",
    )
    if data is None:
        return None
    return (data[1], data[2], data[3])


@dataclass(frozen=True)
class LeadOffConfig:
    """The device's active lead-off configuration, as reported by the device."""

    status: int
    """One of the LOFF_CFG_STATUS_* codes."""

    comp_th: int
    """Comparator threshold, index into LOFF_THRESHOLDS."""

    raw_register: int
    """The LOFF register (address 04h) as read back from the ADS1298."""

    @property
    def ok(self) -> bool:
        """Whether the device accepted and applied the request."""
        return self.status == LOFF_CFG_STATUS_OK

    def to_metadata(self) -> dict[str, int]:
        """Expand the raw register into the fields stored with a recording."""
        return {
            "comp_th": self.comp_th,
            "vlead_off_en": (self.raw_register >> 4) & 0x01,
            "ilead_off": (self.raw_register >> 2) & 0x03,
            "flead_off": self.raw_register & 0x03,
            "raw_register": self.raw_register,
        }


def _parse_loff_config(data: bytearray) -> LeadOffConfig:
    # Reply layout: cmd, status, comp_th, reserved, raw_loff.
    return LeadOffConfig(status=data[1], comp_th=data[2], raw_register=data[4])


def _loff_config_matches(data: bytearray, cmd: int) -> bool:
    # Both the first byte and the length are needed: the device's generic
    # command ack is `value + 0xA0` truncated to 8 bits, so a command of 0x71
    # acks as a one-byte 0x11 and would otherwise be mistaken for this reply.
    return len(data) == LOFF_CFG_RESPONSE_LEN and data[0] == cmd


async def ble_get_loff_config(address: str) -> LeadOffConfig | None:
    """
    Read the device's active lead-off configuration.

    Args:
        address: The BLE address of the device.

    Returns:
        The configuration read back from the device, or None on timeout/error.

    """
    data = await _command_exchange(
        address,
        bytes([BLE_CMD_GET_LOFF_CFG]),
        lambda d: _loff_config_matches(d, BLE_CMD_GET_LOFF_CFG),
        BLE_LOFF_CFG_TIMEOUT,
        "lead-off config read",
    )
    return None if data is None else _parse_loff_config(data)


async def ble_set_loff_config(address: str, comp_th: int) -> LeadOffConfig | None:
    """
    Set the device's lead-off comparator threshold.

    The device only applies this while it is idle; if it is recording or
    streaming it replies with LOFF_CFG_STATUS_NOT_IDLE and leaves the register
    untouched. The reply always carries the values read back from the device,
    so the returned config is what the device is really running either way.

    Args:
        address: The BLE address of the device.
        comp_th: The threshold to apply, index into LOFF_THRESHOLDS.

    Returns:
        The configuration read back from the device, or None on timeout/error.

    """
    # Third byte is reserved for a future ac/dc selection and must be zero.
    data = await _command_exchange(
        address,
        bytes([BLE_CMD_SET_LOFF_CFG, comp_th, 0]),
        lambda d: _loff_config_matches(d, BLE_CMD_SET_LOFF_CFG),
        BLE_LOFF_CFG_TIMEOUT,
        "lead-off config write",
    )
    return None if data is None else _parse_loff_config(data)


@dataclass
class BLEStreamConfig:
    """Config dataclass for the ble_start_stream function."""

    should_process_data_of_sensor: dict[str, bool]
    """Dict of sensor name to whether the sensor's data should be processed"""

    # ===================================== Events =====================================
    stop_event: asyncio.Event
    """Event called when the user wishes to stop the stream"""
    device_disconnected_event: asyncio.Event
    """Event called when the device disconnected by itself"""

    # =================================== Callbacks ====================================
    connected_callback: Callable[[], None]
    """Callback called when the device is connected"""
    error_callback: Callable[[], None]
    """Callback called when an error with the connection arises"""
    found_sensor_callback: Callable[[SensorName], None]
    """Callback called when a new sensor was found in the received data"""

    sensor_parse_config: SensorParseConfig

    # Optional: enable sending commands over the live streaming connection (the
    # device allows a single central, so a lead-off check mid-recording must reuse
    # this connection rather than opening its own).
    client_ready_callback: Callable[[BleakClient], None] | None = None
    """Called once with the connected client so the caller can write commands."""
    command_result_callback: Callable[[bytearray], None] | None = None
    """Called with each indication received on the command characteristic."""


def _get_ble_notification_handler(
    sensors_data: SensorGroup,
    raw_data: RawData,
    should_process_data_of_sensor: dict[str, bool],
    found_sensor_callback: Callable[[SensorName], None],
    sensor_parse_config: SensorParseConfig,
) -> Callable[[BleakGATTCharacteristic, bytearray], None]:
    # Currying
    def _notification_handler(_: BleakGATTCharacteristic, data: bytearray) -> None:
        with RawData.from_bytes(data, WriteLocation.TO_MEMORY) as notif_raw_data:
            try:
                # Get the sensor name from the data
                sensor_name = data_to_sensor_attr_name(data)

                # Callback with the sensor name
                found_sensor_callback(sensor_name)

                # Optional data processing
                if should_process_data_of_sensor[sensor_name]:
                    # A live notification may contain a full sensor batch (ADS1298
                    # currently sends six 36-byte records), not just one record.
                    sensors_data.add_raw_data(
                        notif_raw_data,
                        sensor_parse_config,
                    )

                # Write and go to the end of the buffer
                raw_data.add_data(data)

            except UnknownHeaderError:
                # Ignore errors when parsing the header
                logger.warning("Received an unknown header")

    return _notification_handler


def _get_command_indication_handler(
    raw_data: RawData,
    command_result_callback: Callable[[bytearray], None] | None,
) -> Callable[[BleakGATTCharacteristic, bytearray], None]:
    # Indications on the command characteristic are told apart by length:
    # 0x7777 condition/check markers are 13 bytes and belong in the recording;
    # everything else (4-byte lead-off result, generic acks) goes to the caller.
    marker_len = 13

    def _handler(_: BleakGATTCharacteristic, data: bytearray) -> None:
        if len(data) == marker_len and bytes(data[:2]) == b"\x77\x77":
            with contextlib.suppress(Exception):
                raw_data.add_data(data)
            return
        if command_result_callback is not None:
            command_result_callback(data)

    return _handler


def _get_disconnect_callback(
    stop_event: asyncio.Event,
    device_disconnected_event: asyncio.Event,
) -> Callable[[BleakClient], None]:
    def _disconnect_callback(_: BleakClient) -> None:
        if stop_event.is_set():
            logger.debug("[BLE] Device disconnected by user")
        else:
            logger.error("[BLE] Device disconnected by itself")
            device_disconnected_event.set()

    return _disconnect_callback


async def ble_start_stream(
    address: str,
    data: SensorGroup,
    raw_data: RawData,
    config: BLEStreamConfig,
) -> Exception | None:
    """
    Start the communication with a VersaSens device using BLE.

    Args:
        address: The BLE address of the device to connect to
        data: The SensorsData instance where parsed data is put
        raw_data: The object where the raw data will be put
        config: The stream config used for the stream

    Returns:
        The raised exception if one was raised

    """
    try:
        logger.debug("[BLE] Trying to start BLE connection", address=address)

        # No pair=True: the device's characteristics are not encrypted, so pairing
        # is unnecessary and, on macOS/CoreBluetooth, forcing it is a common cause
        # of hangs during connection / service discovery.
        async with BleakClient(
            address,
            disconnected_callback=_get_disconnect_callback(
                config.stop_event,
                config.device_disconnected_event,
            ),
            timeout=BLE_CONNECTION_TIMEOUT,
        ) as client:
            # Connected to device
            logger.debug(f"[BLE] Connected to {address}")
            _active_clients.add(client)
            config.connected_callback()

            await client.start_notify(
                BLE_CHARACTERISTIC_UUID,
                _get_ble_notification_handler(
                    data,
                    raw_data,
                    config.should_process_data_of_sensor,
                    config.found_sensor_callback,
                    config.sensor_parse_config,
                ),
            )

            # Also subscribe to the command characteristic so a lead-off check can
            # be run over this connection while streaming. Its indications carry
            # both short command results (routed to the caller) and 0x7777 check
            # markers (folded into raw_data so they land in the recording — they
            # ride the command char, not the data char the stream otherwise saves).
            if (
                config.command_result_callback is not None
                or config.client_ready_callback is not None
            ):
                await client.start_notify(
                    BLE_CMD_CHARACTERISTIC_UUID,
                    _get_command_indication_handler(
                        raw_data,
                        config.command_result_callback,
                    ),
                )
                if config.client_ready_callback is not None:
                    config.client_ready_callback(client)

            logger.debug("[BLE] started collecting data")

            # Wait for either disconnect or user stop
            _, pending = await asyncio.wait(
                [
                    asyncio.create_task(config.device_disconnected_event.wait()),
                    asyncio.create_task(config.stop_event.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending waits
            for task in pending:
                task.cancel()

    except BleakCharacteristicNotFoundError as e:
        logger.exception(e)  # pyright: ignore[reportArgumentType]
        config.error_callback()
        return e

    except BleakDeviceNotFoundError as e:
        logger.exception(e)  # pyright: ignore[reportArgumentType]
        config.error_callback()
        return e

    except BleakError as e:
        logger.exception(e)  # pyright: ignore[reportArgumentType]
        config.error_callback()
        return e

    except TimeoutError as e:
        # Raised by BleakClient when the connection times out. Must be caught
        # here so that control returns to the caller instead of escaping and
        # leaving the UI in a stuck, unrecoverable state.
        logger.exception(e)  # pyright: ignore[reportArgumentType]
        config.error_callback()
        return e

    return None
