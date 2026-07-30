"""Hardware trigger device abstraction.

Replaces the Web Serial API device (src/modules/experiment/triggers/
serialport.ts, `navigator.serial.requestPort()`) with desktop-native
hardware access. The JS app only ever sent raw single-byte trigger codes
over a serial/parallel connection -- no LSL was used -- so pyserial /
psychopy.parallel cover full parity without adding an LSL dependency.
"""

from __future__ import annotations

from typing import Protocol


class TriggerDevice(Protocol):
    def send(self, code: int) -> None: ...

    def reset(self) -> None: ...

    def close(self) -> None: ...


class NullTriggerDevice:
    """No-op device for development machines without trigger hardware.
    Logs to console instead of writing bytes anywhere."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.last_code = 0

    def send(self, code: int) -> None:
        self.last_code = code
        if self.verbose:
            print(f'[trigger] send {code}')

    def reset(self) -> None:
        self.last_code = 0
        if self.verbose:
            print('[trigger] reset')

    def close(self) -> None:
        pass


class ParallelTriggerDevice:
    """Wraps psychopy.parallel.ParallelPort for true parallel-port EEG
    amplifiers (e.g. via inpout32/dlportio on Windows, pyparallel on
    Linux)."""

    def __init__(self, address: int | str = 0x0378):
        from psychopy import parallel

        self.port = parallel.ParallelPort(address=address)

    def send(self, code: int) -> None:
        self.port.setData(code)

    def reset(self) -> None:
        self.port.setData(0)

    def close(self) -> None:
        pass


class SerialTriggerDevice:
    """Wraps pyserial for USB-to-TTL trigger boxes, the most common
    interface for modern EEG trigger hardware."""

    def __init__(self, port_name: str, baudrate: int = 115200):
        import serial

        self.ser = serial.Serial(port_name, baudrate)

    def send(self, code: int) -> None:
        self.ser.write(bytes([code]))

    def reset(self) -> None:
        self.ser.write(bytes([0]))

    def close(self) -> None:
        self.ser.close()


def create_trigger_device(
    kind: str, address_or_port: str | int | None = None
) -> TriggerDevice:
    """Factory used by main.py/settings to build the configured device.
    `kind` is one of 'none', 'parallel', 'serial'."""
    if kind == 'parallel':
        return ParallelTriggerDevice(address_or_port if address_or_port is not None else 0x0378)
    if kind == 'serial':
        if not address_or_port:
            raise ValueError('serial trigger device requires a port name')
        return SerialTriggerDevice(str(address_or_port))
    return NullTriggerDevice()


def resolve_device_status_message(trigger_device: TriggerDevice) -> str:
    """Port of the confirmation half of deviceConnectPages
    (triggers/serialport.ts) -- a human-readable status line for the
    trigger device screen (trials/message_trial.py's run_message_trial).

    Unlike the JS version, there's no in-app connect/retry flow here: the
    device is already resolved deterministically from the `--trigger`
    CLI flag at process start, before ExperimentState/PhaseRunners even
    exist (see main.py's `main()`), since a desktop app has no browser
    permission prompt to retry against. This screen is a confirmation the
    experimenter reads before starting, not a connection attempt."""
    if isinstance(trigger_device, ParallelTriggerDevice):
        return 'Trigger device: parallel port connected.'
    if isinstance(trigger_device, SerialTriggerDevice):
        return 'Trigger device: serial port connected.'
    return 'Trigger device: none (continuing without hardware triggers).'
