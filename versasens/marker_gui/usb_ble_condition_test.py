#!/usr/bin/env python3
"""Measure USB-out -> firmware -> BLE-in condition-event latency.

The tool also keeps the existing USB echo RTT measurement and validates the
condition_id embedded in each BLE-only ADS1298 sample record.
"""

import argparse
import asyncio
import contextlib
import statistics
import struct
import time

import serial
import serial.tools.list_ports
from bleak import BleakClient, BleakScanner


DEVICE_NAME = "VersaSens_V1_11"
DATA_UUID = "e11d2e01-04ab-4da5-b66a-eecb738f90f3"
CMD_UUID = "e11d2e03-04ab-4da5-b66a-eecb738f90f3"

HEADER_TRIGGER = 0x7777
HEADER_ADS1298 = 0xDDDD

USB_FRAME_FMT = "<HIBB"
USB_FRAME_LEN = struct.calcsize(USB_FRAME_FMT)  # 8
TRIGGER_EVENT_FMT = "<HIHB"
TRIGGER_EVENT_LEN = struct.calcsize(TRIGGER_EVENT_FMT)  # 9
EEG_RECORD_FMT = "<hIBBB24s"
EEG_RECORD_LEN = struct.calcsize(EEG_RECORD_FMT)  # 33
EEG_RECORDS_PER_BATCH = 7
EEG_BATCH_LEN = EEG_RECORD_LEN * EEG_RECORDS_PER_BATCH  # 231
EEG_PAYLOAD_LEN = 26
EEG_EXPECTED_INDEX_STEP = 4

BLE_CMD_START_OVERWRITE = 0x08
BLE_CMD_MODE_STREAM = 0x04


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100.0
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def print_stats(label, values):
    if not values:
        print(f"{label}: no successful measurements")
        return
    print(
        f"{label}: n={len(values)} min={min(values):.3f} ms "
        f"mean={statistics.fmean(values):.3f} ms "
        f"p50={percentile(values, 50):.3f} ms "
        f"p95={percentile(values, 95):.3f} ms "
        f"p99={percentile(values, 99):.3f} ms "
        f"max={max(values):.3f} ms"
    )


def timestamp_at_or_after(timestamp_us, reference_us):
    """Compare wrapping uint32 microsecond timestamps within a 2^31-us window."""
    return ((timestamp_us - reference_us) & 0xFFFFFFFF) < 0x80000000


def find_serial_port(requested):
    if requested:
        return requested

    ports = list(serial.tools.list_ports.comports())
    preferred = [
        port.device
        for port in ports
        if "VersaSens" in (port.description or "")
        or "usbmodem" in port.device.lower()
    ]
    if len(preferred) == 1:
        return preferred[0]
    if not preferred:
        raise RuntimeError("No VersaSens / usbmodem serial port found; use --serial")
    raise RuntimeError(f"Multiple USB serial ports found: {preferred}; use --serial")


async def find_ble_device(address, name, timeout):
    if address:
        device = await BleakScanner.find_device_by_address(address, timeout=timeout)
        if device is None:
            raise RuntimeError(f"BLE device {address} not found")
        return device

    devices = await BleakScanner.discover(timeout=timeout)
    matches = [device for device in devices if device.name == name]
    if not matches:
        names = sorted({device.name for device in devices if device.name})
        raise RuntimeError(f"BLE device {name!r} not found; discovered: {names}")
    return matches[0]


class ConditionTester:
    def __init__(self, serial_port, timeout, duplicate_window):
        self.serial_port = serial_port
        self.timeout = timeout
        self.duplicate_window = duplicate_window
        self.serial = None
        self.client = None
        self.loop = asyncio.get_running_loop()
        self.usb_acks = asyncio.Queue()
        self.ble_events = asyncio.Queue()
        self.usb_rtt_ms = []
        self.usb_ble_latency_ms = []
        self.last_event_sequence = None
        self.current_condition = 0
        self.usb_timeouts = 0
        self.ble_timeouts = 0
        self.sequence_gaps = 0
        self.event_duplicates = 0
        self.unexpected_events = 0
        self.eeg_errors = 0
        self.eeg_records = 0
        self.eeg_samples = []
        self.transitions = []
        self.last_eeg_index = None
        self._serial_reader_task = None

    def notification_handler(self, _sender, payload):
        received_at = time.perf_counter()
        data = bytes(payload)

        if len(data) == TRIGGER_EVENT_LEN:
            header, timestamp_us, sequence, condition_id = struct.unpack(
                TRIGGER_EVENT_FMT, data
            )
            if header == HEADER_TRIGGER and condition_id in (0, 1):
                self.loop.call_soon_threadsafe(
                    self.ble_events.put_nowait,
                    (received_at, timestamp_us, sequence, condition_id),
                )
                return

        if len(data) == EEG_BATCH_LEN:
            self._validate_eeg_batch(data)
            return

        print(f"WARN unexpected BLE notification: {len(data)} bytes")

    def _validate_eeg_batch(self, data):
        for offset in range(0, len(data), EEG_RECORD_LEN):
            signed_header, timestamp_us, length, index, condition_id, _samples = (
                struct.unpack_from(EEG_RECORD_FMT, data, offset)
            )
            header = signed_header & 0xFFFF
            if header != HEADER_ADS1298 or length != EEG_PAYLOAD_LEN:
                self.eeg_errors += 1
                print(
                    f"WARN invalid EEG record header=0x{header:04x} "
                    f"len={length} timestamp={timestamp_us}"
                )
                continue
            if condition_id not in (0, 1):
                self.eeg_errors += 1
                print(f"WARN invalid EEG condition {condition_id} at {timestamp_us} us")
            if self.last_eeg_index is not None:
                step = (index - self.last_eeg_index) & 0xFF
                if step != EEG_EXPECTED_INDEX_STEP:
                    self.eeg_errors += 1
                    print(
                        f"WARN EEG index gap {self.last_eeg_index}->{index} "
                        f"(expected +{EEG_EXPECTED_INDEX_STEP})"
                    )
            self.last_eeg_index = index
            self.eeg_records += 1
            self.eeg_samples.append((timestamp_us, condition_id, index))

    async def start(self, client, start_stream):
        self.client = client
        self.serial = serial.Serial(self.serial_port, 115200, timeout=0.05)
        self.serial.reset_input_buffer()
        await client.start_notify(DATA_UUID, self.notification_handler)
        if start_stream:
            await client.write_gatt_char(
                CMD_UUID, bytes([BLE_CMD_START_OVERWRITE]), response=True
            )
            await client.write_gatt_char(
                CMD_UUID, bytes([BLE_CMD_MODE_STREAM]), response=True
            )
        self._serial_reader_task = asyncio.create_task(self._serial_reader())

    async def close(self):
        if self._serial_reader_task:
            self._serial_reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._serial_reader_task
        if self.client and self.client.is_connected:
            with contextlib.suppress(Exception):
                await self.client.stop_notify(DATA_UUID)
        if self.serial:
            self.serial.close()

    async def _serial_reader(self):
        buffer = bytearray()
        while True:
            chunk = await asyncio.to_thread(self.serial.read, USB_FRAME_LEN)
            if not chunk:
                continue
            buffer.extend(chunk)
            while len(buffer) >= USB_FRAME_LEN:
                if buffer[0] != 0x77 or buffer[1] != 0x77:
                    buffer.pop(0)
                    continue
                frame = bytes(buffer[:USB_FRAME_LEN])
                del buffer[:USB_FRAME_LEN]
                header, timestamp_us, length, command = struct.unpack(
                    USB_FRAME_FMT, frame
                )
                if header == HEADER_TRIGGER and length == 1:
                    self.usb_acks.put_nowait(
                        (time.perf_counter(), timestamp_us, command)
                    )

    async def _write_usb(self, condition_id):
        def write_and_flush():
            self.serial.write(bytes([condition_id]))
            self.serial.flush()

        await asyncio.to_thread(write_and_flush)

    async def _matching_queue_item(self, queue, predicate):
        deadline = self.loop.time() + self.timeout
        while True:
            remaining = deadline - self.loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            item = await asyncio.wait_for(queue.get(), timeout=remaining)
            if predicate(item):
                return item

    async def send_condition(self, condition_id):
        if condition_id not in (0, 1):
            raise ValueError("condition must be 0 or 1")

        changed = condition_id != self.current_condition
        sent_at = time.perf_counter()
        await self._write_usb(condition_id)

        ack_task = asyncio.create_task(
            self._matching_queue_item(self.usb_acks, lambda item: item[2] == condition_id)
        )
        event_task = None
        if changed:
            event_task = asyncio.create_task(
                self._matching_queue_item(
                    self.ble_events, lambda item: item[3] == condition_id
                )
            )

        try:
            ack = await ack_task
            usb_rtt = (ack[0] - sent_at) * 1000.0
            self.usb_rtt_ms.append(usb_rtt)
            # A valid ACK proves the firmware accepted this explicit state,
            # even if the corresponding BLE event is lost or times out.
            self.current_condition = condition_id
        except asyncio.TimeoutError:
            self.usb_timeouts += 1
            usb_rtt = None

        event = None
        hybrid_latency = None
        if event_task:
            try:
                event = await event_task
                hybrid_latency = (event[0] - sent_at) * 1000.0
                self.usb_ble_latency_ms.append(hybrid_latency)
                expected = None
                if self.last_event_sequence is not None:
                    expected = (self.last_event_sequence + 1) & 0xFFFF
                if expected is not None and event[2] != expected:
                    if event[2] == self.last_event_sequence:
                        self.event_duplicates += 1
                        print(f"WARN duplicate event sequence {event[2]}")
                    else:
                        self.sequence_gaps += 1
                        print(f"WARN event sequence {event[2]}, expected {expected}")
                self.last_event_sequence = event[2]
                self.transitions.append((event[1], event[3], event[2]))
                self.current_condition = condition_id
            except asyncio.TimeoutError:
                self.ble_timeouts += 1
        else:
            try:
                event = await asyncio.wait_for(
                    self._matching_queue_item(
                        self.ble_events, lambda item: item[3] == condition_id
                    ),
                    timeout=self.duplicate_window,
                )
                self.unexpected_events += 1
                print(
                    f"WARN duplicate condition produced BLE event "
                    f"seq={event[2]} dev_ts={event[1]} us"
                )
            except asyncio.TimeoutError:
                pass

        usb_text = "timeout" if usb_rtt is None else f"{usb_rtt:.3f} ms"
        if not changed:
            ble_text = "not expected (condition unchanged)"
        elif hybrid_latency is None:
            ble_text = "timeout"
        else:
            ble_text = (
                f"{hybrid_latency:.3f} ms seq={event[2]} "
                f"dev_ts={event[1]} us"
            )
        print(f"condition={condition_id} USB_RTT={usb_text} USB->BLE={ble_text}")

    def _eeg_label_mismatches(self, show_warnings=False):
        label_mismatches = 0
        for timestamp_us, actual_condition, index in self.eeg_samples:
            expected_condition = 0
            for transition_us, condition_id, _sequence in self.transitions:
                if timestamp_at_or_after(timestamp_us, transition_us):
                    expected_condition = condition_id
            if actual_condition != expected_condition:
                label_mismatches += 1
                if show_warnings and label_mismatches <= 10:
                    print(
                        f"WARN EEG label mismatch index={index} "
                        f"timestamp={timestamp_us} condition={actual_condition} "
                        f"expected={expected_condition}"
                    )
        return label_mismatches

    def report(self):
        label_mismatches = self._eeg_label_mismatches(show_warnings=True)

        print_stats("USB RTT", self.usb_rtt_ms)
        print_stats("USB-out -> BLE-in", self.usb_ble_latency_ms)
        print(
            f"errors: usb_timeouts={self.usb_timeouts} "
            f"ble_timeouts={self.ble_timeouts} "
            f"sequence_gaps={self.sequence_gaps} "
            f"event_duplicates={self.event_duplicates} "
            f"unexpected_events={self.unexpected_events} "
            f"eeg_format/index={self.eeg_errors} "
            f"eeg_label_mismatches={label_mismatches}; "
            f"EEG records validated={self.eeg_records}"
        )
        return (
            self.usb_timeouts
            + self.ble_timeouts
            + self.sequence_gaps
            + self.event_duplicates
            + self.unexpected_events
            + self.eeg_errors
            + label_mismatches
        )


async def interactive_mode(tester):
    print("Commands: 0, 1, stats, quit")
    while True:
        command = (await asyncio.to_thread(input, "condition> ")).strip().lower()
        if command in ("quit", "q", "exit"):
            return
        if command == "stats":
            tester.report()
        elif command in ("0", "1"):
            await tester.send_condition(int(command))
        else:
            print("Enter 0, 1, stats, or quit")


async def async_main(args):
    serial_port = find_serial_port(args.serial)
    print(f"Scanning for BLE device {args.name!r}...")
    device = await find_ble_device(args.address, args.name, args.scan_timeout)
    print(f"BLE device: {device.name} ({device.address})")
    print(f"USB port: {serial_port}")

    tester = ConditionTester(serial_port, args.timeout, args.duplicate_window)
    async with BleakClient(device) as client:
        await tester.start(client, args.start_stream)
        print("BLE subscribed and USB connected")
        error_count = 0
        try:
            if args.count > 0:
                for iteration in range(args.count):
                    await tester.send_condition(1 if iteration % 2 == 0 else 0)
                    if args.interval > 0:
                        await asyncio.sleep(args.interval)
            else:
                await interactive_mode(tester)
        finally:
            error_count = tester.report()
            await tester.close()
        if args.count > 0 and error_count:
            raise RuntimeError(f"automatic test failed with {error_count} error(s)")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Test USB condition input and BLE event/EEG output"
    )
    parser.add_argument("--serial", help="USB CDC port; auto-detected if omitted")
    parser.add_argument("--address", help="BLE address/identifier; scan by name if omitted")
    parser.add_argument("--name", default=DEVICE_NAME, help="BLE advertising name")
    parser.add_argument("--count", type=int, default=0, help="automatic alternating tests")
    parser.add_argument("--interval", type=float, default=0.1, help="seconds between tests")
    parser.add_argument("--timeout", type=float, default=2.0, help="ACK/event timeout seconds")
    parser.add_argument(
        "--duplicate-window",
        type=float,
        default=0.15,
        help="seconds to watch for a forbidden event after repeating a condition",
    )
    parser.add_argument("--scan-timeout", type=float, default=10.0)
    parser.add_argument(
        "--start-stream",
        action="store_true",
        help="request BLE STREAM mode (requires the ADS1298 hardware)",
    )
    return parser


def main():
    args = build_arg_parser().parse_args()
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    except Exception as error:
        raise SystemExit(f"ERROR: {error}") from error


if __name__ == "__main__":
    main()
